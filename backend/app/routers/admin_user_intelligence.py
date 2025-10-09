"""
Admin User Intelligence Router
Endpoints for viewing user portfolio, activity, usage stats, and quotas
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from uuid import UUID

from app.database import get_db
from app.dependencies import require_admin
from app.services.portfolio_analytics import PortfolioAnalytics
from app.services.usage_aggregator import UsageAggregator
from app.models.user_activity_log import UserActivityLog
from app.models.usage_metrics import UsageMetrics
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.admin.rate_limit import Quota
from app.models.user import User
from app.models.admin.plan import Plan
from sqlalchemy import select, and_, desc

router = APIRouter(prefix="/api/admin/v1", tags=["admin-user-intelligence"])


@router.get("/users/{user_id}/portfolio-summary", dependencies=[Depends(require_admin)])
async def get_user_portfolio_summary(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive portfolio summary for a user

    Returns:
    - Total portfolio value
    - Total invested amount
    - Total return percentage
    - Positions count
    - Allocation by asset class
    - Top 5 holdings
    """
    analytics = PortfolioAnalytics(db)

    try:
        summary = await analytics.calculate_portfolio_summary(user_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate portfolio summary: {str(e)}")


@router.get("/users/{user_id}/portfolio-history", dependencies=[Depends(require_admin)])
def get_user_portfolio_history(
    user_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get historical portfolio snapshots for charting

    Returns list of snapshots with:
    - Date
    - Total value
    - Total return percentage
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    snapshots = db.execute(
        select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.as_of >= start_date,
                PortfolioSnapshot.as_of <= end_date
            )
        ).order_by(PortfolioSnapshot.as_of)
    ).scalars().all()

    return [
        {
            'date': str(snap.as_of),
            'total_value': float(snap.total_value) if snap.total_value else 0,
            'total_return_pct': float(snap.total_return_pct) if snap.total_return_pct else 0,
            'positions_count': snap.positions_count,
            'allocation': snap.allocation or {}
        }
        for snap in snapshots
    ]


