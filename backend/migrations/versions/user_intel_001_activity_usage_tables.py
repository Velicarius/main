"""Create user intelligence tables for activity tracking, usage metrics, and portfolio analytics

Revision ID: user_intel_001
Revises: f7a62a0df058
Create Date: 2025-10-09

This migration adds:
- user_activity_log: Track all user API calls per request
- usage_metrics: Aggregated daily usage statistics per user/provider
- portfolio_snapshots: Calculated portfolio metrics and returns
- users.plan_id: Link users to subscription plans
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'user_intel_001'
down_revision = 'f7a62a0df058'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== USER ACTIVITY LOG ====================
    # Tracks every API call made by users for auditing and usage analysis
    op.create_table(
        'user_activity_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='User who made the request'),
        sa.Column('endpoint', sa.String(500), nullable=False, comment='API endpoint path'),
        sa.Column('method', sa.String(10), nullable=False, comment='HTTP method: GET, POST, PUT, DELETE'),
        sa.Column('status_code', sa.Integer, nullable=True, comment='HTTP response status'),
        sa.Column('response_time_ms', sa.Integer, nullable=True, comment='Response time in milliseconds'),
        sa.Column('provider', sa.String(100), nullable=True, comment='API provider used: newsapi, ollama, binance, etc'),
        sa.Column('request_metadata', postgresql.JSONB, nullable=True, default={}, comment='Additional request context'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()'), comment='When request was made'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Indexes for efficient querying
    op.create_index('ix_activity_user_ts', 'user_activity_log', ['user_id', 'timestamp'])
    op.create_index('ix_activity_provider', 'user_activity_log', ['provider', 'timestamp'])
    op.create_index('ix_activity_endpoint', 'user_activity_log', ['endpoint'])
    op.create_index('ix_activity_timestamp', 'user_activity_log', ['timestamp'])

    # ==================== USAGE METRICS ====================
    # Aggregated daily statistics per user/provider for reporting
    op.create_table(
        'usage_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='User ID'),
        sa.Column('provider', sa.String(100), nullable=True, comment='API provider: newsapi, ollama, binance'),
        sa.Column('endpoint', sa.String(500), nullable=True, comment='Specific endpoint or NULL for provider total'),
        sa.Column('metric_date', sa.Date(), nullable=False, comment='Date of aggregated metrics'),
        sa.Column('request_count', sa.Integer, nullable=False, default=0, comment='Total requests made'),
        sa.Column('tokens_used', sa.BigInteger, nullable=False, default=0, comment='Total tokens consumed (for LLM providers)'),
        sa.Column('error_count', sa.Integer, nullable=False, default=0, comment='Number of failed requests'),
        sa.Column('avg_response_time_ms', sa.Integer, nullable=True, comment='Average response time'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )

    # Unique constraint to prevent duplicate daily metrics
    op.create_index(
        'idx_usage_unique',
        'usage_metrics',
        ['user_id', 'provider', 'endpoint', 'metric_date'],
        unique=True
    )

    # Indexes for queries
    op.create_index('ix_usage_user_date', 'usage_metrics', ['user_id', 'metric_date'])
    op.create_index('ix_usage_provider', 'usage_metrics', ['provider', 'metric_date'])

    # ==================== PORTFOLIO SNAPSHOTS ====================
    # Calculated portfolio metrics and analytics
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='User ID'),
        sa.Column('as_of', sa.Date(), nullable=False, comment='Snapshot date'),
        sa.Column('total_value', sa.Numeric(20, 8), nullable=True, comment='Total portfolio value'),
        sa.Column('total_invested', sa.Numeric(20, 8), nullable=True, comment='Total amount invested'),
        sa.Column('total_return_pct', sa.Numeric(10, 4), nullable=True, comment='Total return percentage'),
        sa.Column('positions_count', sa.Integer, nullable=False, default=0, comment='Number of positions'),
        sa.Column('allocation', postgresql.JSONB, nullable=True, default={}, comment='Allocation by asset class: {"EQUITY": 60, "CRYPTO": 40}'),
        sa.Column('risk_metrics', postgresql.JSONB, nullable=True, default={}, comment='Risk metrics: volatility, sharpe, etc'),
        sa.Column('top_holdings', postgresql.JSONB, nullable=True, default=[], comment='Top 5 positions by value'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )

    # Unique constraint per user per date
    op.create_index(
        'idx_portfolio_snapshot_unique',
        'portfolio_snapshots',
        ['user_id', 'as_of'],
        unique=True
    )

    # Indexes
    op.create_index('ix_snapshot_user_date', 'portfolio_snapshots', ['user_id', 'as_of'])
    op.create_index('ix_snapshot_date', 'portfolio_snapshots', ['as_of'])

    # ==================== ADD PLAN_ID TO USERS ====================
    # Link users to their subscription plan
    op.add_column('users', sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id', ondelete='SET NULL'), nullable=True, comment='User subscription plan'))
    op.create_index('ix_users_plan', 'users', ['plan_id'])

    # Set default plan for existing users (free plan)
    op.execute("""
        UPDATE users
        SET plan_id = (SELECT id FROM plans WHERE code = 'free' LIMIT 1)
        WHERE plan_id IS NULL
    """)


def downgrade():
    """Rollback changes"""
    # Remove plan_id from users
    op.drop_index('ix_users_plan', table_name='users')
    op.drop_column('users', 'plan_id')

    # Drop portfolio_snapshots
    op.drop_index('ix_snapshot_date', table_name='portfolio_snapshots')
    op.drop_index('ix_snapshot_user_date', table_name='portfolio_snapshots')
    op.drop_index('idx_portfolio_snapshot_unique', table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')

    # Drop usage_metrics
    op.drop_index('ix_usage_provider', table_name='usage_metrics')
    op.drop_index('ix_usage_user_date', table_name='usage_metrics')
    op.drop_index('idx_usage_unique', table_name='usage_metrics')
    op.drop_table('usage_metrics')

    # Drop user_activity_log
    op.drop_index('ix_activity_timestamp', table_name='user_activity_log')
    op.drop_index('ix_activity_endpoint', table_name='user_activity_log')
    op.drop_index('ix_activity_provider', table_name='user_activity_log')
    op.drop_index('ix_activity_user_ts', table_name='user_activity_log')
    op.drop_table('user_activity_log')
