"""Pydantic schemas for Cache Policies"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class CachePolicyBase(BaseModel):
    dataset: str
    ttl_seconds: int
    swr_enabled: bool = False
    swr_stale_seconds: Optional[int] = None
    swr_refresh_threshold: Optional[int] = None
    etag_enabled: bool = False
    ims_enabled: bool = False
    purge_allowed: bool = True
    compression_enabled: bool = False
    circuit_breaker_enabled: bool = False
    circuit_breaker_threshold: Optional[int] = 3
    circuit_breaker_window_seconds: Optional[int] = 300
    circuit_breaker_recovery_seconds: Optional[int] = 600
    meta: Optional[Dict[str, Any]] = {}


class CachePolicyCreate(CachePolicyBase):
    pass


class CachePolicyUpdate(BaseModel):
    dataset: Optional[str] = None
    ttl_seconds: Optional[int] = None
    swr_enabled: Optional[bool] = None
    swr_stale_seconds: Optional[int] = None
    swr_refresh_threshold: Optional[int] = None
    etag_enabled: Optional[bool] = None
    ims_enabled: Optional[bool] = None
    purge_allowed: Optional[bool] = None
    compression_enabled: Optional[bool] = None
    circuit_breaker_enabled: Optional[bool] = None
    circuit_breaker_threshold: Optional[int] = None
    circuit_breaker_window_seconds: Optional[int] = None
    circuit_breaker_recovery_seconds: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None


class CachePolicySchema(CachePolicyBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    effective_ttl: Optional[int] = None  # Computed field

    class Config:
        from_attributes = True
