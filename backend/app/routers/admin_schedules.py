"""
Schedules Admin Router
Provides CRUD operations for scheduled tasks
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.admin import Schedule
from app.schemas.admin.schedule import (
    ScheduleSchema,
    ScheduleCreate,
    ScheduleUpdate
)
from app.dependencies.auth import require_admin

router = APIRouter(
    prefix="/api/admin/v1/schedules",
    tags=["admin", "schedules"]
)


@router.get("", response_model=List[ScheduleSchema])
def list_schedules(
    is_enabled: bool | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get all schedules with optional filtering"""
    query = db.query(Schedule)

    if is_enabled is not None:
        query = query.filter(Schedule.is_enabled == is_enabled)

    schedules = query.order_by(Schedule.task_name).all()
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleSchema)
def get_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Get a specific schedule by ID"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found"
        )
    return schedule


@router.post("", response_model=ScheduleSchema, status_code=status.HTTP_201_CREATED)
def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Create a new schedule"""
    # Check if task_name already exists
    existing = db.query(Schedule).filter(Schedule.task_name == schedule_data.task_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Schedule with task_name '{schedule_data.task_name}' already exists"
        )

    schedule = Schedule(**schedule_data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleSchema)
def update_schedule(
    schedule_id: UUID,
    schedule_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Update a schedule"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found"
        )

    # Update only provided fields
    update_data = schedule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin)
):
    """Delete a schedule"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found"
        )

    db.delete(schedule)
    db.commit()
    return None
