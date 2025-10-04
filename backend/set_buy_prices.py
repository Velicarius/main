#!/usr/bin/env python3
"""
Скрипт для установки buy_price для позиций без него.
Использует текущую цену как buy_price для позиций без него.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.position import Position
from app.services.price_eod import PriceEODRepository
from sqlalchemy.orm import Session

def set_buy_prices_for_user(user_id: str):
    """Устанавливает buy_price для позиций пользователя без него"""
    
    db = next(get_db())
    try:
        price_repo = PriceEODRepository(db)
        
        # Получаем позиции пользователя без buy_price
        positions = db.query(Position).filter(
            Position.user_id == user_id,
            Position.buy_price.is_(None)
        ).all()
        
        print(f"Найдено {len(positions)} позиций без buy_price для пользователя {user_id}")
        
        updated_count = 0
        for position in positions:
            # Получаем текущую цену
            latest_price = price_repo.get_latest_price(position.symbol)
            
            if latest_price:
                # Устанавливаем текущую цену как buy_price
                position.buy_price = latest_price.close
                updated_count += 1
                print(f"Установлен buy_price {latest_price.close} для {position.symbol}")
            else:
                print(f"Не найдена цена для {position.symbol}")
        
        if updated_count > 0:
            db.commit()
            print(f"Обновлено {updated_count} позиций")
        else:
            print("Нет позиций для обновления")
            
    except Exception as e:
        db.rollback()
        print(f"Ошибка: {e}")
    finally:
        db.close()

def set_buy_prices_for_all_users():
    """Устанавливает buy_price для всех пользователей"""
    
    db = next(get_db())
    try:
        # Получаем всех пользователей с позициями без buy_price
        from app.models.user import User
        users = db.query(User).join(Position).filter(
            Position.buy_price.is_(None)
        ).distinct().all()
        
        print(f"Найдено {len(users)} пользователей с позициями без buy_price")
        
        for user in users:
            print(f"\nОбрабатываем пользователя {user.email} ({user.id})")
            set_buy_prices_for_user(str(user.id))
            
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
        set_buy_prices_for_user(user_id)
    else:
        set_buy_prices_for_all_users()
