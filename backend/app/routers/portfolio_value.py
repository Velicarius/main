# backend/app/routers/portfolio_value.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db
from ..models import Position, Price
from uuid import UUID
from decimal import Decimal, ROUND_HALF_UP

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def r2(x: float | Decimal) -> float:
    # банковское округление до 2 знаков
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@router.get("/value/{user_id}")
def portfolio_value(
    user_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Временная отсечка (UTC); если не задано — берём самые свежие цены)",
    ),
    db: Session = Depends(get_db),
):
    rn = func.row_number().over(
        partition_by=Price.symbol, order_by=Price.ts.desc()
    ).label("rn")

    price_q = select(Price.symbol, Price.close, rn)
    if as_of:
        price_q = price_q.where(Price.ts <= as_of)

    price_latest = price_q.subquery()

    q = (
        select(
            Position.symbol,
            Position.quantity,
            Position.price.label("buy_price"),
            price_latest.c.close.label("mkt_price"),
        )
        .join(
            price_latest,
            (price_latest.c.symbol == Position.symbol)
            & (price_latest.c.rn == 1),
        )
        .where(Position.user_id == str(user_id))
    )

    rows = db.execute(q).all()

    if not rows:
        return {
            "user_id": str(user_id),
            "as_of": as_of.isoformat() if as_of else "latest",
            "positions": [],
            "total_value": 0.0,
            "total_pnl": 0.0,
        }

    positions = []
    total_value = 0.0
    total_pnl = 0.0

    for symbol, qty, buy_price, mkt_price in rows:
        position_value = r2(qty * mkt_price)
        pnl = r2((mkt_price - buy_price) * qty)
        positions.append(
            {
                "symbol": symbol,
                "quantity": r2(qty),
                "buy_price": r2(buy_price),
                "mkt_price": r2(mkt_price),
                "position_value": position_value,
                "pnl": pnl,
            }
        )
        total_value += position_value
        total_pnl += pnl

    return {
        "user_id": str(user_id),
        "as_of": as_of.isoformat() if as_of else "latest",
        "positions": positions,
        "total_value": r2(total_value),
        "total_pnl": r2(total_pnl),
    }
