"""
News aggregation REST API endpoint
"""
import logging
import time
import json
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException, Depends, Body
import redis.asyncio as redis

from app.schemas.news import NewsAggregateResponse
from app.schemas.news_summary import NewsSummaryRequest, NewsSummaryResponse, NewsSummary
from app.marketdata.news_aggregator import create_aggregator
from app.services.news_llm_summary import create_news_summarizer, NewsLLMSummarizer
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news"])

# Redis client for caching
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """Get Redis client for caching"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=0,
                decode_responses=True
            )
            await _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            return None
    return _redis_client


def check_news_enabled():
    """Dependency to check if news feature is enabled"""
    if not settings.news_enable:
        raise HTTPException(
            status_code=503,
            detail="News aggregation feature is disabled. Set NEWS_ENABLE=true to enable."
        )


@router.get("/aggregate", response_model=NewsAggregateResponse)
async def aggregate_news(
    tickers: Optional[str] = Query(
        None,
        description="Comma-separated list of stock tickers (e.g., 'AAPL,TSLA,GOOGL')"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of articles to return (1-200)"
    ),
    from_date: Optional[str] = Query(
        None,
        description="Start date in YYYY-MM-DD format (default: 30 days ago)"
    ),
    to_date: Optional[str] = Query(
        None,
        description="End date in YYYY-MM-DD format (default: today)"
    ),
    providers: Optional[str] = Query(
        None,
        description="Comma-separated provider names (finnhub,alphavantage,newsapi). Default: all enabled"
    ),
    _: None = Depends(check_news_enabled)
):
    """
    Aggregate news from multiple providers

    Returns deduplicated and normalized news articles from enabled providers.

    **Example:**
    ```
    GET /news/aggregate?tickers=AAPL,TSLA&limit=20
    ```

    **Response includes:**
    - `articles`: List of normalized news articles
    - `meta`: Metadata about providers, latency, cache status
    """
    try:
        # Parse tickers
        ticker_list = None
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

        # Parse dates
        from_dt = None
        to_dt = None

        if from_date:
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid from_date format: {from_date}. Expected YYYY-MM-DD"
                )

        if to_date:
            try:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid to_date format: {to_date}. Expected YYYY-MM-DD"
                )

        # Default date range: last 30 days
        if not from_dt:
            from_dt = datetime.now() - timedelta(days=30)
        if not to_dt:
            to_dt = datetime.now()

        # Validate date range
        if from_dt > to_dt:
            raise HTTPException(
                status_code=400,
                detail="from_date must be before to_date"
            )

        # Parse provider list
        provider_list = None
        if providers:
            provider_list = [p.strip().lower() for p in providers.split(",") if p.strip()]
            valid_providers = {"finnhub", "alphavantage", "newsapi"}
            invalid = set(provider_list) - valid_providers
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid providers: {invalid}. Valid: {valid_providers}"
                )

        # Create aggregator and fetch news
        aggregator = create_aggregator()

        result = await aggregator.fetch_all(
            tickers=ticker_list,
            from_date=from_dt,
            to_date=to_dt,
            limit=limit,
            providers=provider_list
        )

        logger.info(
            f"News aggregation: {result['meta']['returned']} articles, "
            f"{result['meta']['latency_ms']}ms latency"
        )

        return NewsAggregateResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"News aggregation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to aggregate news: {str(e)}"
        )


@router.get("/providers")
async def get_providers(_: None = Depends(check_news_enabled)):
    """
    Get list of available news providers and their status

    Returns information about which providers are enabled (have API keys configured).
    """
    aggregator = create_aggregator()

    provider_status = {}
    for name, provider in aggregator.providers.items():
        provider_status[name] = {
            "enabled": provider.is_enabled(),
            "name": provider.provider_name
        }

    return {
        "providers": provider_status,
        "feature_enabled": settings.news_enable
    }


@router.post("/summary", response_model=NewsSummaryResponse)
async def generate_news_summary(
    request: NewsSummaryRequest = Body(...),
    _: None = Depends(check_news_enabled)
):
    """
    Generate LLM-powered structured brief for a ticker

    Clusters recent news articles and generates:
    - Prospects, opportunities, risks
    - Base/Bull/Bear scenarios
    - Non-advisory posture assessment
    - Confidence score

    **Example:**
    ```json
    {
      "ticker": "TSLA",
      "window_hours": 24,
      "limit": 10
    }
    ```

    **Performance:**
    - Cache hit: <100ms
    - Cold (LLM call): 2-5s
    """
    start_time = time.time()

    try:
        # Fetch news for ticker
        aggregator = create_aggregator()

        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(hours=request.window_hours)

        news_result = await aggregator.fetch_all(
            tickers=[request.ticker],
            from_date=from_date,
            to_date=to_date,
            limit=request.limit
        )

        articles = [article.dict() for article in news_result["articles"]]

        if not articles:
            raise HTTPException(
                status_code=404,
                detail=f"No news articles found for {request.ticker} in last {request.window_hours}h"
            )

        # Check cache
        # Use request settings or defaults from environment
        model = request.model or settings.default_news_model or "llama3.1:8b"
        provider = request.provider or settings.default_news_provider or "ollama"
        
        summarizer = create_news_summarizer(model=model, provider=provider)
        article_ids = [a["id"] for a in articles]
        model_version = f"{request.provider or 'default'}:{request.model or 'default'}"
        cache_key = NewsLLMSummarizer.generate_cache_key(
            ticker=request.ticker,
            window_hours=request.window_hours,
            article_ids=article_ids,
            model_version=model_version
        )

        redis_client = await get_redis()
        cached_summary = None

        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    cached_summary = NewsSummary(**json.loads(cached_data))
                    logger.info(f"Cache hit for {request.ticker} summary")
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        if cached_summary:
            latency_ms = int((time.time() - start_time) * 1000)
            return NewsSummaryResponse(
                summary=cached_summary,
                cached=True,
                latency_ms=latency_ms
            )

        # Generate new summary
        summary = await summarizer.generate_summary(
            ticker=request.ticker,
            articles=articles,
            window_hours=request.window_hours,
            portfolio_hint=request.portfolio_hint
        )

        # Cache the result
        if redis_client:
            try:
                cache_ttl = getattr(settings, "news_cache_ttl", 300)  # 5 minutes default
                await redis_client.setex(
                    cache_key,
                    cache_ttl,
                    summary.json()
                )
                logger.info(f"Cached summary for {request.ticker} (TTL: {cache_ttl}s)")
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")

        latency_ms = int((time.time() - start_time) * 1000)

        return NewsSummaryResponse(
            summary=summary,
            cached=False,
            latency_ms=latency_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"News summary generation error: {e}", exc_info=True)
        
        # Provide more user-friendly error messages
        error_message = str(e)
        if "OPENAI_API_KEY" in error_message:
            error_message = "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable or use Ollama models in Settings."
        elif "Connection" in error_message and "ollama" in error_message.lower():
            error_message = "Ollama not available. Please ensure Ollama is running on localhost:11434 or use OpenAI models in Settings."
        elif "Connection" in error_message:
            error_message = "AI service unavailable. Please check your internet connection or try a different model in Settings."
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate news summary: {error_message}"
        )
