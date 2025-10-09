#!/usr/bin/env python3
"""
Загрузка цены для символа BIDU
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.price_service import PriceService
from app.marketdata.stooq_client import symbol_to_stooq, fetch_latest_from_stooq

def main():
    db = SessionLocal()
    try:
        # Загружаем цену для BIDU
        symbol = "BIDU"
        print(f"Загружаем цену для {symbol}...")
        
        # Попробуем несколько вариантов символа
        symbols_to_try = ["BIDU", "BIDU.us", "BIDU.US"]
        
        for symbol_variant in symbols_to_try:
            print(f"Пробуем символ: {symbol_variant}")
            try:
                stooq_symbol = symbol_to_stooq(symbol_variant)
                print(f"Stooq формат: {stooq_symbol}")
                
                price_data = fetch_latest_from_stooq(symbol_variant)
                if price_data:
                    print(f"Получены данные: {price_data}")
                    
                    # Сохраняем в базу через PriceService
                    price_service = PriceService(db)
                    success = price_service.load_price_for_symbol(symbol_variant)
                    print(f"Сохранение успешно: {success}")
                    
                    # Получаем сохраненные данные
                    latest_price = price_service.repository.get_latest_price(symbol_variant)
                    if latest_price:
                        print(f"Сохраненная цена: ${latest_price.close:.2f} на {latest_price.date}")
                        break
                    else:
                        print("Данные не сохранились")
                else:
                    print(f"Нет данных для {symbol_variant}")
            except Exception as e:
                print(f"Ошибка для {symbol_variant}: {e}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()








