from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID


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





