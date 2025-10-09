"""Pydantic schemas for Feature Flags"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any, Dict
from decimal import Decimal
import uuid


class FeatureFlagBase(BaseModel):
    key: str
    value_type: str = "boolean"
    value_boolean: Optional[bool] = None
    value_string: Optional[str] = None
    value_json: Optional[Dict[str, Any]] = None
    value_number: Optional[Decimal] = None
    env_scope: str = "all"
    description: Optional[str] = None
    is_enabled: bool = True


class FeatureFlagCreate(FeatureFlagBase):
    pass


class FeatureFlagUpdate(BaseModel):
    key: Optional[str] = None
    value_type: Optional[str] = None
    value_boolean: Optional[bool] = None
    value_string: Optional[str] = None
    value_json: Optional[Dict[str, Any]] = None
    value_number: Optional[Decimal] = None
    env_scope: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class FeatureFlagSchema(FeatureFlagBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    current_value: Optional[Any] = None  # Computed field

    class Config:
        from_attributes = True
