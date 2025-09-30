from celery import Celery
from celery.schedules import crontab
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_beat_schedule():
    """Get beat schedule based on feature flags"""
    if not settings.eod_enable:
        logger.info("EOD feature is disabled, no beat schedule configured")
        return {}
    
    if settings.eod_source != "stooq":
        logger.warning(f"EOD source '{settings.eod_source}' is not supported for beat schedule")
        return {}
    
    # Parse CRON string (format: "minute hour day month day_of_week")
    cron_parts = settings.eod_schedule_cron.split()
    if len(cron_parts) != 5:
        logger.warning(f"Invalid CRON format '{settings.eod_schedule_cron}', using default 23:30")
        minute, hour = 30, 23
    else:
        try:
            minute = int(cron_parts[0])
            hour = int(cron_parts[1])
        except ValueError:
            logger.warning(f"Invalid CRON values, using default 23:30")
            minute, hour = 30, 23
    
    logger.info(f"EOD beat schedule enabled: daily at {hour:02d}:{minute:02d}")
    
    return {
        "nightly_eod": {
            "task": "prices.run_eod_refresh",
            "schedule": crontab(hour=hour, minute=minute),
            "args": (),
        },
    }


# Create Celery app
celery_app = Celery(
    "ai-portfolio",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/1",
    include=[
        "app.tasks.fetch_eod",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=getattr(settings, "timezone", "UTC"),
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    
    # Beat schedule - only include if EOD is enabled
    beat_schedule=_get_beat_schedule(),
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
)


def _get_beat_schedule():
    """Get beat schedule based on feature flags"""
    if not settings.eod_enable:
        logger.info("EOD feature is disabled, no beat schedule configured")
        return {}
    
    if settings.eod_source != "stooq":
        logger.warning(f"EOD source '{settings.eod_source}' is not supported for beat schedule")
        return {}
    
    # Parse CRON string (format: "minute hour day month day_of_week")
    cron_parts = settings.eod_schedule_cron.split()
    if len(cron_parts) != 5:
        logger.warning(f"Invalid CRON format '{settings.eod_schedule_cron}', using default 23:30")
        minute, hour = 30, 23
    else:
        try:
            minute = int(cron_parts[0])
            hour = int(cron_parts[1])
        except ValueError:
            logger.warning(f"Invalid CRON values, using default 23:30")
            minute, hour = 30, 23
    
    logger.info(f"EOD beat schedule enabled: daily at {hour:02d}:{minute:02d}")
    
    return {
        "nightly_eod": {
            "task": "prices.run_eod_refresh",
            "schedule": crontab(hour=hour, minute=minute),
            "args": (),
        },
    }


# Import tasks to register them
from app.tasks import fetch_eod  # noqa





