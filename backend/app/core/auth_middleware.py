"""
Authentication Middleware and Dependencies
Protects endpoints with JWT authentication and provides current user context
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.core.jwt_auth import JWTAuth
from app.database import get_db
from app.models.user import User


# HTTP Bearer security scheme
security = HTTPBearer()


class CurrentUser:
    """Current authenticated user context"""

    def __init__(self, user_id: uuid.UUID, email: str, db_user: Optional[User] = None):
        self.user_id = user_id
        self.email = email
        self.db_user = db_user

    def __str__(self):
        return f"User({self.user_id}, {self.email})"


def get_token_from_request(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extract JWT token from Authorization header

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        JWT token string

    Raises:
        HTTPException: If no token provided
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(
    token: str = Depends(get_token_from_request),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """
    Dependency to get current authenticated user from JWT token

    Args:
        token: JWT token from request
        db: Database session

    Returns:
        CurrentUser with user information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Decode and validate token
    token_data = JWTAuth.decode_token(token)

    # Get user from database
    try:
        user_uuid = uuid.UUID(token_data.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    db_user = db.query(User).filter(User.id == user_uuid).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return CurrentUser(
        user_id=user_uuid,
        email=token_data.email,
        db_user=db_user
    )


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[CurrentUser]:
    """
    Optional authentication - returns None if no valid token

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        CurrentUser if authenticated, None otherwise
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")

    try:
        token_data = JWTAuth.decode_token(token)
        user_uuid = uuid.UUID(token_data.user_id)
        db_user = db.query(User).filter(User.id == user_uuid).first()

        if db_user:
            return CurrentUser(
                user_id=user_uuid,
                email=token_data.email,
                db_user=db_user
            )
    except Exception:
        pass

    return None


def require_user_isolation(
    resource_user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user)
) -> None:
    """
    Verify that the current user owns the resource

    Args:
        resource_user_id: User ID that owns the resource
        current_user: Current authenticated user

    Raises:
        HTTPException: If user doesn't own the resource
    """
    if current_user.user_id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
