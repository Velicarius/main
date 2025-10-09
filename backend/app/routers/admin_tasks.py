from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.celery_app import celery_app
from app.tasks.fetch_eod import fetch_eod_for_symbols
from app.dependencies import require_admin

router = APIRouter(prefix="/admin/tasks", tags=["admin-tasks"])


class FetchEODRequest(BaseModel):
    """Request model for manual EOD fetch trigger"""
    symbols: Optional[List[str]] = None
    since: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["AAPL.US", "MSFT.US"],
                "since": "2025-01-01"
            }
        }


class TaskResponse(BaseModel):
    """Response model for task submission"""
    status: str
    task_id: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "queued",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "EOD fetch task queued successfully"
            }
        }


@router.post("/fetch-eod", response_model=TaskResponse, dependencies=[Depends(require_admin)])
async def trigger_fetch_eod(request: FetchEODRequest):
    """
    Manually trigger EOD data fetching task.
    
    Args:
        request: FetchEODRequest with optional symbols and since date
        
    Returns:
        TaskResponse with task ID and status
    """
    try:
        # Validate since date format if provided
        if request.since:
            try:
                from datetime import date
                date.fromisoformat(request.since)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid since date format. Use YYYY-MM-DD format."
                )
        
        # Queue the Celery task
        task = fetch_eod_for_symbols.delay(request.symbols, request.since)
        
        return TaskResponse(
            status="queued",
            task_id=task.id,
            message=f"EOD fetch task queued successfully. Task ID: {task.id}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue EOD fetch task: {str(e)}"
        )


@router.get("/fetch-eod/{task_id}", response_model=dict, dependencies=[Depends(require_admin)])
async def get_task_status(task_id: str):
    """
    Get the status of a Celery task.
    
    Args:
        task_id: Celery task ID
        
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









