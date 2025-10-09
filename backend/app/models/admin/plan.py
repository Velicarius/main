"""
Plan model for user subscription tiers
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Index
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid


class Plan(Base):
    """
    Subscription Plan configuration
    Defines features and limits for different user tiers
    """
    __tablename__ = "plans"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True, comment='free, pro, enterprise')
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    features = Column(JSONB, nullable=False, default=dict, comment='Feature flags')
    limits = Column(JSONB, nullable=False, default=dict, comment='Rate limits & quotas')
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('ix_plans_code', 'code'),
        Index('ix_plans_active', 'is_active'),
    )

    def __repr__(self):
        return f"<Plan(code='{self.code}', name='{self.name}', active={self.is_active})>"

    def has_feature(self, feature_key: str) -> bool:
        """Check if plan includes a specific feature"""
        return self.features.get(feature_key, False) if self.features else False

    def get_limit(self, limit_key: str, default=None):
        """Get a specific limit value"""
        return self.limits.get(limit_key, default) if self.limits else default
