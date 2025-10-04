#!/usr/bin/env python3
"""
Скрипт для установки date_added для существующих позиций.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.position import Position
from sqlalchemy.orm import Session
from datetime import datetime

def update_date_added_for_existing_positions():
    """Устанавливает date_added для существующих позиций"""
    
    db = next(get_db())
    try:
        # Получаем позиции без date_added (NULL значения)
        positions = db.query(Position).filter(
            Position.date_added.is_(None)
        ).all()
        
        print(f"Найдено {len(positions)} позиций без date_added")
        
        updated_count = 0
        for position in positions:
            # Устанавливаем текущую дату как date_added
            position.date_added = datetime.utcnow()
            updated_count += 1
            print(f"Установлен date_added для позиции {position.symbol}")
        
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

if __name__ == "__main__":
    update_date_added_for_existing_positions()
