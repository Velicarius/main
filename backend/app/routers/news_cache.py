"""
News Cache Management API - управление кэшем новостей
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import logging

from app.services.news_cache_service import get_news_cache_service
from app.core.config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news/cache", tags=["news-cache"])


class CacheStatsResponse(BaseModel):
    """Статистика кэша новостей"""
    success: bool
    stats: Dict[str, Any]
    error: str = None


class CacheInvalidationRequest(BaseModel):
    """Запрос на инвалидацию кэша"""
    ticker: str


class CacheInvalidationResponse(BaseModel):
    """Ответ на инвалидацию кэша"""
    success: bool
    message: str
    error: str = None


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Получить статистику кэша новостей"""
    try:
        cache_service = get_news_cache_service()
        stats = cache_service.get_cache_stats()
        
        return CacheStatsResponse(
            success=True,
            stats=stats
        )
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return CacheStatsResponse(
            success=False,
            stats={},
            error=str(e)
        )


@router.post("/invalidate", response_model=CacheInvalidationResponse)
async def invalidate_ticker_cache(request: CacheInvalidationRequest):
    """Инвалидировать кэш для конкретного тикера"""
    try:
        cache_service = get_news_cache_service()
        success = cache_service.invalidate_ticker_cache(request.ticker)
        
        if success:
            return CacheInvalidationResponse(
                success=True,
                message=f"Cache invalidated for {request.ticker}"
            )
        else:
            return CacheInvalidationResponse(
                success=False,
                message=f"Failed to invalidate cache for {request.ticker}",
                error="Cache invalidation failed"
            )
    except Exception as e:
        logger.error(f"Error invalidating cache for {request.ticker}: {e}")
        return CacheInvalidationResponse(
            success=False,
            message=f"Error invalidating cache for {request.ticker}",
            error=str(e)
        )


@router.post("/invalidate/all", response_model=CacheInvalidationResponse)
async def invalidate_all_cache():
    """Инвалидировать весь кэш новостей"""
    try:
        cache_service = get_news_cache_service()
        
        # Получаем все ключи новостей
        news_keys = cache_service.redis_client.keys("news:*")
        
        if news_keys:
            # Удаляем все ключи
            cache_service.redis_client.delete(*news_keys)
            return CacheInvalidationResponse(
                success=True,
                message=f"Invalidated {len(news_keys)} cache entries"
            )
        else:
            return CacheInvalidationResponse(
                success=True,
                message="No cache entries found to invalidate"
            )
    except Exception as e:
        logger.error(f"Error invalidating all cache: {e}")
        return CacheInvalidationResponse(
            success=False,
            message="Error invalidating all cache",
            error=str(e)
        )


@router.get("/config")
async def get_cache_config():
    """Получить конфигурацию кэша новостей"""
    return {
        "success": True,
        "config": {
            "enabled": settings.news_cache_enabled,
            "ttl_seconds": settings.news_cache_ttl_seconds,
            "max_articles": settings.news_cache_max_articles
        }
    }
