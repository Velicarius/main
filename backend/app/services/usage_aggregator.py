"""
Usage Aggregator Service
Aggregates user_activity_log into daily usage_metrics
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from sqlalchemy.dialects.postgresql import insert

from app.models.user_activity_log import UserActivityLog
from app.models.usage_metrics import UsageMetrics

logger = logging.getLogger(__name__)


class UsageAggregator:
    """
    Service for aggregating usage statistics

    Features:
    - Aggregate daily usage from activity logs
    - Group by user/provider/endpoint
    - Calculate request counts, error rates, avg response times
    - Upsert to usage_metrics table
    """

    def __init__(self, db: Session):
        self.db = db

    def aggregate_daily_usage(self, user_id: UUID, target_date: date) -> List[UsageMetrics]:
        """
        Aggregate usage for a specific user and date

        Args:
            user_id: User ID
            target_date: Date to aggregate

        Returns:
            List of created/updated UsageMetrics records
        """
        logger.info(f"Aggregating usage for user {user_id} on {target_date}")

        # Define time range for the day
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = datetime.combine(target_date, datetime.max.time())

        # Query activity logs for this user and date
        activities = self.db.execute(
            select(UserActivityLog).where(
                and_(
                    UserActivityLog.user_id == user_id,
                    UserActivityLog.timestamp >= start_time,
                    UserActivityLog.timestamp <= end_time
                )
            )
        ).scalars().all()

        if not activities:
            logger.info(f"No activity found for user {user_id} on {target_date}")
            return []

        # Group activities by provider and endpoint
        grouped = {}

        for activity in activities:
            provider = activity.provider or 'unknown'
            endpoint = activity.endpoint

            # Create key for grouping
            key = (provider, endpoint)

            if key not in grouped:
                grouped[key] = {
                    'requests': [],
                    'errors': 0,
                    'total_response_time': 0,
                    'response_count': 0,
                }

            grouped[key]['requests'].append(activity)

            # Count errors (4xx, 5xx status codes)
            if activity.status_code and activity.status_code >= 400:
                grouped[key]['errors'] += 1

            # Track response times
            if activity.response_time_ms:
                grouped[key]['total_response_time'] += activity.response_time_ms
                grouped[key]['response_count'] += 1

        # Create/update usage metrics
        results = []

        for (provider, endpoint), data in grouped.items():
            request_count = len(data['requests'])
            error_count = data['errors']

            # Calculate average response time
            avg_response_time = None
            if data['response_count'] > 0:
                avg_response_time = int(data['total_response_time'] / data['response_count'])

            # Upsert usage metrics
            stmt = insert(UsageMetrics).values(
                user_id=user_id,
                provider=provider,
                endpoint=endpoint,
                metric_date=target_date,
                request_count=request_count,
                error_count=error_count,
                avg_response_time_ms=avg_response_time,
                tokens_used=0,  # TODO: Track LLM tokens from request_metadata
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # On conflict, update the existing record
            stmt = stmt.on_conflict_do_update(
                index_elements=['user_id', 'provider', 'endpoint', 'metric_date'],
                set_={
                    'request_count': stmt.excluded.request_count,
                    'error_count': stmt.excluded.error_count,
                    'avg_response_time_ms': stmt.excluded.avg_response_time_ms,
                    'updated_at': datetime.utcnow()
                }
            )

            self.db.execute(stmt)

        self.db.commit()

        # Fetch created metrics
        metrics = self.db.execute(
            select(UsageMetrics).where(
                and_(
                    UsageMetrics.user_id == user_id,
                    UsageMetrics.metric_date == target_date
                )
            )
        ).scalars().all()

        logger.info(f"Created/updated {len(metrics)} usage metrics for user {user_id} on {target_date}")

        return list(metrics)

    def aggregate_all_users(self, target_date: date):
        """
        Aggregate usage for all users on a specific date

        Args:
            target_date: Date to aggregate

        Returns:
            Number of metrics created
        """
        logger.info(f"Aggregating usage for all users on {target_date}")

        # Get all unique user IDs that have activity on this date
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = datetime.combine(target_date, datetime.max.time())

        user_ids = self.db.execute(
            select(UserActivityLog.user_id).distinct().where(
                and_(
                    UserActivityLog.timestamp >= start_time,
                    UserActivityLog.timestamp <= end_time
                )
            )
        ).scalars().all()

        total_metrics = 0

        for user_id in user_ids:
            metrics = self.aggregate_daily_usage(user_id, target_date)
            total_metrics += len(metrics)

        logger.info(f"Aggregated {total_metrics} metrics for {len(user_ids)} users on {target_date}")

        return total_metrics

    def cleanup_old_activity_logs(self, retention_days: int = 90):
        """
        Delete activity logs older than retention period

        Args:
            retention_days: Number of days to retain logs (default 90)

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        result = self.db.execute(
            UserActivityLog.__table__.delete().where(
                UserActivityLog.timestamp < cutoff_date
            )
        )

        self.db.commit()

        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} activity logs older than {retention_days} days")

        return deleted_count
