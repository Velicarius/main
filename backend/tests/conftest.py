import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models import Base

# Тестовая база данных
TEST_DB_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def engine():
    """Создать тестовый движок базы данных"""
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="function")
def db_session(engine):
    """Создать тестовую сессию базы данных"""
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    yield session
    
    # Очищаем после теста
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Создать тестовый клиент FastAPI"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Переопределяем зависимость БД
    app.dependency_overrides[get_db] = override_get_db
    
    # Устанавливаем тестовый режим для отключения Celery/Redis
    app.state.TEST_MODE = True
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Очищаем переопределения
    app.dependency_overrides.clear()
    app.state.TEST_MODE = False
