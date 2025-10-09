"""
User Activity Log model for tracking API requests
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
import uuid


class UserActivityLog(Base):
    """
    Tracks every API call made by users
    Used for usage analytics, auditing, and quota enforcement
    """
    __tablename__ = "user_activity_log"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Request details
    endpoint = Column(String(500), nullable=False, comment='API endpoint path')
    method = Column(String(10), nullable=False, comment='HTTP method')
    status_code = Column(Integer, nullable=True, comment='HTTP response status')
    response_time_ms = Column(Integer, nullable=True, comment='Response time in milliseconds')

    # Provider tracking
    provider = Column(String(100), nullable=True, comment='API provider used')

    # Additional context
    request_metadata = Column(JSONB, nullable=True, default=dict)

    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_activity_user_ts', 'user_id', 'timestamp'),
        Index('ix_activity_provider', 'provider', 'timestamp'),
        Index('ix_activity_endpoint', 'endpoint'),
        Index('ix_activity_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<UserActivityLog(user_id='{self.user_id}', endpoint='{self.endpoint}', status={self.status_code})>"
