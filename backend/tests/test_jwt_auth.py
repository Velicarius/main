"""
Tests for JWT Authentication
"""
import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
import jwt as pyjwt
import uuid

from app.core.jwt_auth import JWTAuth, TokenData
from app.core.config import settings


@pytest.fixture
def test_user_id():
    """Test user UUID"""
    return uuid.uuid4()


@pytest.fixture
def test_email():
    """Test email"""
    return "test@example.com"


@pytest.fixture
def valid_secret():
    """Set valid JWT secret for tests"""
    original = settings.jwt_secret_key
    settings.jwt_secret_key = "test-secret-key-for-testing-purposes"
    yield settings.jwt_secret_key
    settings.jwt_secret_key = original


class TestJWTAuth:
    """Test JWT authentication functionality"""

    def test_create_access_token(self, test_user_id, test_email, valid_secret):
        """Test creating a JWT access token"""
        token = JWTAuth.create_access_token(user_id=test_user_id, email=test_email)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = pyjwt.decode(token, valid_secret, algorithms=[JWTAuth.ALGORITHM])
        assert payload["user_id"] == str(test_user_id)
        assert payload["email"] == test_email
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_with_custom_expiry(self, test_user_id, test_email, valid_secret):
        """Test creating token with custom expiration"""
        expires_delta = timedelta(minutes=15)
        token = JWTAuth.create_access_token(
            user_id=test_user_id,
            email=test_email,
            expires_delta=expires_delta
        )

        payload = pyjwt.decode(token, valid_secret, algorithms=[JWTAuth.ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])

        # Check expiration is approximately 15 minutes from issue time
        time_diff = (exp_time - iat_time).total_seconds()
        assert 14 * 60 < time_diff < 16 * 60  # Between 14 and 16 minutes

    def test_decode_valid_token(self, test_user_id, test_email, valid_secret):
        """Test decoding a valid token"""
        token = JWTAuth.create_access_token(user_id=test_user_id, email=test_email)
        token_data = JWTAuth.decode_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == str(test_user_id)
        assert token_data.email == test_email
        assert isinstance(token_data.exp, datetime)

    def test_decode_expired_token(self, test_user_id, test_email, valid_secret):
        """Test decoding an expired token raises exception"""
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = JWTAuth.create_access_token(
            user_id=test_user_id,
            email=test_email,
            expires_delta=expires_delta
        )

        with pytest.raises(HTTPException) as exc_info:
            JWTAuth.decode_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_decode_invalid_token(self, valid_secret):
        """Test decoding an invalid token raises exception"""
        invalid_token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            JWTAuth.decode_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "invalid token" in exc_info.value.detail.lower()

    def test_decode_token_wrong_secret(self, test_user_id, test_email):
        """Test token created with different secret fails validation"""
        # Create token with one secret
        settings.jwt_secret_key = "secret1"
        token = JWTAuth.create_access_token(user_id=test_user_id, email=test_email)

        # Try to decode with different secret
        settings.jwt_secret_key = "secret2"
        with pytest.raises(HTTPException) as exc_info:
            JWTAuth.decode_token(token)

        assert exc_info.value.status_code == 401

    def test_decode_token_missing_user_id(self, valid_secret):
        """Test token without user_id fails validation"""
        # Manually create token without user_id
        payload = {
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = pyjwt.encode(payload, valid_secret, algorithm=JWTAuth.ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            JWTAuth.decode_token(token)

        assert exc_info.value.status_code == 401
        assert "missing user information" in exc_info.value.detail.lower()

    def test_decode_token_missing_email(self, test_user_id, valid_secret):
        """Test token without email fails validation"""
        payload = {
            "user_id": str(test_user_id),
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = pyjwt.encode(payload, valid_secret, algorithm=JWTAuth.ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            JWTAuth.decode_token(token)

        assert exc_info.value.status_code == 401
        assert "missing user information" in exc_info.value.detail.lower()

    def test_verify_token_valid(self, test_user_id, test_email, valid_secret):
        """Test verify_token returns True for valid token"""
        token = JWTAuth.create_access_token(user_id=test_user_id, email=test_email)
        assert JWTAuth.verify_token(token) is True

    def test_verify_token_invalid(self, valid_secret):
        """Test verify_token returns False for invalid token"""
        assert JWTAuth.verify_token("invalid.token.here") is False

    def test_verify_token_expired(self, test_user_id, test_email, valid_secret):
        """Test verify_token returns False for expired token"""
        expires_delta = timedelta(seconds=-1)
        token = JWTAuth.create_access_token(
            user_id=test_user_id,
            email=test_email,
            expires_delta=expires_delta
        )
        assert JWTAuth.verify_token(token) is False

    def test_no_secret_key_raises_error(self, test_user_id, test_email):
        """Test that missing JWT_SECRET_KEY raises error"""
        settings.jwt_secret_key = None

        with pytest.raises(ValueError) as exc_info:
            JWTAuth.create_access_token(user_id=test_user_id, email=test_email)

        assert "JWT_SECRET_KEY must be set" in str(exc_info.value)
