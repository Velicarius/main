"""Pydantic schemas for Audit Log"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class AuditLogSchema(BaseModel):
    """Read-only schema for Audit Log"""
    id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    actor_type: str
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID]
    entity_name: Optional[str]
    before_state: Optional[Dict[str, Any]]
    after_state: Optional[Dict[str, Any]]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
