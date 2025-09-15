from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from ..database import get_db
from ..models import Position
from ..schemas import PositionCreate, PositionUpdate, PositionOut, BulkPositionResult
from uuid import UUID
from decimal import Decimal
from typing import List

router = APIRouter(prefix="/positions", tags=["positions"])

# Константа для тестового пользователя
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.get("", response_model=List[PositionOut])
def get_positions(
    user_id: UUID = Query(default=TEST_USER_ID, description="ID пользователя"),
    db: Session = Depends(get_db)
):
    """Получить все позиции пользователя"""
    positions = db.execute(
        select(Position).where(Position.user_id == user_id)
    ).scalars().all()
    
    return positions


@router.post("", response_model=PositionOut)
def create_position(
    position_data: PositionCreate,
    user_id: UUID = Query(default=TEST_USER_ID, description="ID пользователя"),
    db: Session = Depends(get_db)
):
    """Создать новую позицию"""
    try:
        position = Position(
            user_id=user_id,
            symbol=position_data.symbol.upper().strip(),
            quantity=position_data.quantity,
            buy_price=position_data.buy_price,
            buy_date=position_data.buy_date,
            currency=position_data.currency or "USD",
            account=position_data.account
        )
        
        db.add(position)
        db.commit()
        db.refresh(position)
        
        return position
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create position: {str(e)}")


@router.post("/bulk_json", response_model=BulkPositionResult)
def bulk_create_positions(
    positions: List[PositionCreate],
    user_id: UUID = Query(default=TEST_USER_ID, description="ID пользователя"),
    db: Session = Depends(get_db)
):
    """Создать или обновить множество позиций за раз"""
    inserted = 0
    updated = 0
    failed = 0
    errors = []
    
    try:
        for pos_data in positions:
            try:
                # Проверяем существующую позицию по (user_id, symbol, account)
                existing = db.execute(
                    select(Position).where(
                        and_(
                            Position.user_id == user_id,
                            Position.symbol == pos_data.symbol.upper().strip(),
                            Position.account == pos_data.account
                        )
                    )
                ).scalar_one_or_none()
                
                if existing:
                    # Обновляем существующую позицию
                    existing.quantity = pos_data.quantity
                    if pos_data.buy_price is not None:
                        existing.buy_price = pos_data.buy_price
                    if pos_data.buy_date is not None:
                        existing.buy_date = pos_data.buy_date
                    if pos_data.currency is not None:
                        existing.currency = pos_data.currency
                    if pos_data.account is not None:
                        existing.account = pos_data.account
                    updated += 1
                else:
                    # Создаем новую позицию
                    new_position = Position(
                        user_id=user_id,
                        symbol=pos_data.symbol.upper().strip(),
                        quantity=pos_data.quantity,
                        buy_price=pos_data.buy_price,
                        buy_date=pos_data.buy_date,
                        currency=pos_data.currency or "USD",
                        account=pos_data.account
                    )
                    db.add(new_position)
                    inserted += 1
                    
            except Exception as e:
                failed += 1
                errors.append(f"Failed to process {pos_data.symbol}: {str(e)}")
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Bulk operation failed: {str(e)}")
    
    return BulkPositionResult(
        inserted=inserted,
        updated=updated,
        failed=failed,
        errors=errors
    )


@router.patch("/{position_id}", response_model=PositionOut)
def update_position(
    position_id: UUID,
    position_data: PositionUpdate,
    user_id: UUID = Query(default=TEST_USER_ID, description="ID пользователя"),
    db: Session = Depends(get_db)
):
    """Частично обновить позицию"""
    position = db.execute(
        select(Position).where(
            and_(
                Position.id == position_id,
                Position.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    try:
        # Обновляем только переданные поля
        update_data = position_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(position, field, value)
        
        db.commit()
        db.refresh(position)
        
        return position
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update position: {str(e)}")


@router.delete("/{position_id}")
def delete_position(
    position_id: UUID,
    user_id: UUID = Query(default=TEST_USER_ID, description="ID пользователя"),
    db: Session = Depends(get_db)
):
    """Удалить позицию"""
    position = db.execute(
        select(Position).where(
            and_(
                Position.id == position_id,
                Position.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    try:
        db.delete(position)
        db.commit()
        return {"message": "Position deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete position: {str(e)}")


# Старый эндпоинт для совместимости
@router.post("/add")
def add_position_legacy(
    symbol: str,
    quantity: float,
    price: float,
    user_id: UUID = Query(default=TEST_USER_ID, description="ID пользователя"),
    db: Session = Depends(get_db)
):
    """Legacy endpoint для создания позиции (совместимость)"""
    try:
        position = Position(
            user_id=user_id,
            symbol=symbol.upper().strip(),
            quantity=Decimal(str(quantity)),
            buy_price=Decimal(str(price)),
            currency="USD"
        )
        
        db.add(position)
        db.commit()
        db.refresh(position)
        
        return {
            "id": str(position.id),
            "symbol": position.symbol,
            "quantity": float(position.quantity),
            "buy_price": float(position.buy_price),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create position: {str(e)}")