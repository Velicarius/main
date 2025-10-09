"""
Tests for Authentication Middleware and Endpoint Protection
"""
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.core.auth_middleware import get_current_user, get_current_user_optional, CurrentUser
from app.core.jwt_auth import JWTAuth
from app.core.config import settings
from app.models.base import Base
from app.models.user import User
from app.database import get_db


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_app(test_db):
    """Create test FastAPI app with authentication"""
    app = FastAPI()

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Set JWT secret for testing
    settings.jwt_secret_key = "test-secret-for-middleware-tests"

    @app.get("/public")
    def public_endpoint():
        return {"message": "public"}

    @app.get("/protected")
    def protected_endpoint(current_user: CurrentUser = Depends(get_current_user)):
        return {
            "message": "protected",
            "user_id": str(current_user.user_id),
            "email": current_user.email
        }

    @app.get("/optional")
    def optional_endpoint(current_user: CurrentUser = Depends(get_current_user_optional)):
        if current_user:
            return {"authenticated": True, "user_id": str(current_user.user_id)}
        return {"authenticated": False}

    return app


@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        name="Test User"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def valid_token(test_user):
    """Create a valid JWT token for test user"""
    return JWTAuth.create_access_token(user_id=test_user.id, email=test_user.email)


class TestAuthenticationMiddleware:
    """Test authentication middleware and endpoint protection"""

    def test_public_endpoint_no_auth(self, test_app):
        """Test that public endpoints work without authentication"""
        client = TestClient(test_app)
        response = client.get("/public")

        assert response.status_code == 200
        assert response.json()["message"] == "public"

    def test_protected_endpoint_no_token(self, test_app):
        """Test that protected endpoints reject requests without token"""
        client = TestClient(test_app)
        response = client.get("/protected")

        assert response.status_code == 403  # FastAPI security returns 403 for no credentials

    def test_protected_endpoint_invalid_token(self, test_app):
        """Test that protected endpoints reject invalid tokens"""
        client = TestClient(test_app)
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
        assert "invalid token" in response.json()["detail"].lower()

    def test_protected_endpoint_expired_token(self, test_app, test_user):
        """Test that protected endpoints reject expired tokens"""
        from datetime import timedelta

        expired_token = JWTAuth.create_access_token(
            user_id=test_user.id,
            email=test_user.email,
            expires_delta=timedelta(seconds=-1)
        )

        client = TestClient(test_app)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_protected_endpoint_valid_token(self, test_app, test_user, valid_token):
        """Test that protected endpoints work with valid token"""
        client = TestClient(test_app)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {valid_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "protected"
        assert data["user_id"] == str(test_user.id)
        assert data["email"] == test_user.email

    def test_protected_endpoint_user_not_found(self, test_app, test_db):
        """Test that token with non-existent user fails"""
        # Create token for user that doesn't exist in DB
        fake_user_id = uuid.uuid4()
        token = JWTAuth.create_access_token(
            user_id=fake_user_id,
            email="nonexistent@example.com"
        )

        client = TestClient(test_app)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401
        assert "user not found" in response.json()["detail"].lower()

    def test_protected_endpoint_malformed_auth_header(self, test_app):
        """Test various malformed Authorization headers"""
        client = TestClient(test_app)

        # Missing "Bearer" prefix
        response = client.get(
            "/protected",
            headers={"Authorization": "some-token"}
        )
        assert response.status_code == 403

        # Empty Bearer
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401

    def test_optional_auth_no_token(self, test_app):
        """Test optional authentication without token"""
        client = TestClient(test_app)
        response = client.get("/optional")

        assert response.status_code == 200
        assert response.json()["authenticated"] is False

    def test_optional_auth_with_valid_token(self, test_app, test_user, valid_token):
        """Test optional authentication with valid token"""
        client = TestClient(test_app)
        response = client.get(
            "/optional",
            headers={"Authorization": f"Bearer {valid_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == str(test_user.id)

    def test_optional_auth_with_invalid_token(self, test_app):
        """Test optional authentication with invalid token returns not authenticated"""
        client = TestClient(test_app)
        response = client.get(
            "/optional",
            headers={"Authorization": "Bearer invalid.token"}
        )

        assert response.status_code == 200
        assert response.json()["authenticated"] is False
