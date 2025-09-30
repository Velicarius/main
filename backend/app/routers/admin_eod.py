"""
Admin endpoints for EOD operations.

This module provides protected admin endpoints for manually triggering
EOD data refresh operations.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.celery_app import celery_app
from app.tasks.fetch_eod import run_eod_refresh

router = APIRouter(prefix="/admin/eod", tags=["admin-eod"])


class EODRefreshResponse(BaseModel):
    """Response model for EOD refresh trigger"""
    status: str
    task_id: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "queued",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "EOD refresh task queued successfully"
            }
        }


def verify_admin_token(x_admin_token: str = Header(None)) -> str:
    """
    Verify admin token from X-Admin-Token header.
    
    Args:
        x_admin_token: Admin token from request header
        
    Returns:
        The admin token if valid
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not settings.admin_token:
        raise HTTPException(
            status_code=500,
            detail="Admin token not configured. Set ADMIN_TOKEN environment variable."
        )
    
    if not x_admin_token:
        raise HTTPException(
            status_code=403,
            detail="Missing X-Admin-Token header"
        )
    
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin token"
        )
    
    return x_admin_token


@router.post("/refresh", response_model=EODRefreshResponse)
async def trigger_eod_refresh(
    admin_token: str = Depends(verify_admin_token)
) -> EODRefreshResponse:
    """
    Manually trigger EOD data refresh.
    
    This endpoint queues the main EOD refresh task that will:
    1. Check feature flags (EOD_ENABLE, EOD_SOURCE)
    2. Discover symbols from positions
    3. Fetch latest data from Stooq
    4. Upsert data to database
    
    Requires X-Admin-Token header with valid admin token.
    
    Returns:
        EODRefreshResponse with task ID and status
    """
    try:
        # Check if EOD is enabled
        if not settings.eod_enable:
            return EODRefreshResponse(
                status="disabled",
                task_id="",
                message="EOD feature is disabled via EOD_ENABLE=false"
            )
        
        # Queue the EOD refresh task
        task = run_eod_refresh.delay()
        
        return EODRefreshResponse(
            status="queued",
            task_id=task.id,
            message=f"EOD refresh task queued successfully. Task ID: {task.id}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue EOD refresh task: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_eod_task_status(
    task_id: str,
    admin_token: str = Depends(verify_admin_token)
) -> Dict[str, Any]:
    """
    Get the status of an EOD refresh task.
    
    Args:
        task_id: Celery task ID
        admin_token: Admin token from header
        
    Returns:
        Task status and result information
    """
    try:
        task = celery_app.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": task.status,
            "result": task.result if task.ready() else None,
        }
        
        if task.failed():
            response["error"] = str(task.info)
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/config", response_model=Dict[str, Any])
async def get_eod_config(
    admin_token: str = Depends(verify_admin_token)
) -> Dict[str, Any]:
    """
    Get current EOD configuration (feature flags).
    
    Args:
        admin_token: Admin token from header
        
    Returns:
        Current EOD configuration
    """
    return {
        "eod_enable": settings.eod_enable,
        "eod_source": settings.eod_source,
        "eod_schedule_cron": settings.eod_schedule_cron,
        "stq_timeout": settings.stq_timeout,
        "admin_token_configured": bool(settings.admin_token)
    }




