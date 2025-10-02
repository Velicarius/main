from pydantic import BaseModel, constr, condecimal
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID


class PositionCreate(BaseModel):
    symbol: constr(strip_whitespace=True, min_length=1)
    quantity: condecimal(gt=0)
    buy_price: Optional[condecimal(gt=0)] = None
    buy_date: Optional[date] = None
    currency: Optional[str] = "USD"
    account: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "quantity": "10.5",
                "buy_price": "150.25",
                "buy_date": "2024-01-15",
                "currency": "USD",
                "account": "main"
            }
        }


class SellPositionRequest(BaseModel):
    position_id: UUID
    quantity: condecimal(gt=0)
    sell_price: Optional[condecimal(gt=0)] = None
    sell_date: Optional[date] = None
    currency: Optional[str] = "USD"

    class Config:
        json_schema_extra = {
            "example": {
                "position_id": "123e4567-e89b-12d3-a456-426614174000",
                "quantity": "5.0",
                "sell_price": "160.00",
                "sell_date": "2024-01-20",
                "currency": "USD"
            }
        }


class PositionUpdate(BaseModel):
    quantity: Optional[condecimal(gt=0)] = None
    buy_price: Optional[condecimal(gt=0)] = None
    buy_date: Optional[date] = None
    currency: Optional[str] = None
    account: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "quantity": "15.0",
                "buy_price": "155.30",
                "currency": "USD"
            }
        }


class PositionOut(BaseModel):
    id: UUID
    user_id: UUID
    symbol: str
    quantity: Decimal
    buy_price: Optional[Decimal]
    buy_date: Optional[date]
    currency: str
    account: Optional[str]
    last_price: Optional[Decimal] = None
    last_date: Optional[date] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "00000000-0000-0000-0000-000000000001",
                "symbol": "AAPL",
                "quantity": "10.5",
                "buy_price": "150.25",
                "buy_date": "2024-01-15",
                "currency": "USD",
                "account": "main"
            }
        }


class BulkPositionResult(BaseModel):
    inserted: int
    updated: int
    failed: int
    errors: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "inserted": 2,
                "updated": 1,
                "failed": 1,
                "errors": ["Invalid symbol: empty string"]
            }
        }
# --- PriceEOD schemas ---

class PriceEODCreate(BaseModel):
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None
    source: Optional[str] = None


class PriceEODUpdate(BaseModel):
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    source: Optional[str] = None


class PriceEODResponse(BaseModel):
    id: UUID
    symbol: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None
    source: Optional[str] = None
    ingested_at: datetime

    class Config:
        from_attributes = True


class PortfolioValuationEODOut(BaseModel):
    id: UUID
    user_id: UUID
    as_of: date
    total_value: Decimal
    currency: str
    created_at: datetime
    class Config:
        from_attributes = True


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
