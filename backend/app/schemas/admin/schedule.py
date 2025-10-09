"""Pydantic schemas for Schedules"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class ScheduleBase(BaseModel):
    task_name: str
    task_type: str = "celery"
    cron_expression: Optional[str] = None
    timezone: str = "UTC"
    is_enabled: bool = True
    payload: Optional[Dict[str, Any]] = {}
    max_retries: int = 3


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    task_name: Optional[str] = None
    task_type: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    is_enabled: Optional[bool] = None
    payload: Optional[Dict[str, Any]] = None
    max_retries: Optional[int] = None


class ScheduleSchema(ScheduleBase):
    id: uuid.UUID
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    last_run_duration_ms: Optional[int]
    next_run_at: Optional[datetime]
    retry_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
