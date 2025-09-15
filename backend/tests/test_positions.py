import pytest
from decimal import Decimal
from datetime import date
from uuid import UUID

from app.models import Position, User


def test_create_position_model(db_session):
    """Тест создания позиции на уровне модели"""
    # Создаем тестового пользователя
    test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
    db_session.add(test_user)
    db_session.commit()
    
    # Создаем позицию
    position = Position(
        user_id=test_user.id,
        symbol="AAPL",
        quantity=Decimal("10.5"),
        buy_price=Decimal("150.25"),
        buy_date=date(2024, 1, 15),
        currency="USD",
        account="main"
    )
    
    db_session.add(position)
    db_session.commit()
    db_session.refresh(position)
    
    assert position.symbol == "AAPL"
    assert position.quantity == Decimal("10.5")
    assert position.buy_price == Decimal("150.25")
    assert position.buy_date == date(2024, 1, 15)
    assert position.currency == "USD"
    assert position.account == "main"
    assert position.user_id == test_user.id
    assert position.id is not None


def test_position_relationships(db_session):
    """Тест связей между моделями"""
    # Создаем тестового пользователя
    test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
    db_session.add(test_user)
    db_session.commit()
    
    # Создаем позицию
    position = Position(
        user_id=test_user.id,
        symbol="AAPL",
        quantity=Decimal("10"),
        buy_price=Decimal("150"),
        currency="USD"
    )
    
    db_session.add(position)
    db_session.commit()
    db_session.refresh(position)
    
    # Проверяем связь с пользователем
    db_session.refresh(test_user)
    assert len(test_user.positions) == 1
    assert test_user.positions[0].symbol == "AAPL"


def test_position_defaults(db_session):
    """Тест значений по умолчанию"""
    # Создаем тестового пользователя
    test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
    db_session.add(test_user)
    db_session.commit()
    
    position = Position(
        user_id=test_user.id,
        symbol="AAPL",
        quantity=Decimal("10")
    )
    
    db_session.add(position)
    db_session.commit()
    db_session.refresh(position)
    
    assert position.currency == "USD"  # значение по умолчанию
    assert position.buy_price is None
    assert position.buy_date is None
    assert position.account is None


def test_create_position_api(client, db_session):
    """Тест создания позиции через API"""
    # Создаем тестового пользователя
    test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
    db_session.add(test_user)
    db_session.commit()
    
    position_data = {
        "symbol": "AAPL",
        "quantity": "10.5",
        "buy_price": "150.25",
        "buy_date": "2024-01-15",
        "currency": "USD",
        "account": "main"
    }
    
    response = client.post("/positions", json=position_data, params={"user_id": str(test_user.id)})
    
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["quantity"] == "10.50000000"  # Decimal с полной точностью
    assert data["buy_price"] == "150.25000000"
    assert data["buy_date"] == "2024-01-15"
    assert data["currency"] == "USD"
    assert data["account"] == "main"
    assert data["user_id"] == str(test_user.id)


def test_get_positions_api(client, db_session):
    """Тест получения списка позиций через API"""
    # Создаем тестового пользователя
    test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
    db_session.add(test_user)
    db_session.commit()
    
    # Создаем несколько позиций
    positions = [
        {"symbol": "AAPL", "quantity": "10", "buy_price": "150"},
        {"symbol": "GOOGL", "quantity": "5", "buy_price": "2800"},
    ]
    
    for pos in positions:
        response = client.post("/positions", json=pos, params={"user_id": str(test_user.id)})
        assert response.status_code == 200
    
    # Получаем список позиций
    response = client.get("/positions", params={"user_id": str(test_user.id)})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["symbol"] in ["AAPL", "GOOGL"]
    assert data[1]["symbol"] in ["AAPL", "GOOGL"]


def test_symbol_normalization_api(client, db_session):
    """Тест нормализации символа (uppercase, strip) через API"""
    # Создаем тестового пользователя
    test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
    db_session.add(test_user)
    db_session.commit()
    
    position_data = {
        "symbol": "  aapl  ",  # с пробелами и lowercase
        "quantity": "10",
        "buy_price": "150"
    }
    
    response = client.post("/positions", json=position_data, params={"user_id": str(test_user.id)})
    
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"  # должно быть uppercase и без пробелов


def test_validation_errors_api(client, db_session):
    """Тест валидации данных через API"""
    # Создаем тестового пользователя
    test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
    db_session.add(test_user)
    db_session.commit()
    
    # Отрицательное количество
    response = client.post("/positions", json={
        "symbol": "AAPL",
        "quantity": "-10",
        "buy_price": "150"
    }, params={"user_id": str(test_user.id)})
    assert response.status_code == 422
    
    # Пустой символ
    response = client.post("/positions", json={
        "symbol": "",
        "quantity": "10",
        "buy_price": "150"
    }, params={"user_id": str(test_user.id)})
    assert response.status_code == 422
    
    # Отрицательная цена покупки
    response = client.post("/positions", json={
        "symbol": "AAPL",
        "quantity": "10",
        "buy_price": "-150"
    }, params={"user_id": str(test_user.id)})
    assert response.status_code == 422
