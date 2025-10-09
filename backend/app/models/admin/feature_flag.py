"""
Feature Flag model for runtime configuration
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Numeric, Index
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from typing import Any, Optional


class FeatureFlag(Base):
    """
    Feature Flag for runtime configuration
    Supports boolean, string, JSON, and numeric values
    """
    __tablename__ = "feature_flags"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), nullable=False, unique=True, comment='EOD_ENABLE, NEWS_ENABLE')
    value_type = Column(String(20), nullable=False, default='boolean', comment='boolean, string, json, number')
    value_boolean = Column(Boolean, nullable=True)
    value_string = Column(Text, nullable=True)
    value_json = Column(JSONB, nullable=True)
    value_number = Column(Numeric, nullable=True)
    env_scope = Column(String(50), nullable=False, default='all', comment='all, production, staging, dev')
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('ix_feature_flags_key', 'key'),
        Index('ix_feature_flags_enabled', 'is_enabled', 'env_scope'),
    )

    def __repr__(self):
        return f"<FeatureFlag(key='{self.key}', value={self.get_value()}, enabled={self.is_enabled})>"

    def get_value(self) -> Any:
        """Get the value based on value_type"""
        if self.value_type == 'boolean':
            return self.value_boolean
        elif self.value_type == 'string':
            return self.value_string
        elif self.value_type == 'json':
            return self.value_json
        elif self.value_type == 'number':
            return float(self.value_number) if self.value_number is not None else None
        return None

    def set_value(self, value: Any):
        """Set the value based on type"""
        if self.value_type == 'boolean':
            self.value_boolean = bool(value)
        elif self.value_type == 'string':
            self.value_string = str(value)
        elif self.value_type == 'json':
            self.value_json = value
        elif self.value_type == 'number':
            self.value_number = value

    def is_active_for_env(self, current_env: str) -> bool:
        """Check if flag is active for the given environment"""
        if not self.is_enabled:
            return False
        if self.env_scope == 'all':
            return True
        return self.env_scope == current_env
