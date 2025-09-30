from datetime import datetime
from sqlalchemy import Column, String, Date, DateTime, Numeric, ForeignKey, UniqueConstraint, Index
from app.dbtypes import GUID
import uuid
from .base import Base

class PortfolioValuationEOD(Base):
    __tablename__ = "portfolio_valuations_eod"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    as_of = Column(Date, nullable=False)
    total_value = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(8), nullable=False, default="USD", server_default="USD")
    created_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "as_of", name="uq_portfolio_valuations_eod_user_asof"),
        Index("ix_pv_user_asof", "user_id", "as_of"),
        Index("ix_pv_asof", "as_of"),
    )

