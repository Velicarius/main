"""
Cache Policy model for cache configuration
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid


class CachePolicy(Base):
    """
    Cache Policy configuration
    Manages TTL, SWR, ETag, and circuit breaker settings for different datasets
    """
    __tablename__ = "cache_policies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    dataset = Column(String(100), nullable=False, unique=True, comment='news, prices, insights')

    # TTL Configuration
    ttl_seconds = Column(Integer, nullable=False, comment='Time to live')

    # Stale-While-Revalidate (SWR)
    swr_enabled = Column(Boolean, nullable=False, default=False, comment='Stale-while-revalidate')
    swr_stale_seconds = Column(Integer, nullable=True, comment='How long to serve stale')
    swr_refresh_threshold = Column(Integer, nullable=True, comment='When to trigger refresh')

    # HTTP Caching
    etag_enabled = Column(Boolean, nullable=False, default=False)
    ims_enabled = Column(Boolean, nullable=False, default=False, comment='If-Modified-Since')

    # Cache Management
    purge_allowed = Column(Boolean, nullable=False, default=True)
    compression_enabled = Column(Boolean, nullable=False, default=False)

    # Circuit Breaker
    circuit_breaker_enabled = Column(Boolean, nullable=False, default=False)
    circuit_breaker_threshold = Column(Integer, nullable=True, default=3)
    circuit_breaker_window_seconds = Column(Integer, nullable=True, default=300)
    circuit_breaker_recovery_seconds = Column(Integer, nullable=True, default=600)

    # Additional metadata
    meta = Column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('ix_cache_policies_dataset', 'dataset'),
    )

    def __repr__(self):
        return f"<CachePolicy(dataset='{self.dataset}', ttl={self.ttl_seconds}s, swr={self.swr_enabled})>"

    @property
    def effective_ttl(self) -> int:
        """Get effective TTL including stale period if SWR enabled"""
        if self.swr_enabled and self.swr_stale_seconds:
            return self.ttl_seconds + self.swr_stale_seconds
        return self.ttl_seconds
