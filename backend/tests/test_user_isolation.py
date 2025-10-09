"""
Tests for User Isolation in Portfolio Data
Ensures users can only access their own positions
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
from decimal import Decimal

from app.main import app
from app.core.jwt_auth import JWTAuth
from app.core.config import settings
from app.models.base import Base
from app.models.user import User
from app.models.position import Position
from app.database import get_db


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_isolation.db"
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
def client(test_db):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    settings.jwt_secret_key = "test-secret-for-isolation-tests"

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def user1(test_db):
    """Create first test user"""
    user = User(
        id=uuid.uuid4(),
        email="user1@example.com",
        name="User One"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def user2(test_db):
    """Create second test user"""
    user = User(
        id=uuid.uuid4(),
        email="user2@example.com",
        name="User Two"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def user1_token(user1):
    """Create JWT token for user1"""
    return JWTAuth.create_access_token(user_id=user1.id, email=user1.email)


@pytest.fixture
def user2_token(user2):
    """Create JWT token for user2"""
    return JWTAuth.create_access_token(user_id=user2.id, email=user2.email)


@pytest.fixture
def user1_positions(test_db, user1):
    """Create positions for user1"""
    positions = [
        Position(
            user_id=user1.id,
            symbol="AAPL.US",
            quantity=Decimal("10"),
            buy_price=Decimal("150.00"),
            currency="USD",
            account="default"
        ),
        Position(
            user_id=user1.id,
            symbol="MSFT.US",
            quantity=Decimal("5"),
            buy_price=Decimal("300.00"),
            currency="USD",
            account="default"
        )
    ]
    for pos in positions:
        test_db.add(pos)
    test_db.commit()
    for pos in positions:
        test_db.refresh(pos)
    return positions


@pytest.fixture
def user2_positions(test_db, user2):
    """Create positions for user2"""
    positions = [
        Position(
            user_id=user2.id,
            symbol="GOOGL.US",
            quantity=Decimal("3"),
            buy_price=Decimal("2800.00"),
            currency="USD",
            account="default"
        )
    ]
    for pos in positions:
        test_db.add(pos)
    test_db.commit()
    for pos in positions:
        test_db.refresh(pos)
    return positions


class TestUserIsolation:
    """Test that users can only access their own data"""

    def test_get_positions_user1_sees_only_their_positions(
        self, client, user1_token, user1_positions, user2_positions
    ):
        """Test that user1 only sees their own positions"""
        response = client.get(
            "/positions",
            headers={"Authorization": f"Bearer {user1_token}"}
        )

        assert response.status_code == 200
        positions = response.json()
        assert len(positions) == 2

        symbols = [pos["symbol"] for pos in positions]
        assert "AAPL.US" in symbols
        assert "MSFT.US" in symbols
        assert "GOOGL.US" not in symbols  # User2's position not visible

    def test_get_positions_user2_sees_only_their_positions(
        self, client, user2_token, user1_positions, user2_positions
    ):
        """Test that user2 only sees their own positions"""
        response = client.get(
            "/positions",
            headers={"Authorization": f"Bearer {user2_token}"}
        )

        assert response.status_code == 200
        positions = response.json()
        assert len(positions) == 1

        assert positions[0]["symbol"] == "GOOGL.US"

    def test_update_position_user_cannot_update_others_position(
        self, client, user1_token, user2_positions
    ):
        """Test that user1 cannot update user2's position"""
        user2_position_id = user2_positions[0].id

        response = client.patch(
            f"/positions/{user2_position_id}",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"quantity": 100}
        )

        assert response.status_code == 404  # Position not found (for this user)

    def test_delete_position_user_cannot_delete_others_position(
        self, client, user1_token, user2_positions
    ):
        """Test that user1 cannot delete user2's position"""
        user2_position_id = user2_positions[0].id

        response = client.delete(
            f"/positions/{user2_position_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )

        assert response.status_code == 404  # Position not found (for this user)

    def test_get_positions_without_auth_fails(self, client, user1_positions):
        """Test that getting positions without authentication fails"""
        response = client.get("/positions")

        assert response.status_code == 403  # Forbidden - no auth

    def test_user_can_update_own_position(
        self, client, user1_token, user1_positions
    ):
        """Test that user can update their own position"""
        position_id = user1_positions[0].id

        response = client.patch(
            f"/positions/{position_id}",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"quantity": 20}
        )

        assert response.status_code == 200
        updated_position = response.json()
        assert float(updated_position["quantity"]) == 20

    def test_user_can_delete_own_position(
        self, client, user1_token, user1_positions
    ):
        """Test that user can delete their own position"""
        position_id = user1_positions[0].id

        response = client.delete(
            f"/positions/{position_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )

        assert response.status_code == 200

        # Verify position is deleted
        response = client.get(
            "/positions",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        positions = response.json()
        position_ids = [pos["id"] for pos in positions]
        assert str(position_id) not in position_ids

    def test_create_position_associates_with_correct_user(
        self, client, user1_token, test_db, user1
    ):
        """Test that creating a position associates it with the authenticated user"""
        response = client.post(
            "/positions",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={
                "symbol": "TSLA.US",
                "quantity": 5,
                "buy_price": 700.00,
                "currency": "USD",
                "account": "default"
            }
        )

        assert response.status_code == 200
        created_position = response.json()

        # Verify position is associated with user1
        assert created_position["user_id"] == str(user1.id)
        assert created_position["symbol"] == "TSLA.US"

    def test_two_users_can_have_same_symbol(
        self, client, user1_token, user2_token, test_db
    ):
        """Test that two users can independently own the same symbol"""
        # User1 creates TSLA position
        response1 = client.post(
            "/positions",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={
                "symbol": "TSLA.US",
                "quantity": 5,
                "buy_price": 700.00,
                "currency": "USD",
                "account": "default"
            }
        )
        assert response1.status_code == 200

        # User2 creates TSLA position
        response2 = client.post(
            "/positions",
            headers={"Authorization": f"Bearer {user2_token}"},
            json={
                "symbol": "TSLA.US",
                "quantity": 10,
                "buy_price": 650.00,
                "currency": "USD",
                "account": "default"
            }
        )
        assert response2.status_code == 200

        # Verify user1 sees their own quantity
        response1_positions = client.get(
            "/positions",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        user1_tsla = [p for p in response1_positions.json() if p["symbol"] == "TSLA.US"][0]
        assert float(user1_tsla["quantity"]) == 5

        # Verify user2 sees their own quantity
        response2_positions = client.get(
            "/positions",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        user2_tsla = [p for p in response2_positions.json() if p["symbol"] == "TSLA.US"][0]
        assert float(user2_tsla["quantity"]) == 10
