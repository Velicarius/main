from pydantic import BaseModel, condecimal
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from .position import PositionOut


class UserOut(BaseModel):
    id: UUID
    email: str
    name: Optional[str]
    usd_balance: Decimal

    class Config:
        from_attributes = True


class BalanceUpdateRequest(BaseModel):
    usd_balance: condecimal(ge=0)


class CashLedgerMetric(BaseModel):
    """Метрика денежной кассы пользователя"""
    free_usd: Decimal  # Свободные деньги в USD
    portfolio_balance: Decimal  # Рыночная стоимость позиций в USD
    total_equity: Decimal  # Общий капитал = Free USD + Portfolio Balance
    positions_count: int  # Количество позиций


class UserWithBalance(BaseModel):
    id: UUID
    email: str
    name: Optional[str]
    usd_balance: Decimal
    positions: List[PositionOut]




