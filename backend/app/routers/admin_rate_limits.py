"""
Rate Limits & Quotas Admin Router
Provides CRUD operations for rate limits and quotas
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.admin import RateLimit, Quota
from app.schemas.admin.rate_limit import (
    RateLimitSchema,
    RateLimitCreate,
    RateLimitUpdate,
    QuotaSchema,
    QuotaCreate,
    QuotaUpdate
)
from app.dependencies.auth import require_admin

router = APIRouter(
    prefix="/api/admin/v1/rate-limits",
    tags=["admin", "rate-limits"]
)


# Rate Limits endpoints

@router.get("", response_model=List[RateLimitSchema])
def list_rate_limits(
    scope_type: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all rate limits with optional filtering"""
    query = db.query(RateLimit)

    if scope_type:
        query = query.filter(RateLimit.scope_type == scope_type)

    limits = query.order_by(RateLimit.scope_type, RateLimit.scope_key).all()
    return limits


@router.get("/{limit_id}", response_model=RateLimitSchema)
def get_rate_limit(
    limit_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific rate limit by ID"""
    limit = db.query(RateLimit).filter(RateLimit.id == limit_id).first()
    if not limit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit {limit_id} not found"
        )
    return limit


@router.post("", response_model=RateLimitSchema, status_code=status.HTTP_201_CREATED)
def create_rate_limit(
    limit_data: RateLimitCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Create a new rate limit"""
    limit = RateLimit(**limit_data.model_dump())
    db.add(limit)
    db.commit()
    db.refresh(limit)
    return limit


@router.patch("/{limit_id}", response_model=RateLimitSchema)
def update_rate_limit(
    limit_id: UUID,
    limit_data: RateLimitUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Update a rate limit"""
    limit = db.query(RateLimit).filter(RateLimit.id == limit_id).first()
    if not limit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit {limit_id} not found"
        )

    # Update only provided fields
    update_data = limit_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(limit, field, value)

    db.commit()
    db.refresh(limit)
    return limit


@router.delete("/{limit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate_limit(
    limit_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Delete a rate limit"""
    limit = db.query(RateLimit).filter(RateLimit.id == limit_id).first()
    if not limit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit {limit_id} not found"
        )

    db.delete(limit)
    db.commit()
    return None


# Quotas endpoints

@router.get("/quotas", response_model=List[QuotaSchema], tags=["quotas"])
def list_quotas(
    scope_type: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all quotas with optional filtering"""
    query = db.query(Quota)

    if scope_type:
        query = query.filter(Quota.scope_type == scope_type)

    quotas = query.order_by(Quota.scope_type, Quota.scope_key).all()
    return quotas


@router.get("/quotas/{quota_id}", response_model=QuotaSchema, tags=["quotas"])
def get_quota(
    quota_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific quota by ID"""
    quota = db.query(Quota).filter(Quota.id == quota_id).first()
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quota {quota_id} not found"
        )
    return quota


@router.post("/quotas", response_model=QuotaSchema, status_code=status.HTTP_201_CREATED, tags=["quotas"])
def create_quota(
    quota_data: QuotaCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Create a new quota"""
    quota = Quota(**quota_data.model_dump())
    db.add(quota)
    db.commit()
    db.refresh(quota)
    return quota


@router.patch("/quotas/{quota_id}", response_model=QuotaSchema, tags=["quotas"])
def update_quota(
    quota_id: UUID,
    quota_data: QuotaUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Update a quota"""
    quota = db.query(Quota).filter(Quota.id == quota_id).first()
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quota {quota_id} not found"
        )

    # Update only provided fields
    update_data = quota_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quota, field, value)

    db.commit()
    db.refresh(quota)
    return quota


@router.delete("/quotas/{quota_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["quotas"])
def delete_quota(
    quota_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Delete a quota"""
    quota = db.query(Quota).filter(Quota.id == quota_id).first()
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quota {quota_id} not found"
        )

    db.delete(quota)
    db.commit()
    return None
