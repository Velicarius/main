import asyncio
import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.database import SessionLocal
from app.services.price_eod import PriceEODRepository
from app.quotes.stooq import fetch_eod, StooqFetchError

logger = logging.getLogger(__name__)

# Import Celery app (will be defined in celery_app.py)
from app.celery_app import celery_app


@celery_app.task(name="prices.run_eod_refresh", bind=True)
def run_eod_refresh(self) -> Dict[str, Any]:
    """
    Main EOD refresh task that respects feature flags.
    
    Returns:
        Summary dictionary with total_symbols, inserted_rows, errors
    """
    logger.info("Starting EOD refresh task")
    
    # Check if EOD is enabled
    if not settings.eod_enable:
        logger.info("EOD feature is disabled via EOD_ENABLE=false, skipping refresh")
        return {
            "status": "disabled",
            "message": "EOD feature is disabled",
            "total_symbols": 0,
            "inserted_rows": 0,
            "errors": []
        }
    
    # Check EOD source
    if settings.eod_source != "stooq":
        logger.warning(f"EOD source '{settings.eod_source}' is not supported, only 'stooq' is implemented")
        return {
            "status": "unsupported_source",
            "message": f"EOD source '{settings.eod_source}' is not supported",
            "total_symbols": 0,
            "inserted_rows": 0,
            "errors": []
        }
    
    db = SessionLocal()
    try:
        # Get symbols from DB
        symbols = _get_distinct_symbols_from_positions(db)
        logger.info(f"Auto-discovered {len(symbols)} symbols from positions")
        
        if not symbols:
            logger.warning("No symbols to process")
            return {
                "status": "no_symbols",
                "message": "No symbols found in positions",
                "total_symbols": 0,
                "inserted_rows": 0,
                "errors": []
            }
        
        # Process symbols
        total_inserted = 0
        errors = []
        
        for symbol in symbols:
            try:
                logger.info(f"Processing symbol: {symbol}")
                inserted_count = _fetch_symbol_with_retries(symbol, db, self.request.id)
                total_inserted += inserted_count
                logger.info(f"Successfully processed {symbol}: {inserted_count} rows")
                
            except Exception as e:
                error_msg = f"Failed to process {symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue with other symbols even if one fails
        
        result = {
            "status": "completed",
            "message": f"Processed {len(symbols)} symbols",
            "total_symbols": len(symbols),
            "inserted_rows": total_inserted,
            "errors": errors
        }
        
        logger.info(f"EOD refresh completed: {result}")
        return result
        
    finally:
        db.close()


@celery_app.task(name="prices.fetch_eod_for_symbols", bind=True)
def fetch_eod_for_symbols(self, symbols: Optional[List[str]] = None, since: Optional[str] = None) -> Dict[str, Any]:
    """
    Celery task to fetch EOD data for symbols with batching and retries.
    
    Args:
        symbols: List of symbols to fetch. If None, fetches all distinct symbols from positions.
        since: Date string (YYYY-MM-DD) to filter data. If provided, only returns data >= since.
        
    Returns:
        Summary dictionary with total_symbols, inserted_rows, since
    """
    logger.info(f"Starting EOD fetch task with symbols={symbols}, since={since}")
    
    # Parse since date if provided
    since_date = None
    if since:
        try:
            since_date = date.fromisoformat(since)
            logger.info(f"Filtering data since {since_date}")
        except ValueError:
            logger.error(f"Invalid since date format: {since}")
            raise ValueError(f"Invalid since date format: {since}")
    
    db = SessionLocal()
    try:
        # Get symbols from DB if not provided
        if symbols is None:
            symbols = _get_distinct_symbols_from_positions(db)
            logger.info(f"Auto-discovered {len(symbols)} symbols from positions")
        
        if not symbols:
            logger.warning("No symbols to process")
            return {
                "total_symbols": 0,
                "inserted_rows": 0,
                "since": since,
                "errors": []
            }
        
        # Process symbols in batches
        total_inserted = 0
        errors = []
        
        for batch_start in range(0, len(symbols), settings.eod_batch_size):
            batch_symbols = symbols[batch_start:batch_start + settings.eod_batch_size]
            logger.info(f"Processing batch {batch_start//settings.eod_batch_size + 1}: {len(batch_symbols)} symbols")
            
            batch_inserted, batch_errors = _process_symbol_batch(
                db, batch_symbols, since_date, self.request.id
            )
            
            total_inserted += batch_inserted
            errors.extend(batch_errors)
            
            # Pause between batches to be polite to Stooq
            if batch_start + settings.eod_batch_size < len(symbols):
                logger.debug(f"Pausing {settings.fetch_eod_batch_pause_seconds}s between batches")
                asyncio.run(asyncio.sleep(settings.fetch_eod_batch_pause_seconds))
        
        result = {
            "total_symbols": len(symbols),
            "inserted_rows": total_inserted,
            "since": since,
            "errors": errors
        }
        
        logger.info(f"EOD fetch completed: {result}")
        return result
        
    finally:
        db.close()


