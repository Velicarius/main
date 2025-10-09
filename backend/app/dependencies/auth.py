"""
Auth dependencies for FastAPI endpoints
Provides JWT authentication and role-based access control
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.core.jwt_auth import JWTAuth, TokenData
from app.database import get_db
from app.models.user import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    token_data: TokenData = JWTAuth.decode_token(token)

    # Get user from database
    user_id = uuid.UUID(token_data.user_id)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token is provided, otherwise return None
    Useful for endpoints that work with or without authentication

    Args:
        credentials: Optional Bearer token
        db: Database session

    Returns:
        User object or None
    """
    if not credentials:
        return None

    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency factory that checks if user has a specific role

    Args:
        required_role: Name of the role required (e.g., 'admin', 'ops')

    Returns:
        Dependency function that validates user has the role

    Example:
        @router.get("/admin/users", dependencies=[Depends(require_role("admin"))])
        def list_users():
            ...
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        user_roles = user.roles

        if required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )

        return user

    return role_checker


def require_any_role(required_roles: List[str]):
    """
    Dependency factory that checks if user has any of the specified roles

    Args:
        required_roles: List of acceptable role names

    Returns:
        Dependency function that validates user has at least one role

    Example:
        @router.get("/ops/tasks", dependencies=[Depends(require_any_role(["admin", "ops"]))])
        def list_tasks():
            ...
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        user_roles = user.roles

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )

        return user

    return role_checker


# Pre-built dependencies for common roles
require_admin = require_role("admin")
require_ops = require_role("ops")
require_admin_or_ops = require_any_role(["admin", "ops"])
