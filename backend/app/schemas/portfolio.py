from pydantic import BaseModel
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID


class PortfolioValuationEODOut(BaseModel):
    id: UUID
    user_id: UUID
    as_of: date
    total_value: Decimal
    currency: str
    created_at: datetime
    
    class Config:
        from_attributes = True


