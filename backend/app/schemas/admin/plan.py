"""Pydantic schemas for Plans"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class PlanBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    features: Dict[str, Any] = {}
    limits: Dict[str, Any] = {}
    is_active: bool = True


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PlanSchema(PlanBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
