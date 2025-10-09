"""
News planner for daily quota-aware news fetching.

This module provides planning functionality to select which symbols
to fetch news for based on portfolio weights and news drought analysis,
while respecting daily quotas and provider limits.

Key features:
- Portfolio-based symbol prioritization
- News drought analysis
- Quota-aware planning
- Redis-based idempotency
- Celery Beat integration
"""

import logging
import hashlib
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from app.database import get_db
from app.models.news import NewsArticle, ArticleLink
from app.models.position import Position
from app.models.price import Price
from app.core.config import settings
from app.core.news_cache import get_redis_client

logger = logging.getLogger(__name__)


@dataclass
class PlannedQuery:
    """Represents a planned news query for a symbol."""
    symbol: str
    query: str
    provider: str
    priority: float


def sha1_hex(s: str) -> str:
    """Generate SHA1 hash of a string."""
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def plan_daily_news(fetch_date: Optional[date] = None) -> List[PlannedQuery]:
    """
    Plan daily news fetching based on portfolio weights and news drought.
    
    Args:
        fetch_date: Date to plan for (defaults to today)
        
    Returns:
        List of planned queries sorted by priority (highest first)
    """
    if fetch_date is None:
        fetch_date = date.today()
    
    logger.info(f"Planning daily news for {fetch_date}")
    
    try:
        db = next(get_db())
        
        # Get distinct symbols from portfolio
        symbols_data = _get_symbols_with_weights(db)
        
        if not symbols_data:
            logger.warning("No symbols found in portfolio")
            return []
        
        # Calculate priorities for each symbol
        planned_queries = []
        for symbol_data in symbols_data:
            symbol = symbol_data['symbol']
            portfolio_weight = symbol_data['weight']
            drought_days = _calculate_news_drought(db, symbol)
            
            # Calculate priority: 60% portfolio weight + 40% news drought
            priority = 0.6 * portfolio_weight + 0.4 * drought_days
            
            # Build query string
            query = _build_query_string(symbol)
            
            planned_query = PlannedQuery(
                symbol=symbol,
                query=query,
                provider=settings.news_provider_default,
                priority=priority
            )
            
            planned_queries.append(planned_query)
        
        # Sort by priority (highest first)
        planned_queries.sort(key=lambda x: x.priority, reverse=True)
        
        # Apply daily symbol limit
        max_symbols = settings.news_daily_symbols
        if len(planned_queries) > max_symbols:
            planned_queries = planned_queries[:max_symbols]
            logger.info(f"Limited to top {max_symbols} symbols by priority")
        
        logger.info(f"Planned {len(planned_queries)} news queries for {fetch_date}")
        
        db.close()
        return planned_queries
        
    except Exception as e:
        logger.error(f"Error planning daily news: {e}", exc_info=True)
        return []


def _get_symbols_with_weights(db: Session) -> List[Dict[str, Any]]:
    """
    Get symbols from portfolio with their weights.
    
    Uses positions table as primary source, with prices as fallback.
    """
    try:
        # Try to get symbols from positions table
        positions = db.query(Position.symbol, func.count(Position.id).label('count')).group_by(Position.symbol).all()
        
        if positions:
            # Calculate normalized weights based on position count
            total_positions = sum(pos.count for pos in positions)
            max_count = max(pos.count for pos in positions) if positions else 1
            
            symbols_data = []
            for pos in positions:
                # Normalize weight: position count / max count
                weight = pos.count / max_count if max_count > 0 else 1.0
                
                symbols_data.append({
                    'symbol': pos.symbol,
                    'weight': weight,
                    'source': 'positions'
                })
            
            logger.info(f"Found {len(symbols_data)} symbols from positions table")
            return symbols_data
        
        # Fallback to prices table if no positions
        prices = db.query(Price.symbol).distinct().all()
        
        if prices:
            symbols_data = []
            for price in prices:
                symbols_data.append({
                    'symbol': price.symbol,
                    'weight': 1.0,  # Default weight
                    'source': 'prices'
                })
            
            logger.info(f"Found {len(symbols_data)} symbols from prices table (fallback)")
            return symbols_data
        
        logger.warning("No symbols found in positions or prices tables")
        return []
        
    except Exception as e:
        logger.error(f"Error getting symbols with weights: {e}", exc_info=True)
        return []


