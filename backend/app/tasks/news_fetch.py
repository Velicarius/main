"""
News fetch task for idempotent news retrieval with ETag/IMS support.

This module provides the fetch_news Celery task that:
- Uses conditional requests (ETag or If-Modified-Since)
- Normalizes items and calls ingest
- Updates query cache and quota counters
- Is idempotent and shadow-safe
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from app.celery_app import celery_app
from app.core.news_cache import (
    get_query_cache, 
    set_query_cache, 
    acquire_singleflight, 
    inc_daily, 
    inc_minute
)
from app.services.news_ingest import normalize_item, ingest_articles
from app.database import SessionLocal
from app.models.news import NewsArticle, ArticleLink
from app.core.config import settings

logger = logging.getLogger(__name__)


def sha1_hex(s: str) -> str:
    """Generate SHA1 hash of a string."""
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def now_iso() -> str:
    """Get current UTC time as ISO string with Z suffix."""
    import pytz
    utc = pytz.UTC
    return utc.localize(datetime.utcnow()).isoformat()


def parsed_utc(s: Optional[str]) -> Optional[datetime]:
    """
    Robust parse of ISO datetime string to UTC datetime.
    
    Args:
        s: ISO datetime string (may have Z suffix)
        
    Returns:
        UTC datetime object or None on bad input
    """
    if not s:
        return None
    
    try:
        # Handle Z suffix
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        
        # Parse ISO format
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse datetime: {s}")
        return None


def latest_published_at_for_symbol(symbol: str) -> datetime:
    """
    Get the latest published_at for a symbol from news_articles.
    
    Args:
        symbol: Stock symbol to query
        
    Returns:
        Latest published_at datetime or now-7days as fallback (both TZ-aware UTC)
    """
    import pytz
    utc = pytz.UTC
    
    try:
        with db_session() as db:
            # Query latest news for this symbol
            latest_news = db.query(NewsArticle.published_at).join(
                ArticleLink, NewsArticle.id == ArticleLink.article_id
            ).filter(
                ArticleLink.symbol == symbol.upper()
            ).order_by(NewsArticle.published_at.desc()).first()
            
            if latest_news and latest_news.published_at:
                # Ensure TZ-aware UTC
                published_at = latest_news.published_at
                if published_at.tzinfo is None:
                    published_at = utc.localize(published_at)
                return published_at
            else:
                # Fallback: 7 days ago (TZ-aware UTC)
                return utc.localize(datetime.utcnow() - timedelta(days=7))
                
    except Exception as e:
        logger.error(f"Error getting latest published_at for {symbol}: {e}")
        return utc.localize(datetime.utcnow() - timedelta(days=7))


def _get_article_ids_for_cache(provider: str, symbol: str, published_after: Optional[datetime]) -> List[str]:
    """
    Get article IDs for cache with stable ordering (published_at DESC, id DESC).
    
    Args:
        provider: Provider name
        symbol: Stock symbol
        published_after: Only include articles published after this date
        
    Returns:
        List of article IDs in stable order
    """
    try:
        with db_session() as db:
            # Build query with stable ordering
            query = db.query(NewsArticle.id).join(
                ArticleLink, NewsArticle.id == ArticleLink.article_id
            ).filter(
                NewsArticle.provider == provider,
                ArticleLink.symbol == symbol.upper()
            )
            
            # Add published_after filter if provided
            if published_after:
                query = query.filter(NewsArticle.published_at >= published_after)
            
            # Order by published_at DESC, then id DESC for stable ordering
            query = query.order_by(
                NewsArticle.published_at.desc(),
                NewsArticle.id.desc()
            ).limit(100)  # Reasonable limit for cache
            
            # Execute query and return IDs as strings
            results = query.all()
            return [str(article_id[0]) for article_id in results]
            
    except Exception as e:
        logger.error(f"Error getting article IDs for cache: {e}")
        return []


@contextmanager
def db_session():
    """Database session context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_provider_client(provider: str):
    """
    Get provider client instance.
    
    Args:
        provider: Provider name (e.g., 'newsapi', 'finnhub')
        
    Returns:
        Provider client instance
        
    Raises:
        ValueError: If provider is not supported
    """
    if provider == 'newsapi':
        from app.marketdata.news_providers.newsapi import NewsAPIProvider
        api_key = settings.newsapi_api_key
        if not api_key:
            raise ValueError("NewsAPI key not configured")
        return NewsAPIProvider(api_key=api_key, timeout=settings.news_timeout)
    
    elif provider == 'finnhub':
        from app.marketdata.news_providers.finnhub import FinnhubProvider
        api_key = settings.finnhub_api_key
        if not api_key:
            raise ValueError("Finnhub API key not configured")
        return FinnhubProvider(api_key=api_key, timeout=settings.news_timeout)
    
    elif provider == 'alphavantage':
        from app.marketdata.news_providers.alphavantage import AlphaVantageProvider
        api_key = settings.alphavantage_api_key
        if not api_key:
            raise ValueError("AlphaVantage API key not configured")
        return AlphaVantageProvider(api_key=api_key, timeout=settings.news_timeout)
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")


