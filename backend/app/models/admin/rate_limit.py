"""
Rate Limit and Quota models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, BigInteger, Numeric, Index
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
import uuid


class RateLimit(Base):
    """
    Rate Limiting configuration
    Controls request rates for users, endpoints, providers
    """
    __tablename__ = "rate_limits"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    scope = Column(String(100), nullable=False, comment='user, plan, provider, endpoint, global')
    scope_id = Column(String(200), nullable=True, comment='user_id, provider_name, endpoint_path')
    window_seconds = Column(Integer, nullable=False, comment='Time window for limit')
    limit = Column(Integer, nullable=False, comment='Max requests in window')
    burst = Column(Integer, nullable=True, comment='Burst allowance')
    policy = Column(String(50), nullable=False, default='reject', comment='reject, queue, throttle')
    is_enabled = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('ix_rate_limits_scope', 'scope', 'scope_id'),
        Index('ix_rate_limits_enabled', 'is_enabled'),
        Index('idx_rate_limit_unique', 'scope', 'scope_id', unique=True),
    )

    def __repr__(self):
        return f"<RateLimit(scope='{self.scope}', limit={self.limit}/{self.window_seconds}s)>"


class Quota(Base):
    """
    Resource Quota management
    Tracks usage and limits for various resources (API calls, tokens, storage)
    """
    __tablename__ = "quotas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    scope = Column(String(100), nullable=False, comment='user, plan, provider, resource')
    scope_id = Column(String(200), nullable=True)
    resource_type = Column(String(100), nullable=False, comment='llm_tokens, api_calls, storage')
    period = Column(String(20), nullable=False, comment='hour, day, month')
    hard_cap = Column(BigInteger, nullable=False, comment='Absolute limit')
    soft_cap = Column(BigInteger, nullable=True, comment='Warning threshold')
    current_usage = Column(BigInteger, nullable=False, default=0)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    action_on_breach = Column(String(50), nullable=False, default='block', comment='block, notify, throttle')
    is_enabled = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('ix_quotas_scope', 'scope', 'scope_id', 'resource_type'),
        Index('ix_quotas_period', 'period_start', 'period_end'),
        Index('ix_quotas_enabled', 'is_enabled'),
    )

    def __repr__(self):
        return f"<Quota(scope='{self.scope}', resource='{self.resource_type}', usage={self.current_usage}/{self.hard_cap})>"

    @property
    def usage_percentage(self) -> float:
        """Calculate usage as percentage of hard cap"""
        if self.hard_cap == 0:
            return 0.0
        return (self.current_usage / self.hard_cap) * 100

    @property
    def is_over_soft_cap(self) -> bool:
        """Check if usage exceeds soft cap"""
        if self.soft_cap is None:
            return False
        return self.current_usage >= self.soft_cap

    @property
    def is_over_hard_cap(self) -> bool:
        """Check if usage exceeds hard cap"""
        return self.current_usage >= self.hard_cap
