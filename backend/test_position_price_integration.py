#!/usr/bin/env python3
"""
Интеграционный тест автозагрузки цен при добавлении позиций.
Этот скрипт можно запустить напрямую для проверки работы системы.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Position, User, PriceEOD
from app.services.price_service import PriceService
from uuid import UUID
from decimal import Decimal
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_real_position_creation_with_auto_price_loading():
    """Интеграционный тест: создание позиции и проверка автозагрузки цен"""
    
    print("=== Интеграционный тест автозагрузки цен ===\n")
    
    # Создаем сессию БД
    db = SessionLocal()
    
    try:
        # Создаем тестового пользователя
        test_user_id = UUID("00000000-0000-0000-0000-000000000001")
        
        # Проверяем, есть ли уже пользователь
        existing_user = db.query(User).filter(User.id == test_user_id).first()
        if not existing_user:
            existing_user = User(id=test_user_id, email="test_autoprice@example.com")
            db.add(existing_user)
            db.commit()
            print(f"✅ Создан тестовый пользователь: {existing_user.email}")
        else:
            print(f"✅ Используем существующего пользователя: {existing_user.email}")
        
        # Тестовые символы для проверки
        test_symbols = [
            {"symbol": "AAPL", "quantity": Decimal("10"), "buy_price": Decimal("175.50")},
            {"symbol": "TSLA", "quantity": Decimal("5"), "buy_price": Decimal("220.00")},
            {"symbol": "NVDA", "quantity": Decimal("2"), "buy_price": Decimal("425.75")},
        ]
        
        service = PriceService(db)
        
        print("\n--- Этап 1: Проверка существующих цен ---")
        existing_symbols = []
        for symbol_data in test_symbols:
            symbol = symbol_data["symbol"]
            
            # Проверяем, есть ли уже данные о ценах
            existing_price = service.repository.get_latest_price(symbol)
            
            if existing_price:
                print(f"📊 {symbol}: цена уже есть в БД (дата: {existing_price.get('date')})")
                existing_symbols.append(symbol)
            else:
                print(f"❓ {symbol}: данных о ценах нет в БД")
        
        print(f"\nСимволов с существующими ценами: {len(existing_symbols)}/{len(test_symbols)}")
        
        # Удаляем существующие тестовые позиции
        print("\n--- Этап 2: Очистка тестовых данных ---")
        deleted_positions = db.query(Position).filter(
            Position.user_id == test_user_id,
            Position.symbol.in_([s["symbol"] for s in test_symbols])
        ).delete(synchronize_session=False)
        
        deleted_prices = db.query(PriceEOD).filter(
            PriceEOD.symbol.in_([s["symbol"] for s in test_symbols])
        ).delete(synchronize_session=False)
        
        db.commit()
        print(f"🗑️  Удалено тестовых позиций: {deleted_positions}")
        print(f"🗑️  Удалено тестовых цен: {deleted_prices}")
        
        print("\n--- Этап 3: Создание позиций с автозагрузкой цен ---")
        
        loaded_symbols = []
        failed_symbols = []
        
        for symbol_data in test_symbols:
            symbol = symbol_data["symbol"]
            quantity = symbol_data["quantity"]
            buy_price = symbol_data["buy_price"]
            
            print(f"\n📝 Создаем позицию: {symbol}")
            
            # Создаем позицию
            position = Position(
                user_id=test_user_id,
                symbol=symbol,
                quantity=quantity,
                buy_price=buy_price,
                currency="USD"
            )
            
            db.add(position)
            db.commit()
            db.refresh(position)
            
            print(f"✅ Позиция создана: ID={position.id}, символ={symbol}")
            
            # Запускаем автозагрузку цены (как это делает API)
            try:
                load_success = service.load_price_for_symbol(symbol)
                
                if load_success:
                    print(f"💰 Цена загружена для {symbol}")
                    loaded_symbols.append(symbol)
                else:
                    print(f"⚠️  Цена не была загружена для {symbol}")
                    failed_symbols.append(symbol)
                    
            except Exception as e:
                print(f"❌ Ошибка загрузки цены для {symbol}: {e}")
                failed_symbols.append(symbol)
        
        print(f"\n--- Этап 4: Проверка результатов ---")
        
        print(f"✅ Успешно загружено цен: {len(loaded_symbols)}")
        print(f"❌ Не удалось загрузить цен: {len(failed_symbols)}")
        
        if loaded_symbols:
            print(f"\nЗагруженные символы: {', '.join(loaded_symbols)}")
            
            # Проверяем, что цены действительно сохранены
            for symbol in loaded_symbols:
                price = service.repository.get_latest_price(symbol)
                if price:
                    print(f"📊 {symbol}: {price.get('close')} USD (дата: {price.get('date')})")
                else:
                    print(f"⚠️  {symbol}: данные не найдены в БД после загрузки")
        
        if failed_symbols:
            print(f"\nСимволы с ошибками: {', '.join(failed_symbols)}")
            print("💡 Возможные причины:")
            print("  - Проблемы с сетью")
            print("  - Нераспознанный символ")
            print("  - Временная недоступность Stooq API")
        
        return len(loaded_symbols) > 0  # Тест считается успешным если хотя бы одна цена загрузилась
        
    except Exception as e:
        print(f"❌ Критическая ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


def test_bulk_position_creation():
    """Тест массового создания позиций"""
    
    print("\n\n=== Тест массового создания позиций ===\n")
    
    db = SessionLocal()
    
    try:
        test_user_id = UUID("00000000-0000-0000-0000-000000000001")
        
        # Тестовые символы для массового теста
        symbols_to_test = ["MSFT", "GOOGL"]
        
        print("🗑️  Очистка данных...")
        db.query(Position).filter(
            Position.user_id == test_user_id,
            Position.symbol.in_(symbols_to_test)
        ).delete(synchronize_session=False)
        
        db.commit()
        
        print(f"📝 Создаем позиции для символов: {', '.join(symbols_to_test)}")
        
        positions = []
        for symbol in symbols_to_test:
            position = Position(
                user_id=test_user_id,
                symbol=symbol,
                quantity=Decimal("1"),
                buy_price=Decimal("100"),
                currency="USD"
            )
            positions.append(position)
        
        db.add_all(positions)
        db.commit()
        
        print(f"✅ Создано позиций: {len(positions)}")
        
        # Тестируем массовую автозагрузку
        service = PriceService(db)
        results = service.load_prices_for_symbols(symbols_to_test)
        
        print("\n📊 Результаты автозагрузки:")
        success_count = 0
        for symbol, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {symbol}: {'загружено' if success else 'ошибка'}")
            if success:
                success_count += 1
        
        print(f"\nИтого успешно: {success_count}/{len(symbols_to_test)}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Ошибка в тесте массового создания: {e}")
        return False
    
    finally:
        db.close()


def main():
    """Главная функция для запуска всех тестов"""
    
    print("=== Запуск комплексного тестирования автозагрузки цен ===\n")
    
    # Проверяем доступность Stooq API
    try:
        from app.marketdata.stooq_client import fetch_latest_from_stooq
        test_price = fetch_latest_from_stooq("AAPL")
        if test_price:
            print("Stooq API доступен")
        else:
            print("Stooq API не отвечает")
    except Exception as e:
        print(f"❌ Ошибка проверки Stooq API: {e}")
        return
    
    # Запускаем основные тесты
    results = []
    
    # Тест создания позиций
    results.append(test_real_position_creation_with_auto_price_loading())
    
    # Тест массового создания
    results.append(test_bulk_position_creation())
    
    # Итоги
    successful_tests = sum(results)
    total_tests = len(results)
    
    print(f"\n=== ИТОГИ ТЕСТИРОВАНИЯ ===")
    print(f"Успешных тестов: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("🎉 Все тесты прошли успешно! Автозагрузка цен работает корректно.")
    elif successful_tests > 0:
        print("⚠️  Частичный успех. Некоторые функции работают.")
    else:
        print("❌ Все тесты провалились. Требуется проверка настройки системы.")
    
    return successful_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
