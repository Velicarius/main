"""
Tests for Role-Based Access Control (RBAC) system
Tests JWT token generation with roles, role checking, and admin endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from app.main import app
from app.models.user import User
from app.models.role import Role, UserRole
from app.core.jwt_auth import JWTAuth
from app.security import hash_password


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user without any roles"""
    user = User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        name="Test User",
        password_hash=hash_password("testpass123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create a test user with admin role"""
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        name="Admin User",
        password_hash=hash_password("adminpass123")
    )
    db_session.add(user)
    db_session.flush()

    # Find or create admin role
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(
            id=uuid.uuid4(),
            name="admin",
            description="Administrator role"
        )
        db_session.add(admin_role)
        db_session.flush()

    # Assign admin role
    user_role = UserRole(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=admin_role.id
    )
    db_session.add(user_role)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def ops_user(db_session: Session) -> User:
    """Create a test user with ops role"""
    user = User(
        id=uuid.uuid4(),
        email="ops@example.com",
        name="Ops User",
        password_hash=hash_password("opspass123")
    )
    db_session.add(user)
    db_session.flush()

    # Find or create ops role
    ops_role = db_session.query(Role).filter(Role.name == "ops").first()
    if not ops_role:
        ops_role = Role(
            id=uuid.uuid4(),
            name="ops",
            description="Operations role"
        )
        db_session.add(ops_role)
        db_session.flush()

    # Assign ops role
    user_role = UserRole(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=ops_role.id
    )
    db_session.add(user_role)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestJWTWithRoles:
    """Test JWT token generation and validation with roles"""

    def test_create_token_with_roles(self):
        """Test creating JWT token with roles"""
        user_id = uuid.uuid4()
        email = "test@example.com"
        roles = ["user", "admin"]

        token = JWTAuth.create_access_token(user_id, email, roles)

        assert token is not None
        assert isinstance(token, str)

    def test_decode_token_with_roles(self):
        """Test decoding JWT token and extracting roles"""
        user_id = uuid.uuid4()
        email = "test@example.com"
        roles = ["user", "admin"]

        token = JWTAuth.create_access_token(user_id, email, roles)
        token_data = JWTAuth.decode_token(token)

        assert token_data.user_id == str(user_id)
        assert token_data.email == email
        assert token_data.roles == roles

    def test_decode_token_without_roles(self):
        """Test decoding token without roles (backward compatibility)"""
        user_id = uuid.uuid4()
        email = "test@example.com"

        token = JWTAuth.create_access_token(user_id, email)
        token_data = JWTAuth.decode_token(token)

        assert token_data.user_id == str(user_id)
        assert token_data.email == email
        assert token_data.roles == []


class TestUserRoles:
    """Test user role assignments and queries"""

    def test_user_has_no_roles_initially(self, test_user: User):
        """Test that new user has no roles"""
        assert test_user.roles == []

    def test_user_has_admin_role(self, admin_user: User):
        """Test that admin user has admin role"""
        assert "admin" in admin_user.roles

    def test_user_has_ops_role(self, ops_user: User):
        """Test that ops user has ops role"""
        assert "ops" in ops_user.roles

    def test_user_multiple_roles(self, db_session: Session, test_user: User):
        """Test user can have multiple roles"""
        # Add admin role
        admin_role = db_session.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(id=uuid.uuid4(), name="admin", description="Admin")
            db_session.add(admin_role)
            db_session.flush()

        user_role1 = UserRole(
            id=uuid.uuid4(),
            user_id=test_user.id,
            role_id=admin_role.id
        )
        db_session.add(user_role1)

        # Add ops role
        ops_role = db_session.query(Role).filter(Role.name == "ops").first()
        if not ops_role:
            ops_role = Role(id=uuid.uuid4(), name="ops", description="Ops")
            db_session.add(ops_role)
            db_session.flush()

        user_role2 = UserRole(
            id=uuid.uuid4(),
            user_id=test_user.id,
            role_id=ops_role.id
        )
        db_session.add(user_role2)
        db_session.commit()
        db_session.refresh(test_user)

        assert "admin" in test_user.roles
        assert "ops" in test_user.roles
        assert len(test_user.roles) == 2