@router.get("/users/{user_id}/activity", dependencies=[Depends(require_admin)])
def get_user_activity(
    user_id: UUID,
    days: int = Query(default=7, ge=1, le=90),
    provider: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get user API activity logs

    Returns paginated list of:
    - Endpoint
    - Method
    - Status code
    - Response time
    - Provider
    - Timestamp
    """
    start_time = datetime.utcnow() - timedelta(days=days)

    query = select(UserActivityLog).where(
        and_(
            UserActivityLog.user_id == user_id,
            UserActivityLog.timestamp >= start_time
        )
    )

    if provider:
        query = query.where(UserActivityLog.provider == provider)

    query = query.order_by(desc(UserActivityLog.timestamp))
    query = query.limit(limit).offset(offset)

    activities = db.execute(query).scalars().all()

    # Get total count
    count_query = select(UserActivityLog).where(
        and_(
            UserActivityLog.user_id == user_id,
            UserActivityLog.timestamp >= start_time
        )
    )
    if provider:
        count_query = count_query.where(UserActivityLog.provider == provider)

    total_count = len(db.execute(count_query).scalars().all())

    return {
        'activities': [
            {
                'id': str(act.id),
                'endpoint': act.endpoint,
                'method': act.method,
                'status_code': act.status_code,
                'response_time_ms': act.response_time_ms,
                'provider': act.provider,
                'timestamp': act.timestamp.isoformat()
            }
            for act in activities
        ],
        'total': total_count,
        'limit': limit,
        'offset': offset
    }


@router.get("/users/{user_id}/usage-stats", dependencies=[Depends(require_admin)])
def get_user_usage_stats(
    user_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    provider: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Get aggregated usage statistics

    Returns:
    - Usage by provider (request counts, error rates)
    - Usage by date (time series data)
    - Total statistics
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    query = select(UsageMetrics).where(
        and_(
            UsageMetrics.user_id == user_id,
            UsageMetrics.metric_date >= start_date,
            UsageMetrics.metric_date <= end_date
        )
    )

    if provider:
        query = query.where(UsageMetrics.provider == provider)

    metrics = db.execute(query.order_by(UsageMetrics.metric_date)).scalars().all()

    # Group by provider
    by_provider = {}
    by_date = {}

    for metric in metrics:
        prov = metric.provider or 'unknown'

        if prov not in by_provider:
            by_provider[prov] = {
                'requests': 0,
                'errors': 0,
                'tokens': 0,
                'avg_response_time_ms': []
            }

        by_provider[prov]['requests'] += metric.request_count
        by_provider[prov]['errors'] += metric.error_count
        by_provider[prov]['tokens'] += metric.tokens_used

        if metric.avg_response_time_ms:
            by_provider[prov]['avg_response_time_ms'].append(metric.avg_response_time_ms)

        # Group by date
        date_str = str(metric.metric_date)
        if date_str not in by_date:
            by_date[date_str] = {
                'date': date_str,
                'requests': 0,
                'errors': 0
            }

        by_date[date_str]['requests'] += metric.request_count
        by_date[date_str]['errors'] += metric.error_count

    # Calculate average response times
    for prov_data in by_provider.values():
        if prov_data['avg_response_time_ms']:
            prov_data['avg_response_time_ms'] = int(sum(prov_data['avg_response_time_ms']) / len(prov_data['avg_response_time_ms']))
        else:
            prov_data['avg_response_time_ms'] = None

    # Sort by_date
    by_date_list = sorted(by_date.values(), key=lambda x: x['date'])

    return {
        'by_provider': by_provider,
        'by_date': by_date_list,
        'total_requests': sum(p['requests'] for p in by_provider.values()),
        'total_errors': sum(p['errors'] for p in by_provider.values()),
        'period_days': days
    }


@router.get("/users/{user_id}/quotas", dependencies=[Depends(require_admin)])
def get_user_quotas(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get user's plan limits and current usage quotas

    Returns:
    - Plan details
    - Quota usage per resource type
    - Percentage used
    """
    # Get user with plan
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan_info = None
    if user.plan_id:
        plan = db.execute(
            select(Plan).where(Plan.id == user.plan_id)
        ).scalar_one_or_none()

        if plan:
            plan_info = {
                'code': plan.code,
                'name': plan.name,
                'features': plan.features or {},
                'limits': plan.limits or {}
            }

    # Get active quotas for user
    quotas = db.execute(
        select(Quota).where(
            and_(
                Quota.scope == 'user',
                Quota.scope_id == str(user_id),
                Quota.is_enabled == True
            )
        )
    ).scalars().all()

    quota_list = [
        {
            'resource_type': q.resource_type,
            'period': q.period,
            'current_usage': q.current_usage,
            'hard_cap': q.hard_cap,
            'soft_cap': q.soft_cap,
            'usage_percentage': q.usage_percentage,
            'is_over_soft_cap': q.is_over_soft_cap,
            'is_over_hard_cap': q.is_over_hard_cap,
            'period_start': q.period_start.isoformat() if q.period_start else None,
            'period_end': q.period_end.isoformat() if q.period_end else None
        }
        for q in quotas
    ]

    return {
        'plan': plan_info,
        'quotas': quota_list
    }


@router.post("/users/{user_id}/portfolio-snapshot", dependencies=[Depends(require_admin)])
async def create_user_portfolio_snapshot(
    user_id: UUID,
    as_of: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Manually trigger portfolio snapshot creation for a user

    Useful for testing or backfilling data
    """
    analytics = PortfolioAnalytics(db)

    try:
        snapshot = await analytics.create_portfolio_snapshot(user_id, as_of)

        return {
            'id': str(snapshot.id),
            'user_id': str(snapshot.user_id),
            'as_of': str(snapshot.as_of),
            'total_value': float(snapshot.total_value) if snapshot.total_value else 0,
            'total_return_pct': float(snapshot.total_return_pct) if snapshot.total_return_pct else 0,
            'positions_count': snapshot.positions_count,
            'created_at': snapshot.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create snapshot: {str(e)}")
