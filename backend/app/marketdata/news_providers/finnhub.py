"""
Finnhub news provider
https://finnhub.io/docs/api/company-news
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from .base import BaseNewsProvider

logger = logging.getLogger(__name__)


class FinnhubProvider(BaseNewsProvider):
    """Finnhub stock news provider"""

    BASE_URL = "https://finnhub.io/api/v1"

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
        Fetch company news from Finnhub

        API endpoint: /company-news?symbol={ticker}&from={from_date}&to={to_date}
        """
        if not self.is_enabled():
            logger.warning("Finnhub provider disabled (no API key)")
            return []

        # Finnhub requires at least one ticker
        if not tickers or len(tickers) == 0:
            logger.warning("Finnhub requires at least one ticker")
            return []

        # Format dates as YYYY-MM-DD
        from_str = from_date.strftime("%Y-%m-%d") if from_date else (datetime.now().replace(day=1).strftime("%Y-%m-%d"))
        to_str = to_date.strftime("%Y-%m-%d") if to_date else datetime.now().strftime("%Y-%m-%d")

        all_articles = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for ticker in tickers[:5]:  # Limit to 5 tickers to avoid rate limits
                try:
                    response = await client.get(
                        f"{self.BASE_URL}/company-news",
                        params={
                            "symbol": ticker,
                            "from": from_str,
                            "to": to_str,
                            "token": self.api_key
                        }
                    )
                    response.raise_for_status()
                    articles = response.json()

                    # Finnhub returns array of articles
                    if isinstance(articles, list):
                        all_articles.extend(articles[:limit])

                except httpx.HTTPStatusError as e:
                    logger.error(f"Finnhub API error for {ticker}: {e.response.status_code}")
                except Exception as e:
                    logger.error(f"Finnhub fetch error for {ticker}: {e}")

        # Return up to limit
        return all_articles[:limit]

    def normalize(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Finnhub article to NormalizedNews schema

        Finnhub format:
        {
          "category": "company news",
          "datetime": 1234567890,
          "headline": "...",
          "id": 12345,
          "image": "...",
          "related": "AAPL",
          "source": "Bloomberg",
          "summary": "...",
          "url": "..."
        }
        """
        try:
            # Extract domain from URL for canonical key
            url = raw_article.get("url", "")
            domain = url.split("/")[2] if len(url.split("/")) > 2 else "finnhub.io"

            # Canonical key: title + domain (will be SHA-1 hashed by dedup utility)
            title = raw_article.get("headline", "")
            canonical_key = f"{title}|{domain}"

            # Parse timestamp
            timestamp = raw_article.get("datetime", 0)
            published_at = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()

            # Extract ticker (Finnhub uses "related" field)
            ticker = raw_article.get("related", "")
            tickers = [ticker] if ticker else []

            return {
                "provider": "finnhub",
                "title": title,
                "summary": raw_article.get("summary"),
                "url": url,
                "source": raw_article.get("source", "Finnhub"),
                "tickers": tickers,
                "event_type": raw_article.get("category", "general"),
                "published_at": published_at,
                "language": "en",
                "canonical_key": canonical_key
            }
        except Exception as e:
            logger.error(f"Finnhub normalize error: {e}")
            return {}
