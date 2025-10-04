from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, ForeignKey, Date, Numeric, Integer, Enum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Index
from app.dbtypes import GUID
import uuid
import time
from decimal import Decimal
from datetime import datetime
from .base import Base

# Define ENUM strings for risk levels and rebalancing frequencies
RISK_LEVEL_CHOICES = ["low", "medium", "high"]
REBAL_FREQ_CHOICES = ["none", "quarterly", "semiannual", "yearly"]

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    base_currency = Column(String(3), nullable=True, default="USD")

    # Goal settings
    target_value = Column(Numeric(precision=18, scale=2), nullable=True)
    target_date = Column(Date, nullable=True)

    # Risk and return parameters  
    risk_level = Column(String, nullable=True)
    expected_return = Column(Numeric(precision=6, scale=3), nullable=True)
    volatility = Column(Numeric(precision=6, scale=3), nullable=True)
    max_drawdown = Column(Numeric(precision=6, scale=3), nullable=True)

    # Contribution and rebalancing
    monthly_contribution = Column(Numeric(precision=18, scale=2), nullable=True)
    rebalancing_frequency = Column(String, nullable=False, server_default="none")

    # Portfolio allocation and constraints (JSONB)
    allocation = Column(JSONB, nullable=False, server_default='{}')
    constraints = Column(JSONB, nullable=False, server_default='{}')

    # Legacy fields (for backward compatibility)
    strategy_type = Column(String, nullable=True)  # Keep for migration
    
    # Timestamps (using lambda functions for compatibility)
    created_at = Column(Numeric(precision=24, scale=8), nullable=False, default=lambda: Decimal(str(time.time())))
    updated_at = Column(Numeric(precision=24, scale=8), nullable=False, default=lambda: Decimal(str(time.time())))

    # Relationships
    user = relationship("User", back_populates="strategy")

    # Indexes
    __table_args__ = (
        Index('idx_strategies_user_id', 'user_id', unique=True),
    )

    def __repr__(self):
        return f"<Strategy(user_id={self.user_id}, target_value={self.target_value})>"

