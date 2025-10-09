"""
Admin User Management Router
Endpoints for managing users and their roles (admin-only)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app.models.user import User
from app.models.role import Role, UserRole
from app.schemas.role import (
    UserWithRoles,
    RoleSchema,
    AssignRoleRequest,
    RemoveRoleRequest
)
from app.dependencies import require_admin, get_current_user

router = APIRouter(prefix="/api/admin/v1", tags=["admin-users"])


@router.get("/users", response_model=List[UserWithRoles], dependencies=[Depends(require_admin)])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all users with their roles (admin only)

    Args:
        skip: Number of users to skip (pagination)
        limit: Maximum number of users to return
        db: Database session

    Returns:
        List of users with their roles
    """
    users = db.query(User).offset(skip).limit(limit).all()

    return [
        UserWithRoles(
            id=user.id,
            email=user.email,
            name=user.name,
            roles=user.roles
        )
        for user in users
    ]


@router.get("/users/{user_id}", response_model=UserWithRoles, dependencies=[Depends(require_admin)])
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get specific user with their roles (admin only)

    Args:
        user_id: UUID of the user
        db: Database session

    Returns:
        User with roles

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserWithRoles(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=user.roles
    )


@router.get("/users/{user_id}/roles", response_model=List[RoleSchema], dependencies=[Depends(require_admin)])
def get_user_roles(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get all roles for a specific user (admin only)

    Args:
        user_id: UUID of the user
        db: Database session

    Returns:
        List of roles assigned to the user

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get role objects through user_roles relationship
    roles = [ur.role for ur in user.user_roles if ur.role]

    return roles


@router.post("/users/{user_id}/roles", status_code=status.HTTP_201_CREATED)
def assign_role(
    user_id: uuid.UUID,
    request: AssignRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign a role to a user (admin only)

    Args:
        user_id: UUID of the user
        request: Role assignment request with role_name
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Success message with assigned role

    Raises:
        HTTPException: If user or role not found, or role already assigned
    """
    # Check if admin
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Find role
    role = db.query(Role).filter(Role.name == request.role_name).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{request.role_name}' not found"
        )

    # Check if user already has this role
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User already has role '{request.role_name}'"
        )

    # Create user-role assignment
    user_role = UserRole(
        user_id=user_id,
        role_id=role.id,
        assigned_by=current_user.id
    )

    db.add(user_role)
    db.commit()

    return {
        "message": f"Role '{request.role_name}' assigned to user",
        "user_id": str(user_id),
        "role": request.role_name
    }


@router.delete("/users/{user_id}/roles/{role_name}", status_code=status.HTTP_200_OK)
def remove_role(
    user_id: uuid.UUID,
    role_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a role from a user (admin only)

    Args:
        user_id: UUID of the user
        role_name: Name of the role to remove
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If user or role not found, or user doesn't have the role
    """
    # Check if admin
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Find role
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found"
        )

    # Find user-role assignment
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id
    ).first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User does not have role '{role_name}'"
        )

    # Delete the assignment
    db.delete(user_role)
    db.commit()

    return {
        "message": f"Role '{role_name}' removed from user",
        "user_id": str(user_id),
        "role": role_name
    }


@router.get("/roles", response_model=List[RoleSchema], dependencies=[Depends(require_admin)])
def list_roles(db: Session = Depends(get_db)):
    """
    List all available roles (admin only)

    Args:
        db: Database session

    Returns:
        List of all roles in the system
    """
    roles = db.query(Role).all()
    return roles
