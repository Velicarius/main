from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)

    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")

class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    symbol = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)

    user = relationship("User", back_populates="positions")


from sqlalchemy import Column, String, Float, ForeignKey, DateTime, UniqueConstraint, Index
from datetime import datetime

class Price(Base):
    __tablename__ = "prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, index=True, nullable=False)           # тикер, напр. AAPL
    ts = Column(DateTime(timezone=False), nullable=False)         # метка времени (UTC)
    close = Column(Float, nullable=False)                         # цена закрытия

    # частые запросы: по символу и интервалу времени
    __table_args__ = (
        UniqueConstraint("symbol", "ts", name="uq_price_symbol_ts"),
        Index("ix_price_symbol_ts", "symbol", "ts"),
    )
