"""
Audit Log Admin Router
Provides read-only access to audit logs
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from app.database import get_db
from app.models.admin import AuditLog
from app.schemas.admin.audit_log import AuditLogSchema
from app.dependencies.auth import require_admin

router = APIRouter(
    prefix="/api/admin/v1/audit-log",
    tags=["admin", "audit-log"]
)


@router.get("", response_model=List[AuditLogSchema])
def list_audit_logs(
    action: str | None = None,
    entity_type: str | None = None,
    actor_id: UUID | None = None,
    limit: int = Query(100, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """
    Get audit logs with optional filtering
    Read-only endpoint - audit logs cannot be modified or deleted
    """
    query = db.query(AuditLog)

    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)

    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc())

    # Apply pagination
    logs = query.offset(offset).limit(limit).all()
    return logs


@router.get("/{log_id}", response_model=AuditLogSchema)
def get_audit_log(
    log_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific audit log entry by ID"""
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log {log_id} not found"
        )
    return log


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[AuditLogSchema])
def get_audit_logs_for_entity(
    entity_type: str,
    entity_id: UUID,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all audit logs for a specific entity"""
    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id
        )
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return logs
