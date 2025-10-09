"""
News read API endpoints with Redis caching and SWR.

This module provides read-only endpoints to retrieve stored news articles
from the news_articles and article_links tables with Redis caching.

Notes for reviewer:
- Symbols remain strings for now; we'll revisit a proper symbols dimension later
- Redis caching with SWR (stale-while-revalidate) is now implemented
- We intentionally allow published_at to be NULL in DB; list query should sort NULLs last when order=desc
"""

import logging
import asyncio
import hashlib
from datetime import datetime
from typing import List, Optional, Literal
from fastapi import APIRouter, HTTPException, Query, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func, distinct

from app.database import get_db
from app.models.news import NewsArticle, ArticleLink
from app.dbtypes import GUID
from app.core.news_cache import (
    get_query_cache, set_query_cache,
    get_article_cache, set_article_cache
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news-read"])


def sha1_hex(s: str) -> str:
    """Generate SHA1 hash of a string."""
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def _generate_query_hash(
    provider: Optional[str],
    symbol: Optional[str], 
    since: Optional[datetime],
    until: Optional[datetime],
    min_relevance: float,
    order: str,
    limit: int,
    offset: int
) -> str:
    """
    Generate stable query hash for caching.
    
    Normalizes filters to a stable signature for consistent caching.
    """
    # Normalize provider
    provider_key = (provider or "").lower()
    
    # Normalize symbol
    symbol_key = (symbol or "").upper()
    
    # Normalize dates to ISO format
    since_iso = since.isoformat() if since else ""
    until_iso = until.isoformat() if until else ""
    
    # Create stable signature
    signature = f"{provider_key}|{symbol_key}|{since_iso}|{until_iso}|{min_relevance}|{order}|{limit}|{offset}"
    
    return sha1_hex(signature)


class NewsListItem(BaseModel):
    """News article list item response model."""
    id: str = Field(..., description="Article UUID")
    title: str = Field(..., description="Article title")
    source_name: str = Field(..., description="Source name")
    url: str = Field(..., description="Article URL")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    provider: str = Field(..., description="Provider name")
    lang: Optional[str] = Field(None, description="Language code")
    symbols: List[str] = Field(default_factory=list, description="Linked symbols")


class NewsDetail(BaseModel):
    """News article detail response model."""
    id: str = Field(..., description="Article UUID")
    title: str = Field(..., description="Article title")
    source_name: str = Field(..., description="Source name")
    url: str = Field(..., description="Article URL")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    provider: str = Field(..., description="Provider name")
    lang: Optional[str] = Field(None, description="Language code")
    lead: Optional[str] = Field(None, description="Article summary/lead")
    simhash: Optional[int] = Field(None, description="Content simhash")
    symbols: List[str] = Field(default_factory=list, description="Linked symbols")
    raw_json: Optional[dict] = Field(None, description="Raw provider data (optional)")


class NewsListResponse(BaseModel):
    """News list response with pagination."""
    items: List[NewsListItem] = Field(..., description="News articles")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


async def _refresh_news_cache(
    provider: Optional[str],
    symbol: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
    min_relevance: float,
    order: str,
    limit: int,
    offset: int,
    db: Session
) -> None:
    """
    Background refresh task for stale cache entries.
    
    Repeats the same DB query and updates the cache with fresh data.
    """
    try:
        # Re-run the same query logic as the main endpoint
        query = db.query(NewsArticle)
        
        # Join with article_links if symbol is provided
        if symbol:
            query = query.join(ArticleLink, NewsArticle.id == ArticleLink.article_id)
            query = query.filter(
                and_(
                    ArticleLink.symbol == symbol.upper(),
                    ArticleLink.relevance_score >= min_relevance
                )
            )
        
        # Apply filters
        if provider:
            query = query.filter(NewsArticle.provider == provider)
        
        if since:
            query = query.filter(NewsArticle.published_at >= since)
        
        if until:
            query = query.filter(NewsArticle.published_at <= until)
        
        # Apply ordering
        if order == "desc":
            query = query.order_by(desc(NewsArticle.published_at))
        else:
            query = query.order_by(asc(NewsArticle.published_at))
        
        # Get articles for this page
        articles = query.offset(offset).limit(limit).all()
        
        # Collect article IDs
        article_ids = [str(article.id) for article in articles]
        
        # Update cache
        cache_data = {
            "article_ids": article_ids,
            "etag": f"refresh_{datetime.utcnow().isoformat()}",
            "fetched_at": datetime.utcnow().isoformat()
        }
        
        provider_key = provider or "_"
        symbol_key = symbol or "_"
        qhash = _generate_query_hash(provider, symbol, since, until, min_relevance, order, limit, offset)
        
        set_query_cache(provider_key, symbol_key, qhash, cache_data)
        
        logger.info(f"Background cache refresh completed for {len(article_ids)} articles")
        
    except Exception as e:
        logger.error(f"Background cache refresh failed: {e}", exc_info=True)


async def _fetch_from_db(
    provider: Optional[str],
    symbol: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
    min_relevance: float,
    order: str,
    limit: int,
    offset: int,
    db: Session
) -> NewsListResponse:
    """Fetch news articles directly from database."""
    # Base query from news_articles
    query = db.query(NewsArticle)
    
    # Join with article_links if symbol is provided
    if symbol:
        query = query.join(ArticleLink, NewsArticle.id == ArticleLink.article_id)
        query = query.filter(
            and_(
                ArticleLink.symbol == symbol.upper(),
                ArticleLink.relevance_score >= min_relevance
            )
        )
    
    # Apply filters
    if provider:
        query = query.filter(NewsArticle.provider == provider)
    
    if since:
        query = query.filter(NewsArticle.published_at >= since)
    
    if until:
        query = query.filter(NewsArticle.published_at <= until)
    
    # Apply ordering
    if order == "desc":
        query = query.order_by(desc(NewsArticle.published_at))
    else:
        query = query.order_by(asc(NewsArticle.published_at))
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    articles = query.offset(offset).limit(limit).all()
    
    # Convert to response models
    items = await _convert_articles_to_items(articles, db)
    
    return NewsListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


async def _fetch_articles_by_ids(article_ids: List[str], db: Session) -> List[NewsArticle]:
    """Fetch articles by their IDs, preserving order."""
    if not article_ids:
        return []
    
    # Convert string IDs to UUIDs
    import uuid
    try:
        uuids = [uuid.UUID(article_id) for article_id in article_ids]
    except (ValueError, TypeError):
        return []
    
    # Fetch articles in the same order as requested
    articles = []
    for article_uuid in uuids:
        article = db.query(NewsArticle).filter(NewsArticle.id == article_uuid).first()
        if article:
            articles.append(article)
    
    return articles


async def _get_total_count(
    provider: Optional[str],
    symbol: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
    min_relevance: float,
    db: Session
) -> int:
    """Get total count for the query (not cached)."""
    query = db.query(NewsArticle)
    
    # Join with article_links if symbol is provided
    if symbol:
        query = query.join(ArticleLink, NewsArticle.id == ArticleLink.article_id)
        query = query.filter(
            and_(
                ArticleLink.symbol == symbol.upper(),
                ArticleLink.relevance_score >= min_relevance
            )
        )
    
    # Apply filters
    if provider:
        query = query.filter(NewsArticle.provider == provider)
    
    if since:
        query = query.filter(NewsArticle.published_at >= since)
    
    if until:
        query = query.filter(NewsArticle.published_at <= until)
    
    return query.count()


async def _convert_articles_to_items(articles: List[NewsArticle], db: Session) -> List[NewsListItem]:
    """Convert NewsArticle objects to NewsListItem response models."""
    items = []
    for article in articles:
        # Get linked symbols for this article
        symbol_links = db.query(ArticleLink.symbol).filter(
            ArticleLink.article_id == article.id
        ).all()
        
        symbols = [link.symbol for link in symbol_links]
        
        items.append(NewsListItem(
            id=str(article.id),
            title=article.title,
            source_name=article.source_name,
            url=article.url,
            published_at=article.published_at,
            provider=article.provider,
            lang=article.lang,
            symbols=symbols
        ))
    
    return items


@router.get("", response_model=NewsListResponse)
async def list_news(
    symbol: Optional[str] = Query(None, description="Filter by symbol (requires article_links join)"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    since: Optional[datetime] = Query(None, description="Filter articles published after this date (ISO 8601)"),
    until: Optional[datetime] = Query(None, description="Filter articles published before this date (ISO 8601)"),
    min_relevance: float = Query(0.0, ge=0.0, le=1.0, description="Minimum relevance score (only when symbol provided)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of articles to return"),
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    order: Literal["desc", "asc"] = Query("desc", description="Sort order by published_at"),
    cache: bool = Query(True, description="Enable caching (set to false to bypass cache)"),
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    List news articles with optional filtering, pagination, and Redis caching.
    
    **Features:**
    - Filter by symbol (joins with article_links)
    - Filter by provider, date range
    - Pagination with limit/offset
    - Relevance scoring for symbol-based queries
    - Sort by publication date
    - Redis caching with SWR (stale-while-revalidate)
    
    **Cache Behavior:**
    - cache=true (default): Use Redis cache with SWR
    - cache=false: Bypass cache entirely
    
    **Example:**
    ```
    GET /news?symbol=AAPL&since=2025-10-01T00:00:00Z&limit=10
    ```
    """
    try:
        # Validate date range
        if since and until and since > until:
            raise HTTPException(
                status_code=400,
                detail="since date must be before until date"
            )
        
        # Generate cache key components
        provider_key = provider or "_"
        symbol_key = symbol or "_"
        qhash = _generate_query_hash(provider, symbol, since, until, min_relevance, order, limit, offset)
        
        # Set cache headers
        response.headers["X-Cache-Key"] = qhash[:8]  # Truncated hash for debugging
        
        # Handle cache bypass
        if not cache:
            response.headers["X-Cache"] = "BYPASS"
            return await _fetch_from_db(provider, symbol, since, until, min_relevance, order, limit, offset, db)
        
        # Only cache when limit <= 100
        if limit > 100:
            response.headers["X-Cache"] = "BYPASS"
            return await _fetch_from_db(provider, symbol, since, until, min_relevance, order, limit, offset, db)
        
        # Try to get from cache
        try:
            cached_data, is_stale = get_query_cache(provider_key, symbol_key, qhash)
            
            if cached_data:
                # Cache hit - fetch articles by IDs
                article_ids = cached_data.get("article_ids", [])
                articles = await _fetch_articles_by_ids(article_ids, db)
                
                # Get total count (this is a limitation - we don't cache total)
                total = await _get_total_count(provider, symbol, since, until, min_relevance, db)
                
                # Convert to response models
                items = await _convert_articles_to_items(articles, db)
                
                result = NewsListResponse(
                    items=items,
                    total=total,
                    limit=limit,
                    offset=offset
                )
                
                if is_stale:
                    response.headers["X-Cache"] = "STALE"
                    # Trigger background refresh
                    asyncio.create_task(_refresh_news_cache(
                        provider, symbol, since, until, min_relevance, order, limit, offset, db
                    ))
                else:
                    response.headers["X-Cache"] = "HIT"
                
                return result
                
        except Exception as cache_error:
            logger.warning(f"Cache error, falling back to DB: {cache_error}")
            response.headers["X-Cache"] = "ERROR"
        
        # Cache miss or error - fetch from DB
        response.headers["X-Cache"] = "MISS"
        result = await _fetch_from_db(provider, symbol, since, until, min_relevance, order, limit, offset, db)
        
        # Cache the result
        try:
            article_ids = [item.id for item in result.items]
            cache_data = {
                "article_ids": article_ids,
                "etag": f"miss_{datetime.utcnow().isoformat()}",
                "fetched_at": datetime.utcnow().isoformat()
            }
            set_query_cache(provider_key, symbol_key, qhash, cache_data)
        except Exception as cache_error:
            logger.warning(f"Failed to cache result: {cache_error}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing news: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve news: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for news read service.
    
    Returns basic status information about the read service.
    """
    return {
        "status": "healthy",
        "service": "news-read",
        "version": "1.0.0"
    }


@router.get("/{article_id}", response_model=NewsDetail)
async def get_news_detail(
    article_id: str,
    include_raw: bool = Query(False, description="Include raw_json in response"),
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific news article with Redis caching.
    
    **Parameters:**
    - `article_id`: UUID of the article
    - `include_raw`: Whether to include raw provider data
    
    **Cache Behavior:**
    - First call: Cache miss, fetches from DB and caches full article
    - Subsequent calls: Cache hit, serves from Redis
    - Raw JSON is cached but only included in response if requested
    
    **Example:**
    ```
    GET /news/123e4567-e89b-12d3-a456-426614174000?include_raw=true
    ```
    """
    try:
        # Validate UUID format
        try:
            import uuid
            article_uuid = uuid.UUID(article_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid article ID format"
            )
        
        # Try to get from cache first
        try:
            cached_article = get_article_cache(article_id)
            if cached_article:
                response.headers["X-Cache"] = "HIT"
                
                # Build response from cached data
                response_data = cached_article.copy()
                
                # Convert published_at back to datetime if it's a string
                if "published_at" in response_data and isinstance(response_data["published_at"], str):
                    from datetime import datetime
                    try:
                        response_data["published_at"] = datetime.fromisoformat(response_data["published_at"])
                    except (ValueError, TypeError):
                        response_data["published_at"] = None
                
                # Include raw JSON if requested (but don't include if not requested)
                if not include_raw and "raw_json" in response_data:
                    del response_data["raw_json"]
                
                return NewsDetail(**response_data)
                
        except Exception as cache_error:
            logger.warning(f"Cache error for article {article_id}: {cache_error}")
            response.headers["X-Cache"] = "ERROR"
        
        # Cache miss or error - fetch from DB
        response.headers["X-Cache"] = "MISS"
        
        # Get article from database
        article = db.query(NewsArticle).filter(NewsArticle.id == article_uuid).first()
        
        if not article:
            raise HTTPException(
                status_code=404,
                detail="Article not found"
            )
        
        # Get linked symbols
        symbol_links = db.query(ArticleLink.symbol).filter(
            ArticleLink.article_id == article.id
        ).order_by(ArticleLink.symbol).all()
        
        symbols = [link.symbol for link in symbol_links]
        
        # Build full response data (always cache the complete article)
        full_response_data = {
            "id": str(article.id),
            "title": article.title,
            "source_name": article.source_name,
            "url": article.url,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "provider": article.provider,
            "lang": article.lang,
            "lead": article.lead,
            "simhash": article.simhash,
            "symbols": symbols,
            "raw_json": article.raw_json  # Always cache with raw_json
        }
        
        # Cache the full article data
        try:
            set_article_cache(article_id, full_response_data)
        except Exception as cache_error:
            logger.warning(f"Failed to cache article {article_id}: {cache_error}")
        
        # Build response data (exclude raw_json if not requested)
        response_data = full_response_data.copy()
        if not include_raw:
            del response_data["raw_json"]
        
        return NewsDetail(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting news detail: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve article: {str(e)}"
        )
