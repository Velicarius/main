"""
NewsAPI.org news provider
https://newsapi.org/docs/endpoints/everything
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from .base import BaseNewsProvider

logger = logging.getLogger(__name__)


class NewsAPIProvider(BaseNewsProvider):
    """NewsAPI.org news provider"""

    BASE_URL = "https://newsapi.org/v2"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def fetch_news(
        self,
        tickers: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from NewsAPI (legacy method for backward compatibility).
        Use fetch_news_conditional() for conditional request support.

        API endpoint: /everything?q={query}&from={from}&to={to}&pageSize={limit}
        """
        if not self.is_enabled():
            logger.warning("NewsAPI provider disabled (no API key)")
            return []

        # Build query: combine tickers or use general business query
        if tickers and len(tickers) > 0:
            query = " OR ".join(tickers[:5])  # Limit to 5 tickers
        else:
            query = "stock market OR finance"

        # Format dates as YYYY-MM-DD
        from_str = from_date.strftime("%Y-%m-%d") if from_date else None
        to_str = to_date.strftime("%Y-%m-%d") if to_date else None

        params = {
            "q": query,
            "apiKey": self.api_key,
            "pageSize": min(limit, 100),  # NewsAPI max is 100
            "language": "en",
            "sortBy": "publishedAt"
        }

        if from_str:
            params["from"] = from_str
        if to_str:
            params["to"] = to_str

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.BASE_URL}/everything", params=params)
                response.raise_for_status()
                data = response.json()

                # Check status
                if data.get("status") != "ok":
                    error_code = data.get("code", "unknown")
                    error_message = data.get("message", "Unknown error")
                    logger.error(f"NewsAPI error [{error_code}]: {error_message}")
                    return []

                # Extract articles
                articles = data.get("articles", [])
                return articles[:limit]

        except httpx.HTTPStatusError as e:
            logger.error(f"NewsAPI HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"NewsAPI fetch error: {e}")
            return []

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
        if not self.is_enabled():
            logger.warning("NewsAPI provider disabled (no API key)")
            return {"status": "error", "items": [], "etag": None, "error": "Provider disabled"}
        
        # Format dates as YYYY-MM-DD
        from_str = published_after.strftime("%Y-%m-%d") if published_after else None
        
        params = {
            "q": query,
            "apiKey": self.api_key,
            "pageSize": min(limit, 100),  # NewsAPI max is 100
            "language": "en",
            "sortBy": "publishedAt"
        }
        
        if from_str:
            params["from"] = from_str
        
        # Build headers for conditional request
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if published_after:
            # Format as RFC1123 for If-Modified-Since
            headers["If-Modified-Since"] = published_after.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.BASE_URL}/everything", params=params, headers=headers)
                
                # Handle 304 Not Modified
                if response.status_code == 304:
                    return {
                        "status": "not_modified",
                        "items": [],
                        "etag": etag
                    }
                
                response.raise_for_status()
                data = response.json()
                
                # Check status
                if data.get("status") != "ok":
                    error_code = data.get("code", "unknown")
                    error_message = data.get("message", "Unknown error")
                    logger.error(f"NewsAPI error [{error_code}]: {error_message}")
                    return {"status": "error", "items": [], "etag": None, "error": error_message}
                
                # Extract articles and ETag
                articles = data.get("articles", [])
                response_etag = response.headers.get("ETag")
                
                return {
                    "status": "ok",
                    "items": articles[:limit],
                    "etag": response_etag
                }
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limit - let retry decorator handle it
                raise
            logger.error(f"NewsAPI HTTP error: {e.response.status_code}")
            return {"status": "error", "items": [], "etag": None, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"NewsAPI fetch error: {e}")
            return {"status": "error", "items": [], "etag": None, "error": str(e)}

    def normalize(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize NewsAPI article to NormalizedNews schema

        NewsAPI format:
        {
          "source": {"id": "bloomberg", "name": "Bloomberg"},
          "author": "John Doe",
          "title": "...",
          "description": "...",
          "url": "...",
          "urlToImage": "...",
          "publishedAt": "2025-01-08T12:30:00Z",
          "content": "..."
        }
        """
        try:
            # Extract domain from URL
            url = raw_article.get("url", "")
            domain = url.split("/")[2] if len(url.split("/")) > 2 else "newsapi.org"

            # Canonical key: title + domain
            title = raw_article.get("title", "")
            canonical_key = f"{title}|{domain}"

            # Parse timestamp (ISO 8601 format)
            time_str = raw_article.get("publishedAt", "")
            try:
                published_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except ValueError:
                published_at = datetime.now()

            # Extract source name
            source_obj = raw_article.get("source", {})
            source_name = source_obj.get("name", "NewsAPI")

            # NewsAPI doesn't provide ticker symbols, so we leave it empty
            tickers = []

            return {
                "provider": "newsapi",
                "title": title,
                "summary": raw_article.get("description"),
                "url": url,
                "source": source_name,
                "tickers": tickers,
                "event_type": "general",
                "published_at": published_at,
                "language": "en",
                "canonical_key": canonical_key
            }
        except Exception as e:
            logger.error(f"NewsAPI normalize error: {e}")
            return {}
