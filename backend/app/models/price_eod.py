from sqlalchemy import Column, String, Float, Date, DateTime, UniqueConstraint, Index
from datetime import datetime
from app.dbtypes import GUID
import uuid
from .base import Base

class PriceEOD(Base):
    """End-of-day price data model"""
    __tablename__ = "prices_eod"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, index=True, nullable=False)           # Stock symbol (e.g., AAPL)
    date = Column(Date, nullable=False)                          # Trading date
    open = Column(Float, nullable=True)                          # Opening price
    high = Column(Float, nullable=True)                          # High price
    low = Column(Float, nullable=True)                           # Low price
    close = Column(Float, nullable=False)                         # Closing price
    volume = Column(Float, nullable=True)                        # Trading volume
    source = Column(String, nullable=True)                        # Data source (e.g., 'yahoo', 'alpha_vantage')
    ingested_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)  # When data was ingested

    # Table constraints and indexes
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_price_eod_symbol_date"),
        Index("ix_price_eod_symbol_date", "symbol", "date"),
        Index("ix_price_eod_date", "date"),
    )

