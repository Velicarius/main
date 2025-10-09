"""
Portfolio Snapshot model for calculated portfolio metrics
"""
from sqlalchemy import Column, String, Integer, Date, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
import uuid


class PortfolioSnapshot(Base):
    """
    Daily snapshot of portfolio metrics and analytics
    Calculated by background job from positions and prices
    """
    __tablename__ = "portfolio_snapshots"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    as_of = Column(Date, nullable=False, comment='Snapshot date')

    # Portfolio metrics
    total_value = Column(Numeric(20, 8), nullable=True)
    total_invested = Column(Numeric(20, 8), nullable=True)
    total_return_pct = Column(Numeric(10, 4), nullable=True, comment='Total return percentage')
    positions_count = Column(Integer, nullable=False, default=0)

    # Allocation and holdings
    allocation = Column(JSONB, nullable=True, default=dict, comment='Allocation by asset class')
    top_holdings = Column(JSONB, nullable=True, default=list, comment='Top 5 positions by value')

    # Risk metrics
    risk_metrics = Column(JSONB, nullable=True, default=dict, comment='Volatility, sharpe ratio, etc')

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_portfolio_snapshot_unique', 'user_id', 'as_of', unique=True),
        Index('ix_snapshot_user_date', 'user_id', 'as_of'),
        Index('ix_snapshot_date', 'as_of'),
    )

    def __repr__(self):
        return f"<PortfolioSnapshot(user_id='{self.user_id}', as_of={self.as_of}, value={self.total_value})>"
