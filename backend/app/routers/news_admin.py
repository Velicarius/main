"""
News admin router for managing news configuration and monitoring.

Provides JWT-protected endpoints for:
- Viewing news system status and metrics
- Toggling provider shadow/live mode
- Monitoring cache and quota statistics
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.services.news_config import get_flags, set_shadow_live, get_config_version
from app.core.news_cache import get_cache_stats, get_quota_state, get_redis_client
from app.scheduling.news_planner import get_planning_stats
from app.core.config import settings
from app.schemas.news_admin import ToggleShadowRequest, NewsStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/news", tags=["news-admin"])




@router.get("/status", response_model=NewsStatusResponse)
async def get_news_status(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """
    Get comprehensive news system status and metrics.
    
    Returns:
        Dict with planner counts, fetch tallies, cache estimates, and flags
    """
    try:
        # Get planner counts from Redis keys
        planner_stats = get_planning_stats(date.today())
        
        # Get fetch tallies by provider (using existing quota counters)
        fetch_stats = {}
        providers = ["newsapi", "finnhub", "alphavantage"]
        for provider in providers:
            try:
                quota_state = get_quota_state(provider)
                fetch_stats[provider] = {
                    "daily_count": quota_state.get("daily_count", 0),
                    "minute_count": quota_state.get("minute_count", 0)
                }
            except Exception as e:
                logger.warning(f"Failed to get quota state for {provider}: {e}")
                fetch_stats[provider] = {"daily_count": 0, "minute_count": 0}
        
        # Get cache estimates via SCAN counts
        cache_stats = get_cache_stats()
        
        # Get flags from config service
        flags = get_flags(db)
        
        return NewsStatusResponse(
            planner=planner_stats,
            fetch=fetch_stats,
            cache=cache_stats,
            flags=flags
        )
        
    except Exception as e:
        logger.error(f"Error getting news status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get news status: {str(e)}")


@router.post("/toggle_shadow")
async def toggle_shadow_mode(
    request: ToggleShadowRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """
    Toggle provider shadow/live mode.
    
    Args:
        request: Provider name and live status
        
    Returns:
        Updated flags dict
    """
    try:
        # Validate provider name
        provider = request.provider.lower()
        valid_providers = ["newsapi", "finnhub", "alphavantage"]
        
        if provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider: {provider}. Valid providers: {valid_providers}"
            )
        
        # Update shadow mode
        updated_flags = set_shadow_live(db, provider, request.live)
        
        logger.info(f"Admin toggled {provider} to live={request.live}")
        
        return {
            "status": "success",
            "provider": provider,
            "live": request.live,
            "flags": updated_flags
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling shadow mode for {request.provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to toggle shadow mode: {str(e)}")


@router.get("/providers")
async def get_providers_status(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """
    Get detailed provider status including shadow mode and quotas.
    
    Returns:
        Dict with provider details and current status
    """
    try:
        providers = ["newsapi", "finnhub", "alphavantage"]
        provider_status = {}
        
        for provider in providers:
            try:
                # Get quota state
                quota_state = get_quota_state(provider)
                
                # Check if provider is live
                from app.services.news_config import is_provider_live
                is_live = is_provider_live(db, provider)
                
                provider_status[provider] = {
                    "live": is_live,
                    "shadow_mode": not is_live,
                    "daily_count": quota_state.get("daily_count", 0),
                    "minute_count": quota_state.get("minute_count", 0),
                    "last_updated": quota_state.get("timestamp")
                }
                
            except Exception as e:
                logger.warning(f"Failed to get status for {provider}: {e}")
                provider_status[provider] = {
                    "live": True,  # Default to live
                    "shadow_mode": False,
                    "daily_count": 0,
                    "minute_count": 0,
                    "error": str(e)
                }
        
        return {
            "providers": provider_status,
            "config_version": get_config_version(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting providers status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get providers status: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for news admin."""
    return {
        "status": "ok",
        "service": "news-admin",
        "timestamp": datetime.utcnow().isoformat()
    }
