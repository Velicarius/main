from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.position import Position
from app.security import hash_password, verify_password
from sqlalchemy import select, insert, update, func, and_
from uuid import uuid4
from pydantic import BaseModel
from decimal import Decimal
from typing import List
from app.schemas import CashLedgerMetric

router = APIRouter(prefix="/users", tags=["users"])

# Pydantic models for JSON requests
class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UserRanking(BaseModel):
    user_id: str
    name: str
    email: str
    total_value: float
    total_invested: float
    pnl_abs: float
    pnl_percentage: float
    rank: int

@router.post("/register")
def register(request: Request, db: Session = Depends(get_db), email: str = "", name: str = ""):
    """Legacy query parameter endpoint for backward compatibility"""
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        return {"error": "User already exists"}
    uid = uuid4()
    db.execute(insert(User).values(id=uid, email=email, name=name))
    db.commit()
    request.session["user_id"] = str(uid)
    return {"user_id": str(uid), "email": email, "name": name}

@router.post("/register-json", response_model=dict)
def register_json(register_data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """JSON endpoint for user registration with password"""
    # Validation
    if not register_data.email.strip():
        raise HTTPException(status_code=400, detail="Email is required")
    if len(register_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    existing = db.execute(select(User).where(User.email == register_data.email)).scalar_one_or_none()
    
    if existing:
        # Migration case: user exists but no password_hash
        if existing.password_hash is None:
            hashed_password = hash_password(register_data.password)
            db.execute(
                update(User)
                .where(User.id == existing.id)
                .values(password_hash=hashed_password, name=register_data.name)
            )
            db.commit()
            request.session["user_id"] = str(existing.id)
            return {"user_id": str(existing.id), "email": existing.email, "name": register_data.name}
        else:
            # User exists with password
            raise HTTPException(status_code=409, detail="User exists")
    else:
        # Create new user
        uid = uuid4()
        hashed_password = hash_password(register_data.password)
        db.execute(
            insert(User).values(
                id=uid, 
                email=register_data.email, 
                name=register_data.name,
                password_hash=hashed_password
            )
        )
        db.commit()
        request.session["user_id"] = str(uid)
        return {"user_id": str(uid), "email": register_data.email, "name": register_data.name}

@router.post("/login")
def login(request: Request, db: Session = Depends(get_db), email: str = ""):
    """Legacy query parameter endpoint for backward compatibility"""
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        return {"error": "User not found"}
    request.session["user_id"] = str(user.id)
    return {"user_id": str(user.id), "email": user.email, "name": user.name}

@router.post("/login-json", response_model=dict)
def login_json(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """JSON endpoint for user login with password"""
    user = db.execute(select(User).where(User.email == login_data.email)).scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    request.session["user_id"] = str(user.id)
    return {"user_id": str(user.id), "email": user.email, "name": user.name}

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}

@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    uid = request.session.get("user_id")
    if not uid:
        return {"authenticated": False}
    user = db.get(User, uid)
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user_id": str(user.id),
        "email": user.email,
        "name": user.name,
    }

@router.get("/ranking", response_model=List[UserRanking])
def get_user_ranking(db: Session = Depends(get_db)):
    """Получить рейтинг пользователей по PnL (%)"""
    
    # Получаем всех пользователей с их позициями
    users_with_positions = db.execute(
        select(User, Position)
        .join(Position, User.id == Position.user_id)
        .where(Position.symbol != "USD")  # Исключаем USD из расчета
    ).all()
    
    # Группируем по пользователям
    user_portfolios = {}
    for user, position in users_with_positions:
        if user.id not in user_portfolios:
            user_portfolios[user.id] = {
                "user": user,
                "positions": []
            }
        user_portfolios[user.id]["positions"].append(position)
    
    # Рассчитываем метрики для каждого пользователя
    rankings = []
    for user_id, portfolio in user_portfolios.items():
        user = portfolio["user"]
        positions = portfolio["positions"]
        
        # Рассчитываем общую стоимость и инвестиции
        total_invested = sum(float(pos.quantity * (pos.buy_price or 0)) for pos in positions)
        total_value = sum(float(pos.quantity * (pos.buy_price or 0)) for pos in positions)  # Используем buy_price как текущую цену для демо
        
        # Добавляем случайный PnL для демо (от -30% до +50%)
        import random
        pnl_percentage = random.uniform(-30, 50)
        pnl_abs = total_invested * (pnl_percentage / 100)
        total_value = total_invested + pnl_abs
        
        rankings.append(UserRanking(
            user_id=str(user.id),
            name=user.name or "Unknown User",
            email=user.email or "unknown@example.com",
            total_value=total_value,
            total_invested=total_invested,
            pnl_abs=pnl_abs,
            pnl_percentage=pnl_percentage,
            rank=0  # Будет установлен после сортировки
        ))
    
    # Сортируем по PnL % (по убыванию)
    rankings.sort(key=lambda x: x.pnl_percentage, reverse=True)
    
    # Устанавливаем ранги
    for i, ranking in enumerate(rankings):
        ranking.rank = i + 1
    
    return rankings


@router.get("/balance")
def get_balance(request: Request, db: Session = Depends(get_db)):
    """Получить текущий USD баланс пользователя"""
    # Временная заглушка - всегда используем первого пользователя для тестирования
    first_user = db.execute(select(User).limit(1)).scalar_one_or_none()
    if not first_user:
        raise HTTPException(status_code=404, detail="No users found")
    
    balance = float(first_user.usd_balance or 0)
    print(f"DEBUG: User {first_user.email} balance: {balance}")  # Debug log
    
    return {"usd_balance": balance}


@router.put("/balance", response_model=dict)
def update_balance(
    balance_data: dict,
    request: Request, 
    db: Session = Depends(get_db)
):
    """Обновить USD баланс пользователя и соответствующую USD позицию"""
    uid = request.session.get("user_id")
    if not uid:
        # Временная заглушка - используем первого пользователя для тестирования
        first_user = db.execute(select(User).limit(1)).scalar_one_or_none()
        if not first_user:
            raise HTTPException(status_code=404, detail="No users found")
        user = first_user
    else:
        user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    new_balance = balance_data.get("usd_balance", 0)
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Balance cannot be negative")
    
    old_balance = user.usd_balance or Decimal("0")
    user.usd_balance = Decimal(str(new_balance))
    
    # Обновляем или создаем USD позицию в таблице positions
    usd_position = db.execute(
        select(Position).where(
            and_(
                Position.user_id == user.id,
                Position.symbol == "USD"
            )
        )
    ).scalar_one_or_none()
    
    if usd_position:
        # Обновляем существующую USD позицию
        usd_position.quantity = Decimal(str(new_balance))
    else:
        # Создаем новую USD позицию
        usd_position = Position(
            user_id=user.id,
            symbol="USD",
            quantity=Decimal(str(new_balance)),
            buy_price=Decimal("1.0"),
            currency="USD",
            account="cash_account"
        )
        db.add(usd_position)
    
    db.commit()
    
    return {"usd_balance": float(user.usd_balance)}


@router.get("/profile", response_model=dict)
def get_user_profile(request: Request, db: Session = Depends(get_db)):
    """Получить профиль пользователя с балансом и позициями"""
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем позиции пользователя
    positions = db.execute(
        select(Position).where(Position.user_id == uid)
    ).scalars().all()
    
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "usd_balance": float(user.usd_balance or 0),
        "positions": [
            {
                "id": str(pos.id),
                "symbol": pos.symbol,
                "quantity": float(pos.quantity),
                "buy_price": float(pos.buy_price) if pos.buy_price else None,
                "buy_date": pos.buy_date.isoformat() if pos.buy_date else None,
                "currency": pos.currency,
                "account": pos.account
            }
            for pos in positions
        ]
    }


