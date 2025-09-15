from pydantic import BaseModel, constr, condecimal
from typing import Optional, List
from decimal import Decimal
from datetime import date
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
