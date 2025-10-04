#!/usr/bin/env python3
"""
Тест логики PnL напрямую через базу данных
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.position import Position
from app.services.price_eod import PriceEODRepository
from sqlalchemy.orm import Session
from uuid import UUID

def test_pnl_logic():
    """Тестирует логику PnL для пользователя 117.tomcat@gmail.com"""
    
    db = next(get_db())
    try:
        price_repo = PriceEODRepository(db)
        
        # Получаем позиции пользователя 117.tomcat@gmail.com
        user_id = UUID("41e10fbf-bad3-4227-9a34-dfc15ba6d6e8")
        positions = db.query(Position).filter(Position.user_id == user_id).all()
        
        print(f"Найдено {len(positions)} позиций для пользователя 117.tomcat@gmail.com")
        
        for pos in positions:
            print(f"\nПозиция: {pos.symbol}")
            print(f"  Количество: {pos.quantity}")
            print(f"  Buy price: {pos.buy_price}")
            print(f"  Date added: {pos.date_added}")
            
            # Получаем текущую цену
            latest_price = price_repo.get_latest_price(pos.symbol)
            if latest_price:
                print(f"  Текущая цена: {latest_price.close} (дата: {latest_price.date})")
                
                # Определяем точку отсчета для PnL
                if pos.buy_price:
                    reference_price = float(pos.buy_price)
                    reference_type = "buy_price"
                else:
                    # Получаем цену на дату добавления
                    added_date = pos.date_added.date()
                    price_on_added_date = price_repo.get_price_on_date(pos.symbol, added_date)
                    if price_on_added_date:
                        reference_price = float(price_on_added_date.close)
                        reference_type = f"price_on_{added_date}"
                    else:
                        reference_price = None
                        reference_type = "no_reference"
                
                print(f"  Точка отсчета: {reference_price} ({reference_type})")
                
                if reference_price:
                    current_price = float(latest_price.close)
                    quantity = float(pos.quantity)
                    
                    pnl = (current_price - reference_price) * quantity
                    pnl_pct = (pnl / (reference_price * quantity)) * 100
                    
                    print(f"  PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
                else:
                    print(f"  PnL: Нельзя рассчитать (нет точки отсчета)")
            else:
                print(f"  Текущая цена: Не найдена")
                
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_pnl_logic()
