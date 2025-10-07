from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, ForeignKey, Date, Numeric, DateTime, Enum
from app.dbtypes import GUID
import uuid
from datetime import datetime
from .base import Base
import enum

class AssetClass(enum.Enum):
    EQUITY = "EQUITY"
    CRYPTO = "CRYPTO"

class Position(Base):
    __tablename__ = "positions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    symbol = Column(String, nullable=False)
    quantity = Column(Numeric(precision=20, scale=8), nullable=False)
    buy_price = Column(Numeric(precision=20, scale=8), nullable=True)
    buy_date = Column(Date, nullable=True)
    date_added = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    currency = Column(String, nullable=False, default="USD", server_default="USD")
    account = Column(String, nullable=True)
    asset_class = Column(Enum(AssetClass), nullable=False, default=AssetClass.EQUITY, server_default="EQUITY")

    user = relationship("User", back_populates="positions")

