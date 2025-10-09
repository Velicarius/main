"""Pydantic schemas for System Settings"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class SystemSettingBase(BaseModel):
    category: str
    key: str
    value_type: str = "string"
    value: Optional[str] = None
    value_json: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_secret: bool = False
    validation_regex: Optional[str] = None


class SystemSettingCreate(SystemSettingBase):
    pass


class SystemSettingUpdate(BaseModel):
    category: Optional[str] = None
    key: Optional[str] = None
    value_type: Optional[str] = None
    value: Optional[str] = None
    value_json: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_secret: Optional[bool] = None
    validation_regex: Optional[str] = None


class SystemSettingSchema(SystemSettingBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
