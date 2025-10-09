"""
Internal news ingestion API endpoints.

This module provides internal endpoints for ingesting news articles
from external providers into the database.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body, Header
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.news_ingest import ingest_articles, normalize_item
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/news", tags=["internal-news"])


class IngestItem(BaseModel):
    """Single news item for ingestion."""
    url: str = Field(..., description="Article URL")
    title: Optional[str] = Field(None, description="Article title")
    lead: Optional[str] = Field(None, description="Article summary/lead")
    published_at: Optional[str] = Field(None, description="Publication date (ISO format)")
    source_name: Optional[str] = Field(None, description="Source name")
    lang: Optional[str] = Field(None, description="Language code")
    symbols: Optional[List[str]] = Field(None, description="Related symbols")
    provider: Optional[str] = Field(None, description="Provider name (auto-filled)")
    
    # Allow additional fields for raw provider data
    class Config:
        extra = "allow"
    
    @validator('url')
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError('URL cannot be empty')
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v.strip()
    
    @validator('symbols')
    def validate_symbols(cls, v):
        if v is None:
            return v
        return [s.strip().upper() for s in v if s and s.strip()]


class IngestRequest(BaseModel):
    """Request payload for news ingestion."""
    provider: str = Field(..., description="Provider name (e.g., 'newsapi', 'alphavantage', 'finnhub')")
    items: List[IngestItem] = Field(..., description="List of news items to ingest")
    default_symbols: Optional[List[str]] = Field(None, description="Fallback symbols if items have none")
    
    @validator('items')
    def validate_items_count(cls, v):
        if len(v) > 200:
            raise ValueError('Maximum 200 items per request')
        if not v:
            raise ValueError('Items list cannot be empty')
        return v
    
    @validator('default_symbols')
    def validate_default_symbols(cls, v):
        if v is None:
            return v
        return [s.strip().upper() for s in v if s and s.strip()]


class IngestResponse(BaseModel):
    """Response from news ingestion."""
    inserted: int = Field(..., description="Number of new articles inserted")
    linked: int = Field(..., description="Number of symbol links created")
    duplicates: int = Field(..., description="Number of duplicate articles found")
    total_processed: int = Field(..., description="Total number of items processed")


def verify_internal_token(x_internal_token: Optional[str] = Header(None)):
    """Verify internal API token for security."""
    if not settings.admin_token:
        # If no admin token is configured, allow access (dev mode)
        return True
    
    if not x_internal_token or x_internal_token != settings.admin_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal API token"
        )
    return True


@router.post("/ingest", response_model=IngestResponse)
async def ingest_news(
    request: IngestRequest = Body(...),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_internal_token)
):
    """
    Ingest news articles from external providers.
    
    This endpoint accepts normalized news articles from external providers,
    deduplicates them by URL, and stores them in the database with symbol links.
    
    **Features:**
    - URL canonicalization (removes UTM parameters, normalizes format)
    - Deduplication by URL and URL hash
    - Symbol linking with relevance scores
    - Graceful handling of duplicates
    
    **Example:**
    ```json
    {
      "provider": "newsapi",
      "items": [
        {
          "url": "https://example.com/news/1",
          "title": "Apple Reports Strong Q4 Results",
          "lead": "Apple exceeded expectations...",
          "published_at": "2024-01-15T10:30:00Z",
          "source_name": "Reuters",
          "symbols": ["AAPL"]
        }
      ],
      "default_symbols": ["NVDA"]
    }
    ```
    
    **Response:**
    ```json
    {
      "inserted": 1,
      "linked": 1,
      "duplicates": 0,
      "total_processed": 1
    }
    ```
    """
    try:
        # Convert Pydantic models to dictionaries for processing
        items_dict = []
        for item in request.items:
            item_dict = item.dict()
            # Add provider to each item if not present
            if 'provider' not in item_dict:
                item_dict['provider'] = request.provider
            items_dict.append(item_dict)
        
        # Ingest articles
        result = ingest_articles(
            db=db,
            provider=request.provider,
            items=items_dict,
            default_symbols=request.default_symbols
        )
        
        # Commit the transaction
        db.commit()
        
        logger.info(
            f"News ingestion completed: {result['inserted']} inserted, "
            f"{result['linked']} linked, {result['duplicates']} duplicates"
        )
        
        return IngestResponse(
            inserted=result['inserted'],
            linked=result['linked'],
            duplicates=result['duplicates'],
            total_processed=len(request.items)
        )
        
    except ValueError as e:
        # Validation errors
        logger.warning(f"News ingestion validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
        
    except Exception as e:
        # Database or other errors
        logger.error(f"News ingestion error: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest news: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for news ingestion service.
    
    Returns basic status information about the ingestion service.
    """
    return {
        "status": "healthy",
        "service": "news-ingest",
        "version": "1.0.0"
    }
