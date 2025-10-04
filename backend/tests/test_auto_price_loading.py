"""
Тесты автоматической загрузки цен при добавлении позиций.
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import UUID
from unittest.mock import patch, MagicMock

from app.models import Position, User, PriceEOD
from app.services.price_service import PriceService


class TestAutoPriceLoading:
    """Тесты автоматической загрузки цен"""

    def test_create_position_triggers_price_loading(self, client, db_session):
        """Тест: создание позиции запускает автозагрузку цены"""
        # Создаем тестового пользователя
        test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
        db_session.add(test_user)
        db_session.commit()

        user_id_param = {"user_id": str(test_user.id)}
        
        # Мокаем автозагрузку цен
        with patch('app.routers.positions.load_price_for_symbol') as mock_load_price:
            mock_load_price.return_value = True
            
            position_data = {
                "symbol": "TSLM",  # Используем новый символ
                "quantity": "10",
                "buy_price": "25.50",
                "currency": "USD"
            }
            
            response = client.post("/positions", json=position_data, params=user_id_param)
            
            # Проверяем, что позиция создана успешно
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "TSLM"
            
            # Проверяем, что автозагрузка вызвана
            mock_load_price.assert_called_once()
            
            # Получаем переданный символ
            call_args = mock_load_price.call_args
            symbol_arg = call_args[0][0]  # Первый позиционный аргумент
            assert symbol_arg == "TSLM"

    def test_bulk_create_positions_triggers_price_loading(self, client, db_session):
        """Тест: массовое создание позиций запускает автозагрузку цен"""
        # Создаем тестового пользователя
        test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
        db_session.add(test_user)
        db_session.commit()

        user_id_param = {"user_id": str(test_user.id)}
        
        # Мокаем автозагрузку цен
        with patch('app.routers.positions.load_prices_for_symbols') as mock_load_prices:
            mock_load_prices.return_value = {"TSLM": True, "NVDA": True}
            
            positions_data = [
                {
                    "symbol": "TSLM",
                    "quantity": "10",
                    "buy_price": "25.50"
                },
                {
                    "symbol": "NVDA",
                    "quantity": "5",
                    "buy_price": "450.00"
                }
            ]
            
            response = client.post("/positions/bulk_json", json=positions_data, params=user_id_param)
            
            # Проверяем, что позиции созданы успешно
            assert response.status_code == 200
            data = response.json()
            assert data["inserted"] == 2
            assert data["failed"] == 0
            
            # Проверяем, что автозагрузка вызвана
            mock_load_prices.assert_called_once()
            
            # Получаем переданные символы
            call_args = mock_load_prices.call_args
            symbols_arg = call_args[0][0]  # Первый позиционный аргумент
            assert "TSLM" in symbols_arg
            assert "NVDA" in symbols_arg

    def test_price_service_normal_symbol_loading(self, db_session):
        """Тест: загрузка цены для обычного символа через PriceService"""
        # Мокаем обращение к Stooq API
        mock_price_data = {
            'date': date.today(),
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000000,
            'source': 'stooq'
        }
        
        with patch('app.services.price_service.fetch_latest_from_stooq', return_value=mock_price_data):
            with patch.object(PriceEOD, '__table__', create=True):  # Мокаем модель для избежания ошибок базы
                service = PriceService(db_session)
                
                # Мокаем репозиторий
                mock_repo = MagicMock()
                mock_repo.get_latest_price.return_value = None  # Цены еще нет
                mock_repo.upsert_prices.return_value = 1       # Успешная вставка
                service.repository = mock_repo
                
                result = service.load_price_for_symbol("AAPL")
                
                # Проверяем результат
                assert result is True
                
                # Проверяем, что репозиторий вызван правильно
                mock_repo.get_latest_price.assert_called_once_with("AAPL")
                mock_repo.upsert_prices.assert_called_once()
                
                # Проверяем переданные данные
                upsert_call = mock_repo.upsert_prices.call_args
                symbol_arg, price_data_arg = upsert_call[0]
                
                assert symbol_arg == "AAPL"
                assert len(price_data_arg) == 1
                assert price_data_arg[0] == mock_price_data

    def test_price_service_skip_existing_price(self, db_session):
        """Тест: пропускается загрузка если цена уже существует"""
        with patch.object(PriceEOD, '__table__', create=True):
            service = PriceService(db_session)
            
            # Мокаем репозиторий - цена уже есть
            mock_repo = MagicMock()
            mock_repo.get_latest_price.return_value = {
                'date': date.today(),
                'close': 102.0
            }
            service.repository = mock_repo
            
            # Не должен вызывать fetch_latest_from_stooq
            with patch('app.services.price_service.fetch_latest_from_stooq') as mock_fetch:
                result = service.load_price_for_symbol("AAPL")
                
                assert result is False
                mock_fetch.assert_not_called()
                mock_repo.get_latest_price.assert_called_once_with("AAPL")

    def test_price_service_error_handling(self, db_session):
        """Тест: обработка ошибок при загрузке цен"""
        with patch.object(PriceEOD, '__table__', create=True):
            service = PriceService(db_session)
            
            # Мокаем репозиторий
            mock_repo = MagicMock()
            mock_repo.get_latest_price.return_value = None
            service.repository = mock_repo
            
            # Мокаем Stooq API - возвращает None (нет данных)
            with patch('app.services.price_service.fetch_latest_from_stooq', return_value=None):
                result = service.load_price_for_symbol("INVALID")
                
                assert result is False
                mock_repo.upsert_prices.assert_not_called()

    def test_symbol_normalization_in_price_loading(self, db_session):
        """Тест: нормализация символов при автозагрузке"""
        # Тестируем символы разного формата
        test_cases = [
            ("aapl", "AAPL"),      # lowercase
            ("  AAPL  ", "AAPL"),  # с пробелами
            ("AAPL", "AAPL"),      # уже нормализованный
        ]
        
        # Создаем тестового пользователя
        test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
        db_session.add(test_user)
        db_session.commit()

        user_id_param = {"user_id": str(test_user.id)}

        for input_symbol, expected_symbol in test_cases:
            with patch('app.routers.positions.load_price_for_symbol') as mock_load_price:
                mock_load_price.return_value = True
                
                position_data = {
                    "symbol": input_symbol,
                    "quantity": "10",
                    "buy_price": "150.00"
                }
                
                response = client.post("/positions", json=position_data, params=user_id_param)
                
                assert response.status_code == 200
                
                # Проверяем, что автозагрузка вызвана с нормализованным символом
                mock_load_price.assert_called_once_with(expected_symbol, db_session)

    def test_usd_symbol_skipped_in_bulk_loading(self, client, db_session):
        """Тест: USD символ пропускается при массовой загрузке"""
        # Создаем тестового пользователя
        test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
        db_session.add(test_user)
        db_session.commit()

        user_id_param = {"user_id": str(test_user.id)}
        
        with patch('app.routers.positions.load_prices_for_symbols') as mock_load_prices:
            mock_load_prices.return_value = {"AAPL": True}
            
            positions_data = [
                {
                    "symbol": "AAPL",
                    "quantity": "10",
                    "buy_price": "150.00"
                },
                {
                    "symbol": "USD",  # USD должен быть пропущен
                    "quantity": "1000",
                    "buy_price": "1.00"
                }
            ]
            
            response = client.post("/positions/bulk_json", json=positions_data, params=user_id_param)
            
            assert response.status_code == 200
            
            # Проверяем, что автозагрузка вызвана только для AAPL
            mock_load_prices.assert_called_once()
            call_args = mock_load_prices.call_args
            symbols_arg = call_args[0][0]
            assert "AAPL" in symbols_arg
            assert "USD" not in symbols_arg

    def test_price_loading_failure_does_not_prevent_position_creation(self, client, db_session):
        """Тест: неудача загрузки цены не блокирует создание позиции"""
        # Создаем тестового пользователя
        test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
        db_session.add(test_user)
        db_session.commit()

        user_id_param = {"user_id": str(test_user.id)}
        
        # Мокаем автозагрузку - возвращает False (неудача)
        with patch('app.routers.positions.load_price_for_symbol', return_value=False):
            position_data = {
                "symbol": "UNKNOWN",
                "quantity": "10",
                "buy_price": "25.50"
            }
            
            response = client.post("/positions", json=position_data, params=user_id_param)
            
            # Позиция должна быть создана несмотря на неудачу загрузки цены
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "UNKNOWN"

    def test_position_update_without_symbols_does_not_trigger_loading(self, client, db_session):
        """Тест: обновление позиции без изменения символа не запускает загрузку"""
        # Создаем тестового пользователя и позицию
        test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
        db_session.add(test_user)
        
        position = Position(
            user_id=test_user.id,
            symbol="AAPL",
            quantity=Decimal("10"),
            buy_price=Decimal("150"),
            currency="USD"
        )
        db_session.add(position)
        db_session.commit()

        user_id_param = {"user_id": str(test_user.id)}
        
        with patch('app.routers.positions.load_price_for_symbol') as mock_load_price:
            update_data = {
                "quantity": "15",  # Меняем только количество
                "buy_price": "155"
            }
            
            response = client.patch(f"/positions/{position.id}", json=update_data, params=user_id_param)
            
            # Обновление должно быть успешным
            assert response.status_code == 200
            
            # Автозагрузка НЕ должна вызываться (символ не изменился)
            mock_load_price.assert_not_called()


class TestLegacyPositionEndpoint:
    """Тесты legacy эндпоинта для совместимости"""

    def test_legacy_position_endpoint_triggers_price_loading(self, client, db_session):
        """Тест: legacy эндпоинт также запускает автозагрузку"""
        # Создаем тестового пользователя
        test_user = User(id=UUID("00000000-0000-0000-0000-000000000001"), email="test@example.com")
        db_session.add(test_user)
        db_session.commit()

        # Симулируем сессию (legacy эндпоинт использует сессию)
        with client.session_transaction() as session:
            session["user_id"] = str(test_user.id)

        with patch('app.routers.positions.load_price_for_symbol') as mock_load_price:
            mock_load_price.return_value = True
            
            response = client.post("/positions/add", params={
                "symbol": "GOOGL",
                "quantity": "5",
                "price": "2800"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "GOOGL"
            
            # Проверяем, что автозагрузка вызвана
            mock_load_price.assert_called_once_with("GOOGL", db_session)