def _calculate_news_drought(db: Session, symbol: str) -> float:
    """
    Calculate news drought days for a symbol.
    
    Returns normalized drought days (0-1 scale, higher = more drought).
    """
    try:
        # Get latest news article for this symbol
        latest_news = db.query(NewsArticle.published_at).join(
            ArticleLink, NewsArticle.id == ArticleLink.article_id
        ).filter(
            ArticleLink.symbol == symbol.upper()
        ).order_by(desc(NewsArticle.published_at)).first()
        
        if latest_news and latest_news.published_at:
            # Calculate days since latest news
            # Handle timezone-aware vs timezone-naive datetimes
            now = datetime.utcnow()
            published_at = latest_news.published_at
            
            # Make both datetimes timezone-aware for comparison
            import pytz
            utc = pytz.UTC
            
            if published_at.tzinfo is None:
                # published_at is timezone-naive, assume UTC
                published_at = utc.localize(published_at)
            if now.tzinfo is None:
                # now is timezone-naive, make it timezone-aware
                now = utc.localize(now)
            
            days_since = (now - published_at).days
        else:
            # No news found, assume maximum drought
            days_since = 30
        
        # Normalize to 0-1 scale (30 days = 1.0)
        drought_norm = min(days_since / 30.0, 1.0)
        
        return drought_norm
        
    except Exception as e:
        logger.error(f"Error calculating news drought for {symbol}: {e}", exc_info=True)
        return 1.0  # Default to maximum drought on error


def _build_query_string(symbol: str) -> str:
    """
    Build search query string for a symbol.
    
    For now, just use the symbol. In the future, could include company names.
    """
    # Simple query: just the symbol
    # Future enhancement: add company name if available
    return f'"{symbol}"'


def is_query_planned(fetch_date: date, provider: str, symbol: str, query: str) -> bool:
    """
    Check if a query has already been planned for the given date.
    
    Uses Redis SETNX for idempotency.
    """
    try:
        redis_client = get_redis_client()
        
        # Generate cache key
        date_str = fetch_date.strftime("%Y%m%d")
        query_hash = sha1_hex(query)
        key = f"news:plan:{date_str}:{provider}:{symbol}:{query_hash}"
        
        # Check if key exists (SETNX returns 1 if key was set, 0 if it existed)
        result = redis_client.set(key, "1", nx=True, ex=86400)  # 24h TTL
        
        return result == 0  # True if key already existed (already planned)
        
    except Exception as e:
        logger.error(f"Error checking query planning status: {e}", exc_info=True)
        return False  # On error, assume not planned to allow retry


def mark_query_planned(fetch_date: date, provider: str, symbol: str, query: str) -> bool:
    """
    Mark a query as planned for the given date.
    
    Returns True if successfully marked, False if already planned.
    """
    try:
        redis_client = get_redis_client()
        
        # Generate cache key
        date_str = fetch_date.strftime("%Y%m%d")
        query_hash = sha1_hex(query)
        key = f"news:plan:{date_str}:{provider}:{symbol}:{query_hash}"
        
        # Set key with TTL (SETNX returns 1 if key was set, 0 if it existed)
        result = redis_client.set(key, "1", nx=True, ex=86400)  # 24h TTL
        
        if result:
            logger.debug(f"Marked query as planned: {key}")
            return True
        else:
            logger.debug(f"Query already planned: {key}")
            return False
            
    except Exception as e:
        logger.error(f"Error marking query as planned: {e}", exc_info=True)
        return False


def get_planning_stats(fetch_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Get statistics about planned queries for a date.
    """
    if fetch_date is None:
        fetch_date = date.today()
    
    try:
        redis_client = get_redis_client()
        date_str = fetch_date.strftime("%Y%m%d")
        
        # Count planned queries for this date
        pattern = f"news:plan:{date_str}:*"
        keys = redis_client.keys(pattern)
        
        # Parse keys to get statistics
        providers = set()
        symbols = set()
        
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 5:
                providers.add(parts[3])
                symbols.add(parts[4])
        
        return {
            "date": date_str,
            "total_planned": len(keys),
            "providers": list(providers),
            "symbols": list(symbols),
            "symbol_count": len(symbols)
        }
        
    except Exception as e:
        logger.error(f"Error getting planning stats: {e}", exc_info=True)
        return {
            "date": fetch_date.strftime("%Y%m%d"),
            "total_planned": 0,
            "providers": [],
            "symbols": [],
            "symbol_count": 0,
            "error": str(e)
        }


def clear_planning_data(fetch_date: Optional[date] = None) -> int:
    """
    Clear planning data for a date (for testing/debugging).
    """
    if fetch_date is None:
        fetch_date = date.today()
    
    try:
        redis_client = get_redis_client()
        date_str = fetch_date.strftime("%Y%m%d")
        
        # Clear all planning keys for this date
        pattern = f"news:plan:{date_str}:*"
        keys = redis_client.keys(pattern)
        
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"Cleared {deleted} planning keys for {date_str}")
            return deleted
        else:
            return 0
            
    except Exception as e:
        logger.error(f"Error clearing planning data: {e}", exc_info=True)
        return 0
