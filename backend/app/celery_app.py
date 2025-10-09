from celery import Celery
from celery.schedules import crontab
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_beat_schedule():
    """Get beat schedule based on feature flags"""
    schedule = {}
    
    # EOD tasks
    if settings.eod_enable:
        if settings.eod_source != "stooq":
            logger.warning(f"EOD source '{settings.eod_source}' is not supported for beat schedule")
        else:
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

            # Portfolio valuation runs 15 minutes after EOD price refresh
            valuation_minute = (minute + 15) % 60
            valuation_hour = hour if (minute + 15) < 60 else (hour + 1) % 24

            logger.info(f"Portfolio valuation schedule enabled: daily at {valuation_hour:02d}:{valuation_minute:02d}")

            schedule.update({
                "nightly_eod": {
                    "task": "prices.run_eod_refresh",
                    "schedule": crontab(hour=hour, minute=minute),
                    "args": (),
                },
                "nightly_portfolio_valuation": {
                    "task": "portfolio.save_daily_valuations",
                    "schedule": crontab(hour=valuation_hour, minute=valuation_minute),
                    "args": (),
                },
            })
    else:
        logger.info("EOD feature is disabled, no EOD beat schedule configured")
    
    # News planner task
    if settings.news_provider_fetch_enabled:
        logger.info(f"News planner beat schedule enabled: daily at {settings.news_planner_run_hour_local:02d}:{settings.news_planner_run_minute_local:02d}")
        
        schedule.update({
            "news_plan_daily": {
                "task": "news.plan_daily",
                "schedule": crontab(hour=settings.news_planner_run_hour_local, minute=settings.news_planner_run_minute_local),
                "args": (),
            }
        })
    else:
        logger.info("News provider fetch is disabled, no news planner beat schedule configured")
    
    return schedule


# Create Celery app
celery_app = Celery(
    "ai-portfolio",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/1",
    include=[
        "app.tasks.fetch_eod",
        "app.tasks.portfolio_valuation",
        "app.tasks.news_tasks",
        "app.tasks.news_fetch",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
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
# Import tasks to register them
from app.tasks import fetch_eod  # noqa
from app.tasks import portfolio_valuation
from app.tasks import news_tasks  # noqa
from app.tasks import news_fetch  # noqa  # noqa





