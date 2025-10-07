"""
News schemas for normalization and API responses
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class NormalizedNews(BaseModel):
    """Normalized news article from any provider"""
    id: str = Field(..., description="SHA-1 hash (canonical_key)")
    provider: str = Field(..., description="Provider name (finnhub, alphavantage, newsapi)")
    title: str = Field(..., description="Article title/headline")
    summary: Optional[str] = Field(None, description="Article summary/description")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="News source name (e.g., Bloomberg, Reuters)")
    tickers: List[str] = Field(default_factory=list, description="Related stock tickers")
    event_type: Optional[str] = Field(None, description="Event type (earnings, M&A, general)")
    published_at: datetime = Field(..., description="Publication timestamp")
    language: str = Field(default="en", description="Article language code")
    canonical_key: str = Field(..., description="Deduplication key")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4e5f6...",
                "provider": "finnhub",
                "title": "Tesla Reports Record Q4 Earnings",
                "summary": "Tesla Inc. reported record quarterly earnings...",
                "url": "https://example.com/news/tesla-earnings",
                "source": "Bloomberg",
                "tickers": ["TSLA"],
                "event_type": "earnings",
                "published_at": "2025-01-15T14:30:00Z",
                "language": "en",
                "canonical_key": "a1b2c3d4e5f6..."
            }
        }


class ProviderMeta(BaseModel):
    """Metadata about a provider's response"""
    status: str = Field(..., description="ok, error, timeout")
    count: int = Field(default=0, description="Number of articles returned")
    error: Optional[str] = Field(None, description="Error message if failed")
    latency_ms: Optional[int] = Field(None, description="Response latency in milliseconds")


class NewsAggregateResponse(BaseModel):
    """Response from news aggregation endpoint"""
    articles: List[NormalizedNews] = Field(..., description="Normalized news articles")
    meta: Dict[str, Any] = Field(..., description="Aggregation metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "articles": [
                    {
                        "id": "a1b2c3d4",
                        "provider": "finnhub",
                        "title": "Market Update",
                        "summary": "Stocks rally...",
                        "url": "https://example.com/news/1",
                        "source": "Reuters",
                        "tickers": ["SPY"],
                        "event_type": "general",
                        "published_at": "2025-01-15T10:00:00Z",
                        "language": "en",
                        "canonical_key": "a1b2c3d4"
                    }
                ],
                "meta": {
                    "total": 45,
                    "returned": 20,
                    "providers": {
                        "finnhub": {"status": "ok", "count": 15, "latency_ms": 234},
                        "alphavantage": {"status": "ok", "count": 12, "latency_ms": 456},
                        "newsapi": {"status": "error", "error": "rate_limit", "count": 0}
                    },
                    "cache_hit": False,
                    "latency_ms": 1234
                }
            }
        }