@celery_app.task(
    name="news.fetch", 
    autoretry_for=(ConnectionError, TimeoutError, OSError),  # Only retry network errors
    retry_backoff=True, 
    max_retries=3,
    retry_kwargs={'max_retries': 3, 'countdown': 60}
)
def fetch_news(provider: str, symbol: str, query: str) -> Dict[str, Any]:
    """
    Idempotent fetch task with conditional requests and cache updates.
    
    Args:
        provider: News provider name (e.g., 'newsapi')
        symbol: Stock symbol to fetch news for
        query: Search query string
        
    Returns:
        Dict with fetch results and status
    """
    start_time = datetime.utcnow()
    
    try:
        # 1) Build qhash, acquire single-flight lock
        qhash = sha1_hex(" ".join(query.lower().split()))
        if not acquire_singleflight(provider, symbol, qhash, ttl=300):  # 5 minutes TTL for slow providers
            logger.info(f"Single-flight lock already exists for {provider}:{symbol}:{qhash[:8]}")
            return {"status": "skipped", "reason": "singleflight-lock"}
        
        # Ensure lock is released on exit
        try:
            # 2) Get conditional params from cache
            cache, stale = get_query_cache(provider, symbol, qhash)
            etag = cache.get("etag") if cache else None
            fetched_at_iso = cache.get("fetched_at") if cache else None
            
            # Determine published_after date
            if fetched_at_iso:
                published_after = parsed_utc(fetched_at_iso)
            else:
                published_after = latest_published_at_for_symbol(symbol)
            
            # 3) Get provider client and make conditional request
            client = get_provider_client(provider)
            
            logger.info(f"Fetching news for {symbol} from {provider} with query_hash: {qhash[:8]}")
            
            # Make conditional request using the provider's conditional method
            import asyncio
            resp = asyncio.run(client.fetch_news_conditional(
                query=query,
                published_after=published_after,
                etag=etag,
                limit=50  # Reasonable limit for fetch tasks
            ))
            
            # 4) Handle not-modified response
            if resp.get("status") == "not_modified":
                logger.info(f"No new content for {symbol} from {provider}")
                set_query_cache(provider, symbol, qhash, {
                    "article_ids": cache["article_ids"] if cache else [],
                    "etag": etag,
                    "fetched_at": now_iso()
                })
                return {"status": "not_modified", "provider": provider, "symbol": symbol}
            
            # 5) Normalize and ingest articles
            items = resp.get("items", [])
            if not items:
                logger.info(f"No articles returned for {symbol} from {provider}")
                return {"status": "ok", "inserted": 0, "duplicates": 0, "linked": 0}
            
            # Normalize items
            normalized = []
            for item in items:
                try:
                    normalized_item = normalize_item(item)
                    normalized.append(normalized_item)
                except Exception as e:
                    logger.error(f"Error normalizing item: {e}")
                    continue
            
            # Ingest articles
            with db_session() as db:
                result = ingest_articles(db, provider=provider, items=[item.__dict__ for item in normalized], default_symbols=[symbol])
            
            # 6) Update query cache and quotas
            # Get article IDs with stable ordering (published_at DESC, id DESC)
            article_ids = _get_article_ids_for_cache(provider, symbol, published_after)
            
            set_query_cache(provider, symbol, qhash, {
                "article_ids": article_ids,
                "etag": resp.get("etag"),
                "fetched_at": now_iso()
            })
            
            # Update quotas only on successful fetch with items
            if items:
                inc_daily(provider)
                inc_minute(provider)
            
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Fetch completed for {symbol} from {provider}: {result.get('inserted', 0)} inserted, {result.get('duplicates', 0)} duplicates, {len(items)} items, {duration*1000:.0f}ms")
            
            return {
                "status": "ok",
                "provider": provider,
                "symbol": symbol,
                "query": query,
                "inserted": result.get("inserted", 0),
                "duplicates": result.get("duplicates", 0),
                "linked": result.get("linked", 0),
                "items_fetched": len(items),
                "duration_seconds": duration
            }
            
        finally:
            # Always release the single-flight lock
            from app.core.news_cache import release_singleflight
            release_singleflight(provider, symbol, qhash)
        
    except ValueError as e:
        # Provider not supported or misconfigured - don't retry
        logger.error(f"Provider error for {provider}:{symbol}: {e}")
        return {"status": "error", "reason": str(e), "provider": provider, "symbol": symbol}
        
    except (ConnectionError, TimeoutError, OSError) as e:
        # Network errors - let Celery retry
        logger.error(f"Network error for {provider}:{symbol}: {e}", exc_info=True)
        raise  # This will trigger Celery retry
        
    except Exception as e:
        # Other errors - don't retry (likely permanent)
        logger.error(f"Permanent error for {provider}:{symbol}: {e}", exc_info=True)
        return {"status": "error", "reason": str(e), "provider": provider, "symbol": symbol}
