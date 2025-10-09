"""
Celery tasks for news planning and fetching.

This module provides Celery tasks for daily news planning and fetching
with quota management and idempotency.
"""

import logging
from datetime import date
from typing import Dict, Any, List

from app.celery_app import celery_app
from app.scheduling.news_planner import (
    plan_daily_news, 
    is_query_planned, 
    mark_query_planned,
    get_planning_stats
)
from app.core.config import settings
from app.database import SessionLocal
from app.services.news_config import get_flags

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2})
def plan_daily(self, fetch_date: str = None) -> Dict[str, Any]:
    """
    Daily news planning task.
    
    Plans which symbols to fetch news for based on portfolio weights
    and news drought analysis, then enqueues fetch tasks.
    
    Args:
        fetch_date: Date string in YYYY-MM-DD format (defaults to today)
        
    Returns:
        Dict with planning results and enqueued tasks info
    """
    try:
        # Check if news fetching is enabled (from DB config instead of env)
        db = SessionLocal()
        try:
            flags = get_flags(db)
            fetch_enabled = flags.get("provider_fetch_enabled", settings.news_provider_fetch_enabled)
        finally:
            db.close()
        
        if not fetch_enabled:
            logger.info("News provider fetch is disabled, skipping daily planning")
            return {
                "status": "skipped",
                "reason": "NEWS_PROVIDER_FETCH_ENABLED is False",
                "fetch_date": fetch_date or date.today().isoformat()
            }
        
        # Parse fetch date
        if fetch_date:
            try:
                target_date = date.fromisoformat(fetch_date)
            except ValueError:
                logger.error(f"Invalid fetch_date format: {fetch_date}")
                return {
                    "status": "error",
                    "error": f"Invalid fetch_date format: {fetch_date}",
                    "fetch_date": fetch_date
                }
        else:
            target_date = date.today()
        
        logger.info(f"Starting daily news planning for {target_date}")
        
        # Plan daily news
        planned_queries = plan_daily_news(target_date)
        
        if not planned_queries:
            logger.warning("No queries planned for daily news")
            return {
                "status": "success",
                "planned_queries": 0,
                "enqueued_tasks": 0,
                "fetch_date": target_date.isoformat(),
                "reason": "No symbols found in portfolio"
            }
        
        # Enqueue fetch tasks with idempotency
        enqueued_count = 0
        skipped_count = 0
        
        for planned_query in planned_queries:
            # Check if already planned (idempotency)
            if is_query_planned(target_date, planned_query.provider, planned_query.symbol, planned_query.query):
                logger.debug(f"Query already planned, skipping: {planned_query.symbol}")
                skipped_count += 1
                continue
            
            # Mark as planned
            if not mark_query_planned(target_date, planned_query.provider, planned_query.symbol, planned_query.query):
                logger.debug(f"Failed to mark query as planned, skipping: {planned_query.symbol}")
                skipped_count += 1
                continue
            
            # Enqueue fetch task
            try:
                from app.tasks.news_fetch import fetch_news
                fetch_news.delay(
                    provider=planned_query.provider,
                    symbol=planned_query.symbol,
                    query=planned_query.query
                )
                enqueued_count += 1
                logger.debug(f"Enqueued fetch task for {planned_query.symbol} (priority: {planned_query.priority:.3f})")
                
            except Exception as e:
                logger.error(f"Failed to enqueue fetch task for {planned_query.symbol}: {e}")
                skipped_count += 1
        
        logger.info(f"Daily planning completed: {enqueued_count} tasks enqueued, {skipped_count} skipped")
        
        return {
            "status": "success",
            "planned_queries": len(planned_queries),
            "enqueued_tasks": enqueued_count,
            "skipped_tasks": skipped_count,
            "fetch_date": target_date.isoformat(),
            "provider": settings.news_provider_default,
            "daily_limit": settings.news_daily_limit,
            "daily_symbols": settings.news_daily_symbols
        }
        
    except Exception as e:
        logger.error(f"Daily planning task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes




@celery_app.task(bind=True)
def get_planning_status(self, fetch_date: str = None) -> Dict[str, Any]:
    """
    Get planning status for a specific date.
    
    Args:
        fetch_date: Date string in YYYY-MM-DD format (defaults to today)
        
    Returns:
        Dict with planning statistics
    """
    try:
        if fetch_date:
            try:
                target_date = date.fromisoformat(fetch_date)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid fetch_date format: {fetch_date}"
                }
        else:
            target_date = date.today()
        
        stats = get_planning_stats(target_date)
        
        return {
            "status": "success",
            "fetch_date": target_date.isoformat(),
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Planning status task failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "fetch_date": fetch_date or date.today().isoformat()
        }


@celery_app.task(bind=True)
def clear_planning_data(self, fetch_date: str = None) -> Dict[str, Any]:
    """
    Clear planning data for a specific date (for testing/debugging).
    
    Args:
        fetch_date: Date string in YYYY-MM-DD format (defaults to today)
        
    Returns:
        Dict with clearing results
    """
    try:
        if fetch_date:
            try:
                target_date = date.fromisoformat(fetch_date)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid fetch_date format: {fetch_date}"
                }
        else:
            target_date = date.today()
        
        from app.scheduling.news_planner import clear_planning_data
        cleared_count = clear_planning_data(target_date)
        
        logger.info(f"Cleared {cleared_count} planning entries for {target_date}")
        
        return {
            "status": "success",
            "fetch_date": target_date.isoformat(),
            "cleared_entries": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Clear planning data task failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "fetch_date": fetch_date or date.today().isoformat()
        }
