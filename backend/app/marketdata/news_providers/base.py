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
