from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Position
from uuid import UUID

router = APIRouter(prefix="/positions", tags=["positions"])

class PositionIn(BaseModel):
    user_id: UUID
    symbol: str
    quantity: float
    price: float

@router.post("/add")
def add_position(data: PositionIn, db: Session = Depends(get_db)):
    pos = Position(
        user_id=str(data.user_id),
        symbol=data.symbol.upper().strip(),
        quantity=float(data.quantity),
        price=float(data.price),
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return {
        "id": str(pos.id),
        "symbol": pos.symbol,
        "quantity": pos.quantity,
        "price": pos.price,
    }
