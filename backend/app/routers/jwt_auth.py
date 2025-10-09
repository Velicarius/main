"""
JWT Authentication Router
Handles login, token generation, and user registration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from uuid import uuid4

from app.database import get_db
from app.models.user import User
from app.core.jwt_auth import JWTAuth
from app.security import hash_password, verify_password


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user and return JWT token

    Args:
        request: Registration data with email and password
        db: Database session

    Returns:
        JWT token for the new user

    Raises:
        HTTPException: If email already exists
    """
    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user_id = uuid4()
    password_hash = hash_password(request.password)

    new_user = User(
        id=user_id,
        email=request.email,
        name=request.name or request.email.split("@")[0],
        password_hash=password_hash
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Assign default 'user' role to new users
    from app.models.role import Role, UserRole
    user_role = db.query(Role).filter(Role.name == "user").first()
    if user_role:
        user_role_assignment = UserRole(
            user_id=new_user.id,
            role_id=user_role.id,
            assigned_by=None  # System assignment
        )
        db.add(user_role_assignment)
        db.commit()
        db.refresh(new_user)

    # Get user roles (now includes default 'user' role)
    user_roles = new_user.roles

    # Generate token with roles
    access_token = JWTAuth.create_access_token(
        user_id=new_user.id,
        email=new_user.email,
        roles=user_roles
    )

    return TokenResponse(
        access_token=access_token,
        user_id=str(new_user.id),
        email=new_user.email
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password, return JWT token

    Args:
        request: Login credentials
        db: Database session

    Returns:
        JWT token for authenticated user

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Get user roles
    user_roles = user.roles

    # Generate token with roles
    access_token = JWTAuth.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=user_roles
    )

    return TokenResponse(
        access_token=access_token,
        user_id=str(user.id),
        email=user.email
    )


@router.get("/verify")
def verify_token(token: str):
    """
    Verify if a JWT token is valid

    Args:
        token: JWT token to verify

    Returns:
        Token validity and user information
    """
    try:
        token_data = JWTAuth.decode_token(token)
        return {
            "valid": True,
            "user_id": token_data.user_id,
            "email": token_data.email,
            "roles": token_data.roles,
            "expires": token_data.exp.isoformat()
        }
    except HTTPException as e:
        return {
            "valid": False,
            "error": e.detail
        }


@router.post("/token-from-session", response_model=TokenResponse)
def get_token_from_session(db: Session = Depends(get_db)):
    """
    Get JWT token for already authenticated session user
    This endpoint uses cookie-based session authentication to identify the user
    and issues a JWT token for accessing JWT-protected endpoints

    Returns:
        JWT token for the currently authenticated user

    Raises:
        HTTPException: If user is not authenticated via session
    """
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest

    # This is a simplified version - in production you'd check the session cookie
    # For now, we'll require the user to provide their email
    # A proper implementation would integrate with your existing session middleware

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Session-to-JWT conversion requires session middleware integration. Please use /api/auth/login instead."
    )
