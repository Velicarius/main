"""
Audit Log model for tracking all admin changes
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid


class AuditLog(Base):
    """
    Audit Log for admin actions
    Tracks all configuration changes with before/after state
    """
    __tablename__ = "audit_log"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Actor information
    actor_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment='User who made change')
    actor_type = Column(String(50), nullable=False, default='user', comment='user, system, api')

    # Action details
    action = Column(String(100), nullable=False, comment='create, update, delete, enable, disable')
    entity_type = Column(String(100), nullable=False, comment='feature_flag, api_provider, schedule')
    entity_id = Column(GUID(), nullable=True)
    entity_name = Column(String(200), nullable=True, comment='Human-readable name')

    # State tracking
    before_state = Column(JSONB, nullable=True, comment='State before change')
    after_state = Column(JSONB, nullable=True, comment='State after change')

    # Request context
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True)

    # Additional metadata
    audit_metadata = Column(JSONB, nullable=True, default=dict)

    # Indexes
    __table_args__ = (
        Index('ix_audit_log_actor', 'actor_id', 'timestamp'),
        Index('ix_audit_log_entity', 'entity_type', 'entity_id', 'timestamp'),
        Index('ix_audit_log_action', 'action', 'timestamp'),
        Index('ix_audit_log_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', entity='{self.entity_type}', timestamp={self.timestamp})>"

    @property
    def changes(self) -> dict:
        """Calculate what changed between before and after states"""
        if not self.before_state or not self.after_state:
            return {}

        changes = {}
        all_keys = set(self.before_state.keys()) | set(self.after_state.keys())

        for key in all_keys:
            before_val = self.before_state.get(key)
            after_val = self.after_state.get(key)

            if before_val != after_val:
                changes[key] = {
                    'before': before_val,
                    'after': after_val
                }

        return changes
