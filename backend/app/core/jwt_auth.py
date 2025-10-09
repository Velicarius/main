"""
JWT Authentication Module
Handles token generation, validation, and user authentication
"""
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
from pydantic import BaseModel
from fastapi import HTTPException, status
from app.core.config import settings
import uuid


class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    email: str
    roles: List[str] = []
    exp: datetime


class JWTAuth:
    """JWT Authentication handler"""

    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

    @classmethod
    def _get_secret_key(cls) -> str:
        """Get JWT secret key from settings"""
        if not settings.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY must be set in environment variables")
        return settings.jwt_secret_key

    @classmethod
    def create_access_token(cls, user_id: uuid.UUID, email: str, roles: Optional[List[str]] = None, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a new JWT access token

        Args:
            user_id: User UUID
            email: User email
            roles: List of role names for the user
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "user_id": str(user_id),
            "email": email,
            "roles": roles or [],
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        encoded_jwt = jwt.encode(to_encode, cls._get_secret_key(), algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def decode_token(cls, token: str) -> TokenData:
        """
        Decode and validate JWT token

        Args:
            token: JWT token string

        Returns:
            TokenData with user information

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, cls._get_secret_key(), algorithms=[cls.ALGORITHM])
            user_id: str = payload.get("user_id")
            email: str = payload.get("email")
            roles: List[str] = payload.get("roles", [])
            exp: int = payload.get("exp")

            if user_id is None or email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user information",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return TokenData(
                user_id=user_id,
                email=email,
                roles=roles,
                exp=datetime.fromtimestamp(exp)
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @classmethod
    def verify_token(cls, token: str) -> bool:
        """
        Verify if token is valid without raising exceptions

        Args:
            token: JWT token string

        Returns:
            True if valid, False otherwise
        """
        try:
            cls.decode_token(token)
            return True
        except HTTPException:
            return False
