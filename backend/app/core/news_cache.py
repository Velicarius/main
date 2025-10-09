"""
News cache primitives with Redis and SWR (stale-while-revalidate).

This module provides caching functionality for news queries and articles
using Redis with SWR pattern for optimal performance.

Features:
- Query result caching with SWR (stale-while-revalidate)
- Article payload caching with long TTL
- Single-flight locking to prevent duplicate upstream calls
- Quota counters for provider rate limiting
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=0,
            decode_responses=True
        )
    return _redis_client


def _normalize_symbol(symbol: Optional[str]) -> str:
    """Normalize symbol for cache key (use '_' for None)."""
    return symbol or "_"


def _generate_query_key(provider: str, symbol: Optional[str], qhash: str) -> str:
    """Generate cache key for query results."""
    normalized_symbol = _normalize_symbol(symbol)
    return f"news:q:{provider}:{normalized_symbol}:{qhash}"


def _generate_article_key(article_id: str) -> str:
    """Generate cache key for article payload."""
    return f"news:article:{article_id}"


def _generate_lock_key(provider: str, symbol: Optional[str], qhash: str) -> str:
    """Generate cache key for single-flight lock."""
    normalized_symbol = _normalize_symbol(symbol)
    return f"news:lock:{provider}:{normalized_symbol}:{qhash}"


def _generate_quota_daily_key(provider: str, date: str) -> str:
    """Generate cache key for daily quota counter."""
    return f"news:quota:{provider}:{date}"


def _generate_quota_minute_key(provider: str, date_minute: str) -> str:
    """Generate cache key for minute quota counter."""
    return f"news:minute:{provider}:{date_minute}"


def get_query_cache(provider: str, symbol: Optional[str], qhash: str) -> Tuple[Optional[Dict], bool]:
    """
    Get cached query results with SWR (stale-while-revalidate) support.
    
    Args:
        provider: Provider name (e.g., 'newsapi', 'alphavantage')
        symbol: Symbol to filter by (None for all symbols)
        qhash: Query hash for cache key
        
    Returns:
        Tuple of (cached_value, is_stale)
        - cached_value: Dict with article_ids, etag, fetched_at or None if not found
        - is_stale: True if data is stale but still within SWR window
        
    Cache behavior:
    - TTL = 900s (15 minutes)
    - SWR window = +2700s (45 minutes total)
    - Fresh: 0-15 minutes
    - Stale: 15-60 minutes (serve cached, refresh in background)
    - Expired: >60 minutes (no cache)
    """
    try:
        redis_client = get_redis_client()
        key = _generate_query_key(provider, symbol, qhash)
        
        # Get cached data
        cached_data = redis_client.get(key)
        if not cached_data:
            return None, False
        
        # Parse JSON data
        try:
            data = json.loads(cached_data)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid JSON in cache key {key}")
            return None, False
        
        # Check TTL to determine if stale
        ttl = redis_client.ttl(key)
        
        if ttl > 0:
            # Still within TTL, data is fresh
            return data, False
        elif ttl == -1:
            # Key exists but no TTL set (shouldn't happen)
            logger.warning(f"Cache key {key} has no TTL")
            return data, False
        else:
            # TTL expired but key still exists (within SWR window)
            return data, True
            
    except Exception as e:
        logger.error(f"Error getting query cache: {e}")
        return None, False


def set_query_cache(
    provider: str, 
    symbol: Optional[str], 
    qhash: str, 
    value: Dict, 
    ttl_seconds: int = 900, 
    swr_window: int = 2700
) -> None:
    """
    Set cached query results with TTL.
    
    Args:
        provider: Provider name
        symbol: Symbol to filter by (None for all symbols)
        qhash: Query hash for cache key
        value: Data to cache (dict with article_ids, etag, fetched_at)
        ttl_seconds: TTL in seconds (default 900s = 15 minutes)
        swr_window: SWR window in seconds (default 2700s = 45 minutes total)
    """
    try:
        redis_client = get_redis_client()
        key = _generate_query_key(provider, symbol, qhash)
        
        # Add fetched_at timestamp if not present
        if "fetched_at" not in value:
            value["fetched_at"] = datetime.utcnow().isoformat()
        
        # Store with TTL
        redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(value)
        )
        
        logger.debug(f"Cached query result for {key} with TTL {ttl_seconds}s")
        
    except Exception as e:
        logger.error(f"Error setting query cache: {e}")


def get_article_cache(article_id: str) -> Optional[Dict]:
    """
    Get cached article payload.
    
    Args:
        article_id: Article UUID string
        
    Returns:
        Cached article data or None if not found
    """
    try:
        redis_client = get_redis_client()
        key = _generate_article_key(article_id)
        
        cached_data = redis_client.get(key)
        if not cached_data:
            return None
        
        try:
            return json.loads(cached_data)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid JSON in article cache key {key}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting article cache: {e}")
        return None


def set_article_cache(article_id: str, doc: Dict, ttl_seconds: int = 604800) -> None:
    """
    Set cached article payload with long TTL.
    
    Args:
        article_id: Article UUID string
        doc: Article data to cache
        ttl_seconds: TTL in seconds (default 604800s = 7 days)
    """
    try:
        redis_client = get_redis_client()
        key = _generate_article_key(article_id)
        
        redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(doc)
        )
        
        logger.debug(f"Cached article {article_id} with TTL {ttl_seconds}s")
        
    except Exception as e:
        logger.error(f"Error setting article cache: {e}")


def acquire_singleflight(provider: str, symbol: Optional[str], qhash: str, ttl: int = 60) -> bool:
    """
    Acquire single-flight lock to prevent duplicate upstream calls.
    
    Args:
        provider: Provider name
        symbol: Symbol to filter by (None for all symbols)
        qhash: Query hash for cache key
        ttl: Lock TTL in seconds (default 60s)
        
    Returns:
        True if lock acquired, False if already locked
    """
    try:
        redis_client = get_redis_client()
        key = _generate_lock_key(provider, symbol, qhash)
        
        # Try to set lock with TTL (NX = only if not exists)
        result = redis_client.set(key, "1", nx=True, ex=ttl)
        
        if result:
            logger.debug(f"Acquired single-flight lock for {key}")
            return True
        else:
            logger.debug(f"Single-flight lock already exists for {key}")
            return False
            
    except Exception as e:
        logger.error(f"Error acquiring single-flight lock: {e}")
        return False


def release_singleflight(provider: str, symbol: Optional[str], qhash: str) -> None:
    """
    Release single-flight lock.
    
    Args:
        provider: Provider name
        symbol: Symbol to filter by (None for all symbols)
        qhash: Query hash for cache key
    """
    try:
        redis_client = get_redis_client()
        key = _generate_lock_key(provider, symbol, qhash)
        
        redis_client.delete(key)
        logger.debug(f"Released single-flight lock for {key}")
        
    except Exception as e:
        logger.error(f"Error releasing single-flight lock: {e}")


def inc_daily(provider: str) -> int:
    """
    Increment daily quota counter for provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Current daily count
    """
    try:
        redis_client = get_redis_client()
        today = datetime.utcnow().strftime("%Y%m%d")
        key = _generate_quota_daily_key(provider, today)
        
        # Increment and get current value
        count = redis_client.incr(key)
        
        # Set TTL to end of day (86400 seconds = 24 hours)
        redis_client.expire(key, 86400)
        
        logger.debug(f"Incremented daily quota for {provider}: {count}")
        return count
        
    except Exception as e:
        logger.error(f"Error incrementing daily quota: {e}")
        return 0


def inc_minute(provider: str) -> int:
    """
    Increment minute quota counter for provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Current minute count
    """
    try:
        redis_client = get_redis_client()
        now = datetime.utcnow()
        minute_key = now.strftime("%Y%m%d%H%M")
        key = _generate_quota_minute_key(provider, minute_key)
        
        # Increment and get current value
        count = redis_client.incr(key)
        
        # Set TTL to end of minute (60 seconds)
        redis_client.expire(key, 60)
        
        logger.debug(f"Incremented minute quota for {provider}: {count}")
        return count
        
    except Exception as e:
        logger.error(f"Error incrementing minute quota: {e}")
        return 0


def get_quota_state(provider: str) -> Dict[str, Any]:
    """
    Get current quota state for provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Dict with daily_count, minute_count, and timestamps
    """
    try:
        redis_client = get_redis_client()
        now = datetime.utcnow()
        
        # Get daily count
        today = now.strftime("%Y%m%d")
        daily_key = _generate_quota_daily_key(provider, today)
        daily_count = redis_client.get(daily_key) or "0"
        
        # Get minute count
        minute_key = now.strftime("%Y%m%d%H%M")
        minute_cache_key = _generate_quota_minute_key(provider, minute_key)
        minute_count = redis_client.get(minute_cache_key) or "0"
        
        return {
            "provider": provider,
            "daily_count": int(daily_count),
            "minute_count": int(minute_count),
            "date": today,
            "minute": minute_key,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting quota state: {e}")
        return {
            "provider": provider,
            "daily_count": 0,
            "minute_count": 0,
            "date": datetime.utcnow().strftime("%Y%m%d"),
            "minute": datetime.utcnow().strftime("%Y%m%d%H%M"),
            "timestamp": datetime.utcnow().isoformat()
        }


def clear_cache_pattern(pattern: str) -> int:
    """
    Clear cache entries matching a pattern.
    
    Args:
        pattern: Redis pattern (e.g., "news:q:*", "news:article:*")
        
    Returns:
        Number of keys deleted
    """
    try:
        redis_client = get_redis_client()
        keys = redis_client.keys(pattern)
        
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"Cleared {deleted} cache keys matching pattern {pattern}")
            return deleted
        else:
            return 0
            
    except Exception as e:
        logger.error(f"Error clearing cache pattern {pattern}: {e}")
        return 0


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dict with cache statistics
    """
    try:
        redis_client = get_redis_client()
        
        # Count different cache types
        query_keys = redis_client.keys("news:q:*")
        article_keys = redis_client.keys("news:article:*")
        lock_keys = redis_client.keys("news:lock:*")
        quota_keys = redis_client.keys("news:quota:*")
        
        return {
            "query_cache_count": len(query_keys),
            "article_cache_count": len(article_keys),
            "lock_count": len(lock_keys),
            "quota_count": len(quota_keys),
            "total_keys": len(query_keys) + len(article_keys) + len(lock_keys) + len(quota_keys),
            "redis_info": redis_client.info()
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            "query_cache_count": 0,
            "article_cache_count": 0,
            "lock_count": 0,
            "quota_count": 0,
            "total_keys": 0,
            "error": str(e)
        }

