"""
News aggregator service - fetches and merges news from multiple providers
"""
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.marketdata.news_providers import (
    FinnhubProvider,
    AlphaVantageProvider,
    NewsAPIProvider
)
from app.utils.news_dedup import merge_provider_results
from app.schemas.news import NormalizedNews, ProviderMeta
from app.core.config import settings
from app.services.news_cache_service import get_news_cache_service

logger = logging.getLogger(__name__)


class NewsAggregator:
    """Aggregates news from multiple providers with deduplication"""

    def __init__(
        self,
        finnhub_api_key: Optional[str] = None,
        alphavantage_api_key: Optional[str] = None,
        newsapi_api_key: Optional[str] = None,
        timeout: int = 10
    ):
        """
        Initialize news aggregator with API keys

        Args:
            finnhub_api_key: Finnhub API key (or None to disable)
            alphavantage_api_key: Alpha Vantage API key (or None to disable)
            newsapi_api_key: NewsAPI API key (or None to disable)
            timeout: HTTP timeout in seconds
        """
        self.providers = {
            "finnhub": FinnhubProvider(api_key=finnhub_api_key, timeout=timeout),
            "alphavantage": AlphaVantageProvider(api_key=alphavantage_api_key, timeout=timeout),
            "newsapi": NewsAPIProvider(api_key=newsapi_api_key, timeout=timeout)
        }

    async def fetch_all(
        self,
        tickers: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        providers: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch news from all enabled providers in parallel with caching

        Args:
            tickers: Optional list of stock tickers to filter by
            from_date: Optional start date filter
            to_date: Optional end date filter
            limit: Maximum number of deduplicated articles to return
            providers: Optional list of provider names to use (default: all enabled)
            use_cache: Whether to use cache (default: True)

        Returns:
            Dict with 'articles' (List[NormalizedNews]) and 'meta' (metadata)
        """
        start_time = time.time()
        
        # Try cache first if enabled and we have a single ticker
        if use_cache and settings.news_cache_enabled and tickers and len(tickers) == 1:
            ticker = tickers[0]
            cache_service = get_news_cache_service()
            
            # Calculate hours back from from_date if provided
            hours_back = 24  # default
            if from_date:
                hours_back = int((datetime.now() - from_date).total_seconds() / 3600)
            
            cached_articles = cache_service.get_cached_news(ticker, hours_back, limit)
            if cached_articles:
                logger.info(f"Cache hit for {ticker}: {len(cached_articles)} articles")
                return {
                    "articles": cached_articles,
                    "meta": {
                        "total": len(cached_articles),
                        "returned": len(cached_articles),
                        "providers": {"cache": {"status": "hit", "count": len(cached_articles)}},
                        "cache_hit": True,
                        "latency_ms": int((time.time() - start_time) * 1000)
                    }
                }

        # Determine which providers to use
        if providers:
            active_providers = {
                name: provider
                for name, provider in self.providers.items()
                if name in providers and provider.is_enabled()
            }
        else:
            active_providers = {
                name: provider
                for name, provider in self.providers.items()
                if provider.is_enabled()
            }

        if not active_providers:
            logger.warning("No news providers enabled")
            return {
                "articles": [],
                "meta": {
                    "total": 0,
                    "returned": 0,
                    "providers": {},
                    "cache_hit": False,
                    "latency_ms": int((time.time() - start_time) * 1000)
                }
            }

        # Fetch from all providers in parallel
        tasks = {
            name: self._fetch_from_provider(provider, tickers, from_date, to_date, limit)
            for name, provider in active_providers.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Build provider metadata and collect normalized articles
        provider_meta = {}
        provider_articles = {}

        for (name, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                provider_meta[name] = {
                    "status": "error",
                    "count": 0,
                    "error": str(result),
                    "latency_ms": None
                }
                logger.error(f"Provider {name} failed: {result}")
            else:
                provider_meta[name] = result["meta"]
                provider_articles[name] = result["articles"]

        # Merge and deduplicate
        deduplicated = merge_provider_results(provider_articles, limit=limit)

        # Convert to Pydantic models
        normalized_articles = [
            NormalizedNews(**article)
            for article in deduplicated
        ]

        # Cache the results if we have a single ticker
        if use_cache and settings.news_cache_enabled and tickers and len(tickers) == 1 and normalized_articles:
            ticker = tickers[0]
            cache_service = get_news_cache_service()
            
            # Calculate hours back from from_date if provided
            hours_back = 24  # default
            if from_date:
                hours_back = int((datetime.now() - from_date).total_seconds() / 3600)
            
            # Cache the articles (sync, but don't block on errors)
            try:
                cache_service.cache_news(ticker, normalized_articles, hours_back, limit)
            except Exception as e:
                logger.warning(f"Failed to cache news for {ticker}: {e}")

        total_latency_ms = int((time.time() - start_time) * 1000)

        return {
            "articles": normalized_articles,
            "meta": {
                "total": len(deduplicated),
                "returned": len(normalized_articles),
                "providers": provider_meta,
                "cache_hit": False,
                "latency_ms": total_latency_ms
            }
        }

    async def _fetch_from_provider(
        self,
        provider,
        tickers: Optional[List[str]],
        from_date: Optional[datetime],
        to_date: Optional[datetime],
        limit: int
    ) -> Dict[str, Any]:
        """
        Fetch and normalize articles from a single provider

        Returns:
            Dict with 'articles' (normalized) and 'meta' (ProviderMeta)
        """
        provider_start = time.time()

        try:
            # Fetch raw articles
            raw_articles = await provider.fetch_news(
                tickers=tickers,
                from_date=from_date,
                to_date=to_date,
                limit=limit
            )

            # Normalize articles
            normalized = []
            for raw in raw_articles:
                try:
                    norm = provider.normalize(raw)
                    if norm:  # Skip empty results
                        normalized.append(norm)
                except Exception as e:
                    logger.warning(f"Failed to normalize article from {provider.provider_name}: {e}")

            latency_ms = int((time.time() - provider_start) * 1000)

            return {
                "articles": normalized,
                "meta": {
                    "status": "ok",
                    "count": len(normalized),
                    "error": None,
                    "latency_ms": latency_ms
                }
            }

        except Exception as e:
            latency_ms = int((time.time() - provider_start) * 1000)
            logger.error(f"Provider {provider.provider_name} error: {e}")

            return {
                "articles": [],
                "meta": {
                    "status": "error",
                    "count": 0,
                    "error": str(e),
                    "latency_ms": latency_ms
                }
            }


def create_aggregator() -> NewsAggregator:
    """
    Factory function to create NewsAggregator from settings

    Returns:
        NewsAggregator instance with API keys from config
    """
    return NewsAggregator(
        finnhub_api_key=getattr(settings, "finnhub_api_key", None),
        alphavantage_api_key=getattr(settings, "alphavantage_api_key", None),
        newsapi_api_key=getattr(settings, "newsapi_api_key", None),
        timeout=getattr(settings, "news_timeout", 10)
    )
