#!/usr/bin/env python3
"""
Тест автоматической загрузки цен.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.price_service import load_price_for_symbol

def test_auto_price_loading():
    """Тестирует автоматическую загрузку цен для символов"""
    
    # Символы для тестирования
    test_symbols = ["AAPL", "MSFT", "GOOGL"]
    
    print("=== Тест автоматической загрузки цен ===")
    
    # Создаем сессию БД
    db = SessionLocal()
    
    try:
        for symbol in test_symbols:
            print(f"\nТестируем символ: {symbol}")
            
            # Пытаемся загрузить цену
            success = load_price_for_symbol(symbol, db)
            
            if success:
                print(f"✅ {symbol}: Цена успешно загружена")
            else:
                print(f"❌ {symbol}: Не удалось загрузить цену")
        
        print("\n=== Результаты теста ===")
        print("Проверьте логи для подробной информации о загрузке.")
        
    except Exception as e:
        print(f"❌ Ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_auto_price_loading()
