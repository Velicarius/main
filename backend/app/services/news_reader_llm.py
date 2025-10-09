"""
LLM-compatible news reader service with shadow mode filtering.

This service provides news data specifically for LLM consumption with
shadow mode filtering to exclude certain providers from LLM responses
while keeping them available in public APIs.

Key features:
- Shadow mode filtering for LLM compatibility
- Feature flag integration
- Fail-open strategy for reliability
- Contract-compatible responses
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc

from app.database import get_db
from app.models.news import NewsArticle, ArticleLink
from app.core.config import settings
from app.core.news_cache import get_query_cache, set_query_cache, get_article_cache, set_article_cache
from app.services.news_config import get_effective_shadow_providers

logger = logging.getLogger(__name__)


class NewsRepositoryLLM:
    """
    LLM-compatible news repository with shadow mode filtering.
    
    This repository provides the same interface as the public news API
    but applies shadow mode filtering to exclude certain providers
    from LLM responses while maintaining contract compatibility.
    """
    
    def __init__(self, db: Session):
        self.db = db
        # Get shadow providers from config service instead of env
        self.shadow_providers = get_effective_shadow_providers(db)
        self.cache_enabled = settings.news_read_cache_enabled
        self.shadow_mode_enabled = settings.news_provider_shadow_mode
    
    def _is_shadow_provider(self, provider: str) -> bool:
        """Check if provider is in shadow mode."""
        if not self.shadow_mode_enabled:
            return False
        return provider.lower() in self.shadow_providers
    
    def _apply_shadow_filter(self, query):
        """Apply shadow mode filtering to query."""
        if not self.shadow_mode_enabled or not self.shadow_providers:
            return query
        
        # Exclude shadow providers
        for provider in self.shadow_providers:
            query = query.filter(NewsArticle.provider != provider)
        
        return query
    
    def _generate_query_hash(
        self,
        provider: Optional[str],
        symbol: Optional[str], 
        since: Optional[datetime],
        until: Optional[datetime],
        min_relevance: float,
        order: str,
        limit: int,
        offset: int
    ) -> str:
        """Generate stable query hash for caching."""
        import hashlib
        
        # Normalize provider
        provider_key = (provider or "").lower()
        
        # Normalize symbol
        symbol_key = (symbol or "").upper()
        
        # Normalize dates to ISO format
        since_iso = since.isoformat() if since else ""
        until_iso = until.isoformat() if until else ""
        
        # Create stable signature
        signature = f"{provider_key}|{symbol_key}|{since_iso}|{until_iso}|{min_relevance}|{order}|{limit}|{offset}|llm"
        
        return hashlib.sha1(signature.encode('utf-8')).hexdigest()
    
    def list_news(
        self,
        symbol: Optional[str] = None,
        provider: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        min_relevance: float = 0.0,
        limit: int = 50,
        offset: int = 0,
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        List news articles with LLM-compatible filtering.
        
        Returns the same format as the public API but with shadow mode filtering applied.
        """
        try:
            # Generate cache key
            provider_key = provider or "_"
            symbol_key = symbol or "_"
            qhash = self._generate_query_hash(provider, symbol, since, until, min_relevance, order, limit, offset)
            
            # Try cache first if enabled
            if self.cache_enabled:
                try:
                    cached_data, is_stale = get_query_cache(provider_key, symbol_key, qhash)
                    if cached_data:
                        # Fetch articles by IDs from cache
                        article_ids = cached_data.get("article_ids", [])
                        articles = self._fetch_articles_by_ids(article_ids)
                        
                        # Apply shadow filtering to cached results
                        filtered_articles = [a for a in articles if not self._is_shadow_provider(a.provider)]
                        
                        # Get total count (not cached)
                        total = self._get_total_count(provider, symbol, since, until, min_relevance)
                        
                        # Convert to response format
                        items = self._convert_articles_to_items(filtered_articles)
                        
                        return {
                            "items": items,
                            "total": total,
                            "limit": limit,
                            "offset": offset,
                            "cached": True,
                            "stale": is_stale
                        }
                except Exception as cache_error:
                    logger.warning(f"Cache error in LLM reader, falling back to DB: {cache_error}")
            
            # Fetch from database
            query = self.db.query(NewsArticle)
            
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
            
            # Apply shadow mode filtering
            query = self._apply_shadow_filter(query)
            
            # Apply ordering
            if order == "desc":
                query = query.order_by(desc(NewsArticle.published_at))
            else:
                query = query.order_by(asc(NewsArticle.published_at))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            articles = query.offset(offset).limit(limit).all()
            
            # Convert to response format
            items = self._convert_articles_to_items(articles)
            
            # Cache result if enabled
            if self.cache_enabled:
                try:
                    article_ids = [item["id"] for item in items]
                    cache_data = {
                        "article_ids": article_ids,
                        "etag": f"llm_{datetime.utcnow().isoformat()}",
                        "fetched_at": datetime.utcnow().isoformat()
                    }
                    set_query_cache(provider_key, symbol_key, qhash, cache_data)
                except Exception as cache_error:
                    logger.warning(f"Failed to cache LLM result: {cache_error}")
            
            return {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset,
                "cached": False,
                "stale": False
            }
            
        except Exception as e:
            logger.error(f"Error in LLM news list: {e}", exc_info=True)
            # Fail-open: return empty result
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "cached": False,
                "stale": False,
                "error": str(e)
            }
    
    def get_news_detail(self, article_id: str, include_raw: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get detailed news article with LLM-compatible filtering.
        
        Returns None if article is from shadow provider.
        """
        try:
            # Try cache first if enabled
            if self.cache_enabled:
                try:
                    cached_article = get_article_cache(article_id)
                    if cached_article:
                        # Check if provider is shadow
                        provider = cached_article.get("provider", "").lower()
                        if self._is_shadow_provider(provider):
                            return None
                        
                        # Build response from cached data
                        response_data = cached_article.copy()
                        
                        # Convert published_at back to datetime if it's a string
                        if "published_at" in response_data and isinstance(response_data["published_at"], str):
                            try:
                                response_data["published_at"] = datetime.fromisoformat(response_data["published_at"])
                            except (ValueError, TypeError):
                                response_data["published_at"] = None
                        
                        # Include raw JSON if requested
                        if not include_raw and "raw_json" in response_data:
                            del response_data["raw_json"]
                        
                        return response_data
                except Exception as cache_error:
                    logger.warning(f"Cache error in LLM detail, falling back to DB: {cache_error}")
            
            # Fetch from database
            import uuid
            try:
                article_uuid = uuid.UUID(article_id)
            except (ValueError, TypeError):
                return None
            
            article = self.db.query(NewsArticle).filter(NewsArticle.id == article_uuid).first()
            
            if not article:
                return None
            
            # Check if provider is shadow
            if self._is_shadow_provider(article.provider):
                return None
            
            # Get linked symbols
            symbol_links = self.db.query(ArticleLink.symbol).filter(
                ArticleLink.article_id == article.id
            ).order_by(ArticleLink.symbol).all()
            
            symbols = [link.symbol for link in symbol_links]
            
            # Build response data
            response_data = {
                "id": str(article.id),
                "title": article.title,
                "source_name": article.source_name,
                "url": article.url,
                "published_at": article.published_at,
                "provider": article.provider,
                "lang": article.lang,
                "lead": article.lead,
                "simhash": article.simhash,
                "symbols": symbols
            }
            
            # Include raw JSON if requested
            if include_raw:
                response_data["raw_json"] = article.raw_json
            
            # Cache the result if enabled
            if self.cache_enabled:
                try:
                    # Always cache with raw_json for consistency
                    cache_data = response_data.copy()
                    cache_data["raw_json"] = article.raw_json
                    cache_data["published_at"] = article.published_at.isoformat() if article.published_at else None
                    set_article_cache(article_id, cache_data)
                except Exception as cache_error:
                    logger.warning(f"Failed to cache LLM article: {cache_error}")
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error in LLM news detail: {e}", exc_info=True)
            return None
    
    def _fetch_articles_by_ids(self, article_ids: List[str]) -> List[NewsArticle]:
        """Fetch articles by their IDs."""
        if not article_ids:
            return []
        
        import uuid
        try:
            uuids = [uuid.UUID(article_id) for article_id in article_ids]
        except (ValueError, TypeError):
            return []
        
        articles = []
        for article_uuid in uuids:
            article = self.db.query(NewsArticle).filter(NewsArticle.id == article_uuid).first()
            if article:
                articles.append(article)
        
        return articles
    
    def _get_total_count(
        self,
        provider: Optional[str],
        symbol: Optional[str],
        since: Optional[datetime],
        until: Optional[datetime],
        min_relevance: float
    ) -> int:
        """Get total count for the query with shadow filtering."""
        query = self.db.query(NewsArticle)
        
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
        
        # Apply shadow mode filtering
        query = self._apply_shadow_filter(query)
        
        return query.count()
    
    def _convert_articles_to_items(self, articles: List[NewsArticle]) -> List[Dict[str, Any]]:
        """Convert NewsArticle objects to response format."""
        items = []
        for article in articles:
            # Get linked symbols for this article
            symbol_links = self.db.query(ArticleLink.symbol).filter(
                ArticleLink.article_id == article.id
            ).all()
            
            symbols = [link.symbol for link in symbol_links]
            
            items.append({
                "id": str(article.id),
                "title": article.title,
                "source_name": article.source_name,
                "url": article.url,
                "published_at": article.published_at,
                "provider": article.provider,
                "lang": article.lang,
                "symbols": symbols
            })
        
        return items


def get_llm_news_repository(db: Session) -> NewsRepositoryLLM:
    """Get LLM news repository instance."""
    return NewsRepositoryLLM(db)
