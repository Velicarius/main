"""
Schedule model for Celery tasks and cron jobs
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid


class Schedule(Base):
    """
    Task Schedule configuration
    Manages Celery tasks, cron jobs, and manual triggers
    """
    __tablename__ = "schedules"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    task_name = Column(String(200), nullable=False, unique=True, comment='prices.run_eod_refresh')
    task_type = Column(String(50), nullable=False, default='celery', comment='celery, cron, manual')
    cron_expression = Column(String(100), nullable=True, comment='30 23 * * *')
    timezone = Column(String(50), nullable=False, default='UTC')
    is_enabled = Column(Boolean, nullable=False, default=True)

    # Execution tracking
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(20), nullable=True, comment='success, failure, timeout')
    last_run_duration_ms = Column(Integer, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    # Task configuration
    payload = Column(JSONB, nullable=True, default=dict, comment='Task parameters')
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('ix_schedules_task_name', 'task_name'),
        Index('ix_schedules_enabled', 'is_enabled'),
        Index('ix_schedules_next_run', 'next_run_at', 'is_enabled'),
    )

    def __repr__(self):
        return f"<Schedule(task_name='{self.task_name}', enabled={self.is_enabled})>"

    @property
    def is_due(self) -> bool:
        """Check if task is due to run"""
        if not self.is_enabled or self.next_run_at is None:
            return False
        return self.next_run_at <= datetime.utcnow()

    @property
    def should_retry(self) -> bool:
        """Check if task should retry after failure"""
        return self.retry_count < self.max_retries