@router.get("/cash-ledger", response_model=CashLedgerMetric)
def get_cash_ledger(request: Request, db: Session = Depends(get_db)):
    """Получить метрики денежной кассы: Free USD, Portfolio Balance, Total Equity"""
    uid = request.session.get("user_id")
    if not uid:
        # Временная заглушка - всегда используем первого пользователя для тестирования
        first_user = db.execute(select(User).limit(1)).scalar_one_or_none()
        if not first_user:
            raise HTTPException(status_code=404, detail="No users found")
        user = first_user
    else:
        user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем все позиции пользователя (без USD)
    positions = db.execute(
        select(Position).where(
            Position.user_id == user.id,
            Position.symbol != "USD"
        )
    ).scalars().all()
    
    # Рассчитываем Portfolio Balance (рыночная стоимость позиций)
    portfolio_balance = Decimal("0")
    
    # Импортируем PriceEODRepository для получения актуальных цен
    from app.services.price_eod import PriceEODRepository
    price_repo = PriceEODRepository(db)
    
    for position in positions:
        # Получаем текущую цену (используем аналогичную логику как в позициях)
        latest_price = None
        symbols_to_try = [
            position.symbol,
            position.symbol.upper(),
            position.symbol.lower(),
            position.symbol.replace('.US', '.us'),
            position.symbol.replace('.us', '.US'),
            position.symbol.replace('.US', ''),
            position.symbol.replace('.us', '')
        ]
        
        for symbol_variant in symbols_to_try:
            latest_price = price_repo.get_latest_price(symbol_variant)
            if latest_price:
                break
        
        # Рассчитываем стоимость позиции
        if latest_price:
            current_price = Decimal(str(latest_price.close))
        else:
            # Используем цену покупки если нет обновленной цены
            current_price = position.buy_price or Decimal("0")
        
        position_value = Decimal(str(position.quantity)) * current_price
        portfolio_balance += position_value
    
    # Free USD = баланс пользователя
    free_usd = user.usd_balance or Decimal("0")
    
    # Total Equity = Free USD + Portfolio Balance
    total_equity = free_usd + portfolio_balance
    
    return CashLedgerMetric(
        free_usd=free_usd,
        portfolio_balance=portfolio_balance,
        total_equity=total_equity,
        positions_count=len(positions)
    )