def _get_distinct_symbols_from_positions(db: Session) -> List[str]:
    """Get distinct symbols from positions table"""
    result = db.execute(text("SELECT DISTINCT symbol FROM positions ORDER BY symbol"))
    return [row[0] for row in result.fetchall()]


def _process_symbol_batch(
    db: Session, 
    symbols: List[str], 
    since_date: Optional[date], 
    task_id: str
) -> tuple[int, List[str]]:
    """Process a batch of symbols with retries"""
    repository = PriceEODRepository(db)
    total_inserted = 0
    errors = []
    
    for symbol in symbols:
        try:
            inserted = _fetch_symbol_with_retries(symbol, since_date, repository, task_id)
            total_inserted += inserted
            
        except Exception as e:
            error_msg = f"Failed to process {symbol}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    return total_inserted, errors


def _fetch_symbol_with_retries(
    symbol: str, 
    db: Session,
    task_id: str
) -> int:
    """Fetch data for a single symbol with exponential backoff retries"""
    repository = PriceEODRepository(db)
    last_exception = None
    
    # Simple retry logic (3 attempts with exponential backoff)
    retry_attempts = 3
    retry_delays = [1, 3, 9]  # seconds
    
    for attempt in range(retry_attempts):
        try:
            logger.debug(f"Fetching {symbol} (attempt {attempt + 1}/{retry_attempts})")
            
            # Fetch data from Stooq
            price_data = fetch_eod(symbol)
            
            if not price_data:
                logger.warning(f"No data returned for {symbol}")
                return 0
            
            # Upsert data
            inserted_count = repository.upsert_prices(symbol, price_data)
            
            # Log success with last date
            if price_data:
                last_date = max(row["date"] for row in price_data)
                logger.info(f"Successfully processed {symbol}: {inserted_count} rows, last date: {last_date}")
            else:
                logger.info(f"Successfully processed {symbol}: {inserted_count} rows")
            
            return inserted_count
            
        except StooqFetchError as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
            
            if attempt < retry_attempts - 1:
                backoff_delay = retry_delays[attempt]
                logger.debug(f"Retrying {symbol} in {backoff_delay}s")
                import time
                time.sleep(backoff_delay)
        except Exception as e:
            last_exception = e
            logger.error(f"Unexpected error for {symbol}: {e}")
            break  # Don't retry unexpected errors
    
    # All retries failed
    logger.error(f"All {retry_attempts} attempts failed for {symbol}")
    raise last_exception


# Synchronous wrapper for sync workers
def fetch_eod_for_symbols_sync(symbols: Optional[List[str]] = None, since: Optional[str] = None) -> Dict[str, Any]:
    """Synchronous wrapper for the Celery task"""
    return fetch_eod_for_symbols(symbols, since)
