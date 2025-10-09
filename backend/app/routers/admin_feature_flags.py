"""
Feature Flags Admin Router
Provides CRUD operations for feature flags
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.admin import FeatureFlag
from app.schemas.admin.feature_flag import (
    FeatureFlagSchema,
    FeatureFlagCreate,
    FeatureFlagUpdate
)
from app.dependencies.auth import require_admin

router = APIRouter(
    prefix="/api/admin/v1/feature-flags",
    tags=["admin", "feature-flags"]
)


@router.get("", response_model=List[FeatureFlagSchema])
def list_feature_flags(
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all feature flags"""
    flags = db.query(FeatureFlag).order_by(FeatureFlag.key).all()
    return flags


@router.get("/{flag_id}", response_model=FeatureFlagSchema)
def get_feature_flag(
    flag_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific feature flag by ID"""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag {flag_id} not found"
        )
    return flag


@router.get("/by-key/{key}", response_model=FeatureFlagSchema)
def get_feature_flag_by_key(
    key: str,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific feature flag by key"""
    flag = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{key}' not found"
        )
    return flag


@router.post("", response_model=FeatureFlagSchema, status_code=status.HTTP_201_CREATED)
def create_feature_flag(
    flag_data: FeatureFlagCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Create a new feature flag"""
    # Check if key already exists
    existing = db.query(FeatureFlag).filter(FeatureFlag.key == flag_data.key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feature flag with key '{flag_data.key}' already exists"
        )

    flag = FeatureFlag(**flag_data.model_dump())
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


@router.patch("/{flag_id}", response_model=FeatureFlagSchema)
def update_feature_flag(
    flag_id: UUID,
    flag_data: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Update a feature flag"""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag {flag_id} not found"
        )

    # Update only provided fields
    update_data = flag_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flag, field, value)

    db.commit()
    db.refresh(flag)
    return flag


@router.delete("/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feature_flag(
    flag_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Delete a feature flag"""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag {flag_id} not found"
        )

    db.delete(flag)
    db.commit()
    return None
