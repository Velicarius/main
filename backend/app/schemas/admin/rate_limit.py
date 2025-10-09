"""Pydantic schemas for Rate Limits and Quotas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class RateLimitBase(BaseModel):
    scope: str
    scope_id: Optional[str] = None
    window_seconds: int
    limit: int
    burst: Optional[int] = None
    policy: str = Field(default="reject")
    is_enabled: bool = True


class RateLimitCreate(RateLimitBase):
    pass


class RateLimitUpdate(BaseModel):
    scope: Optional[str] = None
    scope_id: Optional[str] = None
    window_seconds: Optional[int] = None
    limit: Optional[int] = None
    burst: Optional[int] = None
    policy: Optional[str] = None
    is_enabled: Optional[bool] = None


class RateLimitSchema(RateLimitBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuotaBase(BaseModel):
    scope: str
    scope_id: Optional[str] = None
    resource_type: str
    period: str
    hard_cap: int
    soft_cap: Optional[int] = None
    current_usage: int = 0
    period_start: datetime
    period_end: datetime
    action_on_breach: str = Field(default="block")
    is_enabled: bool = True


class QuotaCreate(QuotaBase):
    pass


class QuotaUpdate(BaseModel):
    scope: Optional[str] = None
    scope_id: Optional[str] = None
    resource_type: Optional[str] = None
    period: Optional[str] = None
    hard_cap: Optional[int] = None
    soft_cap: Optional[int] = None
    current_usage: Optional[int] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    action_on_breach: Optional[str] = None
    is_enabled: Optional[bool] = None


class QuotaSchema(QuotaBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    usage_percentage: Optional[float] = None
    is_over_soft_cap: Optional[bool] = None
    is_over_hard_cap: Optional[bool] = None

    class Config:
        from_attributes = True
