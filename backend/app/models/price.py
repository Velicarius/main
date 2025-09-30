from sqlalchemy import Column, String, Float, DateTime, UniqueConstraint, Index
from app.dbtypes import GUID
import uuid
from .base import Base

class Price(Base):
    __tablename__ = "prices"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, index=True, nullable=False)           # тикер, напр. AAPL
    ts = Column(DateTime(timezone=False), nullable=False)         # метка времени (UTC)
    close = Column(Float, nullable=False)                         # цена закрытия

    # частые запросы: по символу и интервалу времени
    __table_args__ = (
        UniqueConstraint("symbol", "ts", name="uq_price_symbol_ts"),
        Index("ix_price_symbol_ts", "symbol", "ts"),
    )

