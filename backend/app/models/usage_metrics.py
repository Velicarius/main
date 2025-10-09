"""
Usage Metrics model for aggregated usage statistics
"""
from sqlalchemy import Column, String, Integer, BigInteger, Date, DateTime, ForeignKey, Index
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
import uuid


class UsageMetrics(Base):
    """
    Aggregated daily usage statistics per user/provider
    Created by background job that processes user_activity_log
    """
    __tablename__ = "usage_metrics"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Scope
    provider = Column(String(100), nullable=True, comment='API provider or NULL for totals')
    endpoint = Column(String(500), nullable=True, comment='Specific endpoint or NULL for provider total')
    metric_date = Column(Date, nullable=False, comment='Date of aggregated metrics')

    # Metrics
    request_count = Column(Integer, nullable=False, default=0)
    tokens_used = Column(BigInteger, nullable=False, default=0, comment='For LLM providers')
    error_count = Column(Integer, nullable=False, default=0)
    avg_response_time_ms = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_usage_unique', 'user_id', 'provider', 'endpoint', 'metric_date', unique=True),
        Index('ix_usage_user_date', 'user_id', 'metric_date'),
        Index('ix_usage_provider', 'provider', 'metric_date'),
    )

    def __repr__(self):
        return f"<UsageMetrics(user_id='{self.user_id}', provider='{self.provider}', date={self.metric_date}, requests={self.request_count})>"
