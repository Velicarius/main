"""
API Provider and Credentials models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid


class ApiProvider(Base):
    """
    API Provider configuration
    Manages external service providers (news, crypto, LLM, etc.)
    """
    __tablename__ = "api_providers"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False, comment='news, crypto, llm, eod')
    name = Column(String(100), nullable=False, unique=True, comment='binance, newsapi, ollama')
    base_url = Column(String(500), nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_shadow_mode = Column(Boolean, nullable=False, default=False, comment='Test without using results')
    priority = Column(Integer, nullable=False, default=100, comment='Lower = higher priority')
    timeout_seconds = Column(Integer, nullable=False, default=10)
    config_meta = Column(JSONB, nullable=True, default=dict, comment='Provider-specific config')

    # Timestamps and soft delete
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    credentials = relationship("ApiCredential", back_populates="provider", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_api_providers_type', 'type'),
        Index('ix_api_providers_enabled', 'is_enabled', 'is_deleted'),
        Index('ix_api_providers_priority', 'priority'),
    )

    def __repr__(self):
        return f"<ApiProvider(name='{self.name}', type='{self.type}', enabled={self.is_enabled})>"


class ApiCredential(Base):
    """
    API Credentials storage
    Stores encrypted API keys with masking and status tracking
    """
    __tablename__ = "api_credentials"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    provider_id = Column(GUID(), ForeignKey("api_providers.id", ondelete="CASCADE"), nullable=False)
    key_name = Column(String(100), nullable=False, comment='OPENAI_API_KEY, FINNHUB_API_KEY')
    masked_key = Column(String(100), nullable=True, comment='sk-...abc123')
    encrypted_key = Column(Text, nullable=True, comment='Encrypted actual key')
    status = Column(String(20), nullable=False, default='active', comment='active, expired, invalid')
    last_check_at = Column(DateTime, nullable=True)
    last_check_status = Column(String(20), nullable=True, comment='success, failure')
    expires_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps and soft delete
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    provider = relationship("ApiProvider", back_populates="credentials")

    # Indexes
    __table_args__ = (
        Index('ix_api_credentials_provider', 'provider_id'),
        Index('ix_api_credentials_status', 'status', 'is_deleted'),
    )

    def __repr__(self):
        return f"<ApiCredential(key_name='{self.key_name}', status='{self.status}')>"
