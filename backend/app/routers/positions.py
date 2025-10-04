from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from app.database import get_db
from app.models.position import Position
from app.schemas import PositionCreate, PositionUpdate, PositionOut, BulkPositionResult, SellPositionRequest
from app.services.auto_price_loader import load_price_for_symbol, load_prices_for_symbols
from app.services.price_eod import PriceEODRepository
from app.models.price_eod import PriceEOD
from uuid import UUID
from decimal import Decimal
from typing import List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/positions", tags=["positions"])

# Константа для тестового пользователя
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.get("", response_model=List[PositionOut])
def get_positions(
    request: Request,
    db: Session = Depends(get_db)
):
    """Получить все позиции пользователя с последними ценами"""
    uid = request.session.get("user_id")
    if not uid:
        # Временная заглушка для тестирования - используем первого пользователя
        from app.models.user import User
        first_user = db.execute(select(User).limit(1)).scalar_one_or_none()
        if not first_user:
            return []
        user_id = first_user.id
    else:
        user_id = UUID(uid)
    positions = db.execute(
        select(Position).where(Position.user_id == user_id)
    ).scalars().all()
    
    # Присоединяем последние цены из EOD таблицы
    price_repo = PriceEODRepository(db)
    
    result = []
    for pos in positions:
        position_dict = {
            "id": pos.id,
            "user_id": pos.user_id,
            "symbol": pos.symbol,
            "quantity": pos.quantity,
            "buy_price": pos.buy_price,
            "buy_date": pos.buy_date,
            "date_added": pos.date_added,
            "currency": pos.currency,
            "account": pos.account,
        }
        
        # Получаем последнюю цену за день (пробуем разные варианты символа)
        latest_price = None
        symbols_to_try = [
            pos.symbol,
            pos.symbol.upper(),
            pos.symbol.lower(),
            pos.symbol.replace('.US', '.us'),
            pos.symbol.replace('.us', '.US'),
            pos.symbol.replace('.US', ''),
            pos.symbol.replace('.us', '')
        ]
        
        for symbol_variant in symbols_to_try:
            latest_price = price_repo.get_latest_price(symbol_variant)
            if latest_price:
                break
        
        if latest_price:
            position_dict["last_price"] = latest_price.close
            position_dict["last_date"] = latest_price.date
            
            # Если нет buy_price, получаем цену на дату добавления позиции
            if not pos.buy_price and pos.date_added:
                from datetime import date
                added_date = pos.date_added.date()
                price_on_added_date = price_repo.get_price_on_date(pos.symbol, added_date)
                if price_on_added_date:
                    position_dict["reference_price"] = price_on_added_date.close
                    position_dict["reference_date"] = added_date
        
        result.append(position_dict)
    
    return result


