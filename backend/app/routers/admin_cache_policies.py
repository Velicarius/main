"""
Cache Policies Admin Router
Provides CRUD operations for cache policies
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.admin import CachePolicy
from app.schemas.admin.cache_policy import (
    CachePolicySchema,
    CachePolicyCreate,
    CachePolicyUpdate
)
from app.dependencies.auth import require_admin

router = APIRouter(
    prefix="/api/admin/v1/cache-policies",
    tags=["admin", "cache-policies"]
)


@router.get("", response_model=List[CachePolicySchema])
def list_cache_policies(
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all cache policies"""
    policies = db.query(CachePolicy).order_by(CachePolicy.dataset_name).all()
    return policies


@router.get("/{policy_id}", response_model=CachePolicySchema)
def get_cache_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific cache policy by ID"""
    policy = db.query(CachePolicy).filter(CachePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cache policy {policy_id} not found"
        )
    return policy


@router.get("/by-dataset/{dataset_name}", response_model=CachePolicySchema)
def get_cache_policy_by_dataset(
    dataset_name: str,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a cache policy by dataset name"""
    policy = db.query(CachePolicy).filter(CachePolicy.dataset_name == dataset_name).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cache policy for dataset '{dataset_name}' not found"
        )
    return policy


@router.post("", response_model=CachePolicySchema, status_code=status.HTTP_201_CREATED)
def create_cache_policy(
    policy_data: CachePolicyCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Create a new cache policy"""
    # Check if dataset_name already exists
    existing = db.query(CachePolicy).filter(CachePolicy.dataset_name == policy_data.dataset_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cache policy for dataset '{policy_data.dataset_name}' already exists"
        )

    policy = CachePolicy(**policy_data.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.patch("/{policy_id}", response_model=CachePolicySchema)
def update_cache_policy(
    policy_id: UUID,
    policy_data: CachePolicyUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Update a cache policy"""
    policy = db.query(CachePolicy).filter(CachePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cache policy {policy_id} not found"
        )

    # Update only provided fields
    update_data = policy_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cache_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Delete a cache policy"""
    policy = db.query(CachePolicy).filter(CachePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cache policy {policy_id} not found"
        )

    db.delete(policy)
    db.commit()
    return None
