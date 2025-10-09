"""
Base class for news providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseNewsProvider(ABC):
    """Abstract base class for news providers"""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        """
        Initialize news provider

        Args:
            api_key: API key for the provider
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.provider_name = self.__class__.__name__.replace("Provider", "").lower()

    @abstractmethod
    async def fetch_news(
        self,
        tickers: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from provider

        Args:
            tickers: Optional list of stock tickers to filter by
            from_date: Optional start date filter
            to_date: Optional end date filter
            limit: Maximum number of results

        Returns:
            List of raw news articles from provider
        """
        pass

    async def fetch_news_conditional(
        self,
        query: str,
        published_after: Optional[datetime] = None,
        etag: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Fetch news with conditional request support (ETag/If-Modified-Since).
        
        Args:
            query: Search query string
            published_after: Only fetch articles published after this date
            etag: ETag for conditional request
            limit: Maximum number of results
            
        Returns:
            Dict with 'status', 'items', 'etag' keys
            - status: 'ok', 'not_modified', or 'error'
            - items: List of articles (empty if not_modified)
            - etag: ETag from response (for caching)
        """
        # Default implementation falls back to regular fetch_news
        # Subclasses can override for conditional request support
        try:
            items = await self.fetch_news(
                tickers=[query] if query else None,
                from_date=published_after,
                limit=limit
            )
            return {
                "status": "ok",
                "items": items,
                "etag": None  # No ETag support by default
            }
        except Exception as e:
            logger.error(f"Error in fetch_news_conditional: {e}")
            return {
                "status": "error",
                "items": [],
                "etag": None,
                "error": str(e)
            }

    @abstractmethod
    def normalize(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw article to standard format

        Args:
            raw_article: Raw article data from provider

        Returns:
            Normalized article dict matching NormalizedNews schema
        """
        pass

    def is_enabled(self) -> bool:
        """Check if provider is enabled (has API key)"""
        return self.api_key is not None and len(self.api_key) > 0