@router.post("", response_model=PositionOut)
def create_position(
    position_data: PositionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Создать новую позицию или добавить к существующей"""
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = UUID(uid)
    try:
        # Специальная обработка для USD - используем баланс вместо позиции
        symbol = position_data.symbol.upper().strip()
        if symbol == "USD":
            # Обновляем баланс пользователя вместо создания USD позиции
            from app.models.user import User
            user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if user.usd_balance is None:
                user.usd_balance = Decimal("0")
            user.usd_balance += position_data.quantity
            
            db.commit()
            return {"message": f"USD balance updated by {position_data.quantity}"}
        
        # Проверяем существующую позицию по (user_id, symbol, account)
        existing = db.execute(
            select(Position).where(
                and_(
                    Position.user_id == user_id,
                    Position.symbol == symbol,
                    Position.account == position_data.account
                )
            )
        ).scalar_one_or_none()
        
        if existing:
            # Обновляем существующую позицию - добавляем количество
            existing.quantity += position_data.quantity
            
            # Пересчитываем средневзвешенную цену покупки
            if position_data.buy_price is not None:
                if existing.buy_price is not None:
                    # Средневзвешенная цена = (старая_цена * старое_количество + новая_цена * новое_количество) / общее_количество
                    total_cost_old = existing.buy_price * (existing.quantity - position_data.quantity)
                    total_cost_new = position_data.buy_price * position_data.quantity
                    existing.buy_price = (total_cost_old + total_cost_new) / existing.quantity
                else:
                    existing.buy_price = position_data.buy_price
            
            # Обновляем дату покупки на более позднюю
            if position_data.buy_date is not None:
                if existing.buy_date is None or position_data.buy_date > existing.buy_date:
                    existing.buy_date = position_data.buy_date
            
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Создаем новую позицию
            position = Position(
                user_id=user_id,
                symbol=symbol,
                quantity=position_data.quantity,
                buy_price=position_data.buy_price,
                buy_date=position_data.buy_date,
                date_added=datetime.utcnow(),
                currency=position_data.currency or "USD",
                account=position_data.account
            )
            
            db.add(position)
            db.commit()
            db.refresh(position)
            
            # Автоматически загружаем цену для нового символа
            try:
                load_price_for_symbol(symbol, db)
                logger.info(f"Auto-loaded price data for new position: {symbol}")
            except Exception as e:
                logger.warning(f"Failed to auto-load price for {symbol}: {e}")
                # Не прерываем создание позиции из-за ошибки загрузки цены
            
            return position
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create position: {str(e)}")


@router.post("/bulk_json", response_model=BulkPositionResult)
def bulk_create_positions(
    positions: List[PositionCreate],
    request: Request,
    db: Session = Depends(get_db)
):
    """Создать или обновить множество позиций за раз"""
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = UUID(uid)
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
                    # Обновляем существующую позицию - добавляем количество
                    existing.quantity += pos_data.quantity
                    
                    # Пересчитываем средневзвешенную цену покупки
                    if pos_data.buy_price is not None:
                        if existing.buy_price is not None:
                            # Средневзвешенная цена = (старая_цена * старое_количество + новая_цена * новое_количество) / общее_количество
                            total_cost_old = existing.buy_price * (existing.quantity - pos_data.quantity)
                            total_cost_new = pos_data.buy_price * pos_data.quantity
                            existing.buy_price = (total_cost_old + total_cost_new) / existing.quantity
                        else:
                            existing.buy_price = pos_data.buy_price
                    
                    # Обновляем дату покупки на более позднюю
                    if pos_data.buy_date is not None:
                        if existing.buy_date is None or pos_data.buy_date > existing.buy_date:
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
        
        # Автоматически загружаем цены для всех новых символов
        new_symbols = set()
        for pos_data in positions:
            symbol = pos_data.symbol.upper().strip()
            if symbol != 'USD':
                new_symbols.add(symbol)
        
        if new_symbols:
            try:
                load_results = load_prices_for_symbols(list(new_symbols), db)
                loaded_count = sum(1 for success in load_results.values() if success)
                logger.info(f"Auto-loaded prices for {loaded_count}/{len(new_symbols)} new symbols")
            except Exception as e:
                logger.warning(f"Failed to auto-load prices for bulk operation: {e}")
        
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
    request: Request,
    db: Session = Depends(get_db)
):
    """Частично обновить позицию"""
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = UUID(uid)
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


@router.post("/sell", response_model=PositionOut)
def sell_position(
    sell_data: SellPositionRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Продать часть позиции за USD"""
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = UUID(uid)
    try:
        # Находим позицию для продажи
        position = db.execute(
            select(Position).where(
                and_(
                    Position.id == sell_data.position_id,
                    Position.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        if position.quantity < sell_data.quantity:
            raise HTTPException(status_code=400, detail="Insufficient quantity to sell")
        
        # Уменьшаем количество в позиции
        position.quantity -= sell_data.quantity
        
        # Если продали все, удаляем позицию
        if position.quantity == 0:
            db.delete(position)
            db.commit()
            return {"message": "Position sold completely and deleted"}
        
        # Обновляем USD баланс пользователя
        from app.models.user import User
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Рассчитываем сумму полученную от продажи
        usd_received = sell_data.quantity * (sell_data.sell_price or position.buy_price or Decimal("0"))
        
        # Обновляем баланс пользователя
        if user.usd_balance is None:
            user.usd_balance = Decimal("0")
        user.usd_balance += usd_received
        
        db.commit()
        db.refresh(position)
        return position
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to sell position: {str(e)}")


@router.delete("/{position_id}")
def delete_position(
    position_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    """Удалить позицию"""
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = UUID(uid)
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
    request: Request,
    db: Session = Depends(get_db)
):
    """Legacy endpoint для создания позиции (совместимость)"""
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = UUID(uid)
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
        
        # Автоматически загружаем цену для нового символа
        try:
            load_price_for_symbol(symbol.upper().strip(), db)
            logger.info(f"Auto-loaded price data for legacy position: {symbol}")
        except Exception as e:
            logger.warning(f"Failed to auto-load price for {symbol}: {e}")
            # Не прерываем создание позиции из-за ошибки загрузки цены
        
        return {
            "id": str(position.id),
            "symbol": position.symbol,
            "quantity": float(position.quantity),
            "buy_price": float(position.buy_price),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create position: {str(e)}")