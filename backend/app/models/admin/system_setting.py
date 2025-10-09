"""
System Setting model for generic key-value configuration
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Index
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from typing import Any


class SystemSetting(Base):
    """
    System-wide settings storage
    Generic key-value store for configuration not fitting other tables
    """
    __tablename__ = "system_settings"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    category = Column(String(100), nullable=False, comment='database, celery, redis, general')
    key = Column(String(200), nullable=False, comment='pool_size, timezone, max_connections')
    value_type = Column(String(20), nullable=False, default='string', comment='string, number, boolean, json')
    value = Column(Text, nullable=True)
    value_json = Column(JSONB, nullable=True)
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, nullable=False, default=False, comment='Mask in UI')
    validation_regex = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('ix_system_settings_category', 'category'),
        Index('idx_system_settings_unique', 'category', 'key', unique=True),
    )

    def __repr__(self):
        return f"<SystemSetting(category='{self.category}', key='{self.key}')>"

    def get_value(self) -> Any:
        """Get typed value based on value_type"""
        if self.value_type == 'json':
            return self.value_json
        elif self.value_type == 'boolean':
            return self.value.lower() == 'true' if self.value else False
        elif self.value_type == 'number':
            try:
                return int(self.value) if self.value else 0
            except ValueError:
                try:
                    return float(self.value) if self.value else 0.0
                except ValueError:
                    return 0
        return self.value  # string

    def set_value(self, value: Any):
        """Set value based on type"""
        if self.value_type == 'json':
            self.value_json = value
            self.value = None
        else:
            self.value = str(value)
            self.value_json = None
