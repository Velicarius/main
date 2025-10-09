"""
Pydantic schemas for API Providers and Credentials
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


# ==================== API PROVIDER ====================

class ApiProviderBase(BaseModel):
    """Base schema for API Provider"""
    type: str = Field(..., description="Provider type: news, crypto, llm, eod")
    name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    base_url: Optional[str] = Field(None, max_length=500)
    is_enabled: bool = Field(default=True)
    is_shadow_mode: bool = Field(default=False, description="Test mode without using results")
    priority: int = Field(default=100, description="Lower = higher priority")
    timeout_seconds: int = Field(default=10, ge=1, le=300)
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ApiProviderCreate(ApiProviderBase):
    """Schema for creating new API Provider"""
    pass


class ApiProviderUpdate(BaseModel):
    """Schema for updating API Provider"""
    type: Optional[str] = None
    name: Optional[str] = None
    base_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_shadow_mode: Optional[bool] = None
    priority: Optional[int] = None
    timeout_seconds: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None


class ApiProviderSchema(ApiProviderBase):
    """Complete API Provider schema"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True


# ==================== API CREDENTIAL ====================

class ApiCredentialBase(BaseModel):
    """Base schema for API Credential"""
    provider_id: uuid.UUID
    key_name: str = Field(..., min_length=1, max_length=100)
    masked_key: Optional[str] = Field(None, max_length=100)
    status: str = Field(default="active", description="active, expired, invalid")
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class ApiCredentialCreate(ApiCredentialBase):
    """Schema for creating new API Credential"""
    plain_key: Optional[str] = Field(None, description="Actual API key (will be encrypted)")


class ApiCredentialUpdate(BaseModel):
    """Schema for updating API Credential"""
    key_name: Optional[str] = None
    masked_key: Optional[str] = None
    plain_key: Optional[str] = Field(None, description="Update API key")
    status: Optional[str] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class ApiCredentialSchema(ApiCredentialBase):
    """Complete API Credential schema"""
    id: uuid.UUID
    last_check_at: Optional[datetime]
    last_check_status: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True
