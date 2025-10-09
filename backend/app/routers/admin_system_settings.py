"""
System Settings Admin Router
Provides CRUD operations for system-wide settings
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.admin import SystemSetting
from app.schemas.admin.system_setting import (
    SystemSettingSchema,
    SystemSettingCreate,
    SystemSettingUpdate
)
from app.dependencies.auth import require_admin

router = APIRouter(
    prefix="/api/admin/v1/system-settings",
    tags=["admin", "system-settings"]
)


@router.get("", response_model=List[SystemSettingSchema])
def list_system_settings(
    category: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all system settings with optional filtering"""
    query = db.query(SystemSetting)

    if category:
        query = query.filter(SystemSetting.category == category)

    settings = query.order_by(SystemSetting.category, SystemSetting.key).all()
    return settings


@router.get("/{setting_id}", response_model=SystemSettingSchema)
def get_system_setting(
    setting_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific system setting by ID"""
    setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System setting {setting_id} not found"
        )
    return setting


@router.get("/by-key/{key}", response_model=SystemSettingSchema)
def get_system_setting_by_key(
    key: str,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a system setting by key"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System setting '{key}' not found"
        )
    return setting


@router.post("", response_model=SystemSettingSchema, status_code=status.HTTP_201_CREATED)
def create_system_setting(
    setting_data: SystemSettingCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Create a new system setting"""
    # Check if key already exists
    existing = db.query(SystemSetting).filter(SystemSetting.key == setting_data.key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"System setting with key '{setting_data.key}' already exists"
        )

    setting = SystemSetting(**setting_data.model_dump())
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


@router.patch("/{setting_id}", response_model=SystemSettingSchema)
def update_system_setting(
    setting_id: UUID,
    setting_data: SystemSettingUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Update a system setting"""
    setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System setting {setting_id} not found"
        )

    # Update only provided fields
    update_data = setting_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(setting, field, value)

    db.commit()
    db.refresh(setting)
    return setting


@router.delete("/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_system_setting(
    setting_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Delete a system setting"""
    setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System setting {setting_id} not found"
        )

    db.delete(setting)
    db.commit()
    return None
