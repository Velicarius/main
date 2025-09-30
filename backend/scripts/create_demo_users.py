#!/usr/bin/env python3
"""
Скрипт для создания 20 демо-пользователей с рандомными портфелями
"""

import asyncio
import random
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.position import Position
from app.models.price_eod import PriceEOD
from sqlalchemy import select
import uuid

# Список популярных акций для демо-портфелей
DEMO_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", 
    "AMD", "INTC", "CRM", "ADBE", "PYPL", "UBER", "SPOT", "SQ", 
    "ZM", "DOCU", "SNOW", "PLTR", "RBLX", "COIN", "HOOD", "SOFI"
]

# Список имен для демо-пользователей
DEMO_NAMES = [
    "Alex Johnson", "Sarah Chen", "Michael Rodriguez", "Emily Davis", "David Kim",
    "Jessica Wang", "Christopher Brown", "Amanda Taylor", "Matthew Wilson", "Ashley Martinez",
    "Daniel Anderson", "Samantha Garcia", "Andrew Thompson", "Nicole White", "Ryan Jackson",
    "Stephanie Harris", "Kevin Martin", "Rachel Lee", "Brandon Clark", "Lauren Lewis"
]

def generate_random_portfolio(user_id: str, db: Session):
    """Генерирует рандомный портфель для пользователя"""
    
    # Количество позиций (от 3 до 8)
    num_positions = random.randint(3, 8)
    
    # Выбираем случайные символы
    selected_symbols = random.sample(DEMO_SYMBOLS, num_positions)
    
    # USD депозит (от $1,000 до $50,000)
    usd_deposit = Decimal(str(random.uniform(1000, 50000)))
    
    # Создаем USD позицию
    usd_position = Position(
        id=str(uuid.uuid4()),
        user_id=user_id,
        symbol="USD",
        quantity=usd_deposit,
        buy_price=Decimal("1.0"),
        buy_date=date.today() - timedelta(days=random.randint(1, 365)),
        currency="USD",
        account="main"
    )
    db.add(usd_position)
    
    # Создаем позиции по акциям
    for symbol in selected_symbols:
        # Количество акций (от 10 до 1000)
        quantity = Decimal(str(random.uniform(10, 1000)))
        
        # Цена покупки (от $20 до $500)
        buy_price = Decimal(str(random.uniform(20, 500)))
        
        # Дата покупки (от 1 дня до 2 лет назад)
        buy_date = date.today() - timedelta(days=random.randint(1, 730))
        
        position = Position(
            id=str(uuid.uuid4()),
            user_id=user_id,
            symbol=symbol,
            quantity=quantity,
            buy_price=buy_price,
            buy_date=buy_date,
            currency="USD",
            account="main"
        )
        db.add(position)

def create_demo_users():
    """Создает 20 демо-пользователей с портфелями"""
    
    db = SessionLocal()
    
    try:
        # Проверяем, есть ли уже демо-пользователи
        existing_demo_users = db.execute(
            select(User).where(User.email.like("%@demo.com"))
        ).scalars().all()
        
        if existing_demo_users:
            print(f"Found {len(existing_demo_users)} existing demo users. Deleting...")
            for user in existing_demo_users:
                db.delete(user)
            db.commit()
        
        print("Creating 20 demo users...")
        
        for i in range(20):
            # Создаем пользователя
            user_id = str(uuid.uuid4())
            email = f"demo{i+1}@demo.com"
            name = DEMO_NAMES[i]
            
            user = User(
                id=user_id,
                email=email,
                name=name
            )
            db.add(user)
            
            # Генерируем портфель
            generate_random_portfolio(user_id, db)
            
            print(f"Created user {i+1}/20: {name} ({email})")
        
        db.commit()
        print("✅ Successfully created 20 demo users with random portfolios!")
        
    except Exception as e:
        print(f"❌ Error creating demo users: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_demo_users()
