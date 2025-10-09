"""
Alpha Vantage news provider
https://www.alphavantage.co/documentation/#news-sentiment
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from .base import BaseNewsProvider

logger = logging.getLogger(__name__)


class AlphaVantageProvider(BaseNewsProvider):
    """Alpha Vantage news & sentiment provider"""

    BASE_URL = "https://www.alphavantage.co/query"

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
        Fetch news and sentiment from Alpha Vantage

        API endpoint: /query?function=NEWS_SENTIMENT&tickers={tickers}&limit={limit}
        """
        if not self.is_enabled():
            logger.warning("Alpha Vantage provider disabled (no API key)")
            return []

        # Build ticker string (comma-separated)
        ticker_str = ",".join(tickers[:5]) if tickers else ""

        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": self.api_key,
            "limit": min(limit, 1000)  # Alpha Vantage max is 1000
        }

        if ticker_str:
            params["tickers"] = ticker_str

        # Alpha Vantage supports time_from/time_to in YYYYMMDDTHHMM format
        if from_date:
            params["time_from"] = from_date.strftime("%Y%m%dT%H%M")
        if to_date:
            params["time_to"] = to_date.strftime("%Y%m%dT%H%M")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                # Check for API errors
                if "Error Message" in data:
                    logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                    return []

                if "Note" in data:
                    logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                    return []

                # Extract feed array
                feed = data.get("feed", [])
                return feed[:limit]

        except httpx.HTTPStatusError as e:
            logger.error(f"Alpha Vantage HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Alpha Vantage fetch error: {e}")
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
            query: Search query string (treated as ticker for Alpha Vantage)
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
            logger.warning("Alpha Vantage provider disabled (no API key)")
            return {"status": "error", "items": [], "etag": None, "error": "Provider disabled"}
        
        # Build ticker string (use query as ticker)
        ticker_str = query.upper() if query else ""
        
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": self.api_key,
            "limit": min(limit, 1000)  # Alpha Vantage max is 1000
        }
        
        if ticker_str:
            params["tickers"] = ticker_str
        
        # Alpha Vantage supports time_from/time_to in YYYYMMDDTHHMM format
        if published_after:
            params["time_from"] = published_after.strftime("%Y%m%dT%H%M")
        
        # Build headers for conditional request
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if published_after:
            # Format as RFC1123 for If-Modified-Since
            headers["If-Modified-Since"] = published_after.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params, headers=headers)
                
                # Handle 304 Not Modified
                if response.status_code == 304:
                    return {
                        "status": "not_modified",
                        "items": [],
                        "etag": etag
                    }
                
                response.raise_for_status()
                data = response.json()
                response_etag = response.headers.get("ETag")
                
                # Check for API errors
                if "Error Message" in data:
                    logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                    return {"status": "error", "items": [], "etag": None, "error": data['Error Message']}
                
                if "Note" in data:
                    logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                    return {"status": "error", "items": [], "etag": None, "error": "Rate limit exceeded"}
                
                # Extract feed array
                feed = data.get("feed", [])
                
                return {
                    "status": "ok",
                    "items": feed[:limit],
                    "etag": response_etag
                }
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limit - let retry decorator handle it
                raise
            logger.error(f"Alpha Vantage HTTP error: {e.response.status_code}")
            return {"status": "error", "items": [], "etag": None, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Alpha Vantage fetch error: {e}")
            return {"status": "error", "items": [], "etag": None, "error": str(e)}

    def normalize(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Alpha Vantage article to NormalizedNews schema

        Alpha Vantage format:
        {
          "title": "...",
          "url": "...",
          "time_published": "20250108T123000",
          "authors": ["..."],
          "summary": "...",
          "banner_image": "...",
          "source": "Bloomberg",
          "category_within_source": "n/a",
          "source_domain": "bloomberg.com",
          "topics": [...],
          "overall_sentiment_score": 0.123,
          "overall_sentiment_label": "Neutral",
          "ticker_sentiment": [
            {"ticker": "AAPL", "relevance_score": "0.9", "ticker_sentiment_score": "0.5", "ticker_sentiment_label": "Bullish"}
          ]
        }
        """
        try:
            # Extract domain
            domain = raw_article.get("source_domain", "alphavantage.co")

            # Canonical key: title + domain
            title = raw_article.get("title", "")
            canonical_key = f"{title}|{domain}"

            # Parse timestamp (YYYYMMDDTHHMMSS format)
            time_str = raw_article.get("time_published", "")
            try:
                published_at = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
            except ValueError:
                published_at = datetime.now()

            # Extract tickers from ticker_sentiment array
            ticker_sentiment = raw_article.get("ticker_sentiment", [])
            tickers = [item["ticker"] for item in ticker_sentiment if "ticker" in item]

            # Determine event type from topics
            topics = raw_article.get("topics", [])
            event_type = "general"
            if any(topic.get("topic") == "Earnings" for topic in topics):
                event_type = "earnings"
            elif any(topic.get("topic") == "Mergers & Acquisitions" for topic in topics):
                event_type = "M&A"

            return {
                "provider": "alphavantage",
                "title": title,
                "summary": raw_article.get("summary"),
                "url": raw_article.get("url", ""),
                "source": raw_article.get("source", "Alpha Vantage"),
                "tickers": tickers,
                "event_type": event_type,
                "published_at": published_at,
                "language": "en",
                "canonical_key": canonical_key
            }
        except Exception as e:
            logger.error(f"Alpha Vantage normalize error: {e}")
            return {}