class TestAdminEndpoints:
    """Test admin user management endpoints"""

    def test_list_users_as_admin(self, admin_user: User):
        """Test listing users as admin"""
        client = TestClient(app)
        token = JWTAuth.create_access_token(
            admin_user.id,
            admin_user.email,
            admin_user.roles
        )

        response = client.get(
            "/api/admin/v1/users",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)

    def test_list_users_as_regular_user_forbidden(self, test_user: User):
        """Test that regular user cannot list users"""
        client = TestClient(app)
        token = JWTAuth.create_access_token(
            test_user.id,
            test_user.email,
            test_user.roles
        )

        response = client.get(
            "/api/admin/v1/users",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    def test_list_users_without_auth_unauthorized(self):
        """Test that unauthenticated request is rejected"""
        client = TestClient(app)

        response = client.get("/api/admin/v1/users")

        assert response.status_code == 403

    def test_get_user_roles_as_admin(self, admin_user: User, test_user: User):
        """Test getting user roles as admin"""
        client = TestClient(app)
        token = JWTAuth.create_access_token(
            admin_user.id,
            admin_user.email,
            admin_user.roles
        )

        response = client.get(
            f"/api/admin/v1/users/{test_user.id}/roles",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)

    def test_assign_role_as_admin(self, admin_user: User, test_user: User, db_session: Session):
        """Test assigning role to user as admin"""
        client = TestClient(app)
        token = JWTAuth.create_access_token(
            admin_user.id,
            admin_user.email,
            admin_user.roles
        )

        # Ensure user role exists
        user_role = db_session.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(id=uuid.uuid4(), name="user", description="User")
            db_session.add(user_role)
            db_session.commit()

        response = client.post(
            f"/api/admin/v1/users/{test_user.id}/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"role_name": "user"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"

    def test_assign_role_as_regular_user_forbidden(self, test_user: User):
        """Test that regular user cannot assign roles"""
        client = TestClient(app)
        token = JWTAuth.create_access_token(
            test_user.id,
            test_user.email,
            test_user.roles
        )

        other_user_id = uuid.uuid4()

        response = client.post(
            f"/api/admin/v1/users/{other_user_id}/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"role_name": "admin"}
        )

        assert response.status_code == 403

    def test_remove_role_as_admin(self, admin_user: User, db_session: Session):
        """Test removing role from user as admin"""
        # Create test user with user role
        test_user = User(
            id=uuid.uuid4(),
            email="roletest@example.com",
            name="Role Test",
            password_hash=hash_password("test123")
        )
        db_session.add(test_user)
        db_session.flush()

        # Assign user role
        user_role_obj = db_session.query(Role).filter(Role.name == "user").first()
        if not user_role_obj:
            user_role_obj = Role(id=uuid.uuid4(), name="user", description="User")
            db_session.add(user_role_obj)
            db_session.flush()

        user_role_assignment = UserRole(
            id=uuid.uuid4(),
            user_id=test_user.id,
            role_id=user_role_obj.id
        )
        db_session.add(user_role_assignment)
        db_session.commit()

        client = TestClient(app)
        token = JWTAuth.create_access_token(
            admin_user.id,
            admin_user.email,
            admin_user.roles
        )

        response = client.delete(
            f"/api/admin/v1/users/{test_user.id}/roles/user",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "user"

    def test_list_roles_as_admin(self, admin_user: User):
        """Test listing all roles as admin"""
        client = TestClient(app)
        token = JWTAuth.create_access_token(
            admin_user.id,
            admin_user.email,
            admin_user.roles
        )

        response = client.get(
            "/api/admin/v1/roles",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)


class TestAuthLogin:
    """Test login returns JWT with roles"""

    def test_login_returns_token_with_roles(self, admin_user: User):
        """Test that login includes user roles in JWT"""
        client = TestClient(app)

        response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@example.com",
                "password": "adminpass123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

        # Decode token and verify roles
        token_data = JWTAuth.decode_token(data["access_token"])
        assert "admin" in token_data.roles
