"""Create admin tables for configuration management

Revision ID: admin_001
Revises: rbac_001
Create Date: 2025-10-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'admin_001'
down_revision = 'rbac_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== API PROVIDERS ====================
    op.create_table(
        'api_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('type', sa.String(50), nullable=False, comment='news, crypto, llm, eod'),
        sa.Column('name', sa.String(100), nullable=False, unique=True, comment='binance, newsapi, ollama'),
        sa.Column('base_url', sa.String(500), nullable=True),
        sa.Column('is_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('is_shadow_mode', sa.Boolean, nullable=False, default=False, comment='Test without using results'),
        sa.Column('priority', sa.Integer, nullable=False, default=100, comment='Lower = higher priority'),
        sa.Column('timeout_seconds', sa.Integer, nullable=False, default=10),
        sa.Column('meta', postgresql.JSONB, nullable=True, server_default='{}', comment='Provider-specific config'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_deleted', sa.Boolean, nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_api_providers_type', 'api_providers', ['type'])
    op.create_index('ix_api_providers_enabled', 'api_providers', ['is_enabled', 'is_deleted'])
    op.create_index('ix_api_providers_priority', 'api_providers', ['priority'])

    # ==================== API CREDENTIALS ====================
    op.create_table(
        'api_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_name', sa.String(100), nullable=False, comment='OPENAI_API_KEY, FINNHUB_API_KEY'),
        sa.Column('masked_key', sa.String(100), nullable=True, comment='sk-...abc123'),
        sa.Column('encrypted_key', sa.Text, nullable=True, comment='Encrypted actual key'),
        sa.Column('status', sa.String(20), nullable=False, default='active', comment='active, expired, invalid'),
        sa.Column('last_check_at', sa.DateTime(), nullable=True),
        sa.Column('last_check_status', sa.String(20), nullable=True, comment='success, failure'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_deleted', sa.Boolean, nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['api_providers.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_api_credentials_provider', 'api_credentials', ['provider_id'])
    op.create_index('ix_api_credentials_status', 'api_credentials', ['status', 'is_deleted'])

    # ==================== RATE LIMITS ====================
    op.create_table(
        'rate_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('scope', sa.String(100), nullable=False, comment='user, plan, provider, endpoint, global'),
        sa.Column('scope_id', sa.String(200), nullable=True, comment='user_id, provider_name, endpoint_path'),
        sa.Column('window_seconds', sa.Integer, nullable=False, comment='Time window for limit'),
        sa.Column('limit', sa.Integer, nullable=False, comment='Max requests in window'),
        sa.Column('burst', sa.Integer, nullable=True, comment='Burst allowance'),
        sa.Column('policy', sa.String(50), nullable=False, default='reject', comment='reject, queue, throttle'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_rate_limits_scope', 'rate_limits', ['scope', 'scope_id'])
    op.create_index('ix_rate_limits_enabled', 'rate_limits', ['is_enabled'])

    # Composite unique constraint
    op.create_index('idx_rate_limit_unique', 'rate_limits', ['scope', 'scope_id'], unique=True)

    # ==================== QUOTAS ====================
    op.create_table(
        'quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('scope', sa.String(100), nullable=False, comment='user, plan, provider, resource'),
        sa.Column('scope_id', sa.String(200), nullable=True),
        sa.Column('resource_type', sa.String(100), nullable=False, comment='llm_tokens, api_calls, storage'),
        sa.Column('period', sa.String(20), nullable=False, comment='hour, day, month'),
        sa.Column('hard_cap', sa.BigInteger, nullable=False, comment='Absolute limit'),
        sa.Column('soft_cap', sa.BigInteger, nullable=True, comment='Warning threshold'),
        sa.Column('current_usage', sa.BigInteger, nullable=False, default=0),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('action_on_breach', sa.String(50), nullable=False, default='block', comment='block, notify, throttle'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_quotas_scope', 'quotas', ['scope', 'scope_id', 'resource_type'])
    op.create_index('ix_quotas_period', 'quotas', ['period_start', 'period_end'])
    op.create_index('ix_quotas_enabled', 'quotas', ['is_enabled'])

    # ==================== PLANS ====================
    op.create_table(
        'plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('code', sa.String(50), nullable=False, unique=True, comment='free, pro, enterprise'),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('features', postgresql.JSONB, nullable=False, server_default='{}', comment='Feature flags'),
        sa.Column('limits', postgresql.JSONB, nullable=False, server_default='{}', comment='Rate limits & quotas'),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_plans_code', 'plans', ['code'])
    op.create_index('ix_plans_active', 'plans', ['is_active'])

    # ==================== FEATURE FLAGS ====================
    op.create_table(
        'feature_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('key', sa.String(100), nullable=False, unique=True, comment='EOD_ENABLE, NEWS_ENABLE'),
        sa.Column('value_type', sa.String(20), nullable=False, default='boolean', comment='boolean, string, json, number'),
        sa.Column('value_boolean', sa.Boolean, nullable=True),
        sa.Column('value_string', sa.Text, nullable=True),
        sa.Column('value_json', postgresql.JSONB, nullable=True),
        sa.Column('value_number', sa.Numeric, nullable=True),
        sa.Column('env_scope', sa.String(50), nullable=False, default='all', comment='all, production, staging, dev'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_feature_flags_key', 'feature_flags', ['key'])
    op.create_index('ix_feature_flags_enabled', 'feature_flags', ['is_enabled', 'env_scope'])

    # ==================== SCHEDULES ====================
    op.create_table(
        'schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('task_name', sa.String(200), nullable=False, unique=True, comment='prices.run_eod_refresh'),
        sa.Column('task_type', sa.String(50), nullable=False, default='celery', comment='celery, cron, manual'),
        sa.Column('cron_expression', sa.String(100), nullable=True, comment='30 23 * * *'),
        sa.Column('timezone', sa.String(50), nullable=False, default='UTC'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_status', sa.String(20), nullable=True, comment='success, failure, timeout'),
        sa.Column('last_run_duration_ms', sa.Integer, nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('payload', postgresql.JSONB, nullable=True, server_default='{}', comment='Task parameters'),
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('max_retries', sa.Integer, nullable=False, default=3),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_schedules_task_name', 'schedules', ['task_name'])
    op.create_index('ix_schedules_enabled', 'schedules', ['is_enabled'])
    op.create_index('ix_schedules_next_run', 'schedules', ['next_run_at', 'is_enabled'])

    # ==================== CACHE POLICIES ====================
    op.create_table(
        'cache_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('dataset', sa.String(100), nullable=False, unique=True, comment='news, prices, insights'),
        sa.Column('ttl_seconds', sa.Integer, nullable=False, comment='Time to live'),
        sa.Column('swr_enabled', sa.Boolean, nullable=False, default=False, comment='Stale-while-revalidate'),
        sa.Column('swr_stale_seconds', sa.Integer, nullable=True, comment='How long to serve stale'),
        sa.Column('swr_refresh_threshold', sa.Integer, nullable=True, comment='When to trigger refresh'),
        sa.Column('etag_enabled', sa.Boolean, nullable=False, default=False),
        sa.Column('ims_enabled', sa.Boolean, nullable=False, default=False, comment='If-Modified-Since'),
        sa.Column('purge_allowed', sa.Boolean, nullable=False, default=True),
        sa.Column('compression_enabled', sa.Boolean, nullable=False, default=False),
        sa.Column('circuit_breaker_enabled', sa.Boolean, nullable=False, default=False),
        sa.Column('circuit_breaker_threshold', sa.Integer, nullable=True, default=3),
        sa.Column('circuit_breaker_window_seconds', sa.Integer, nullable=True, default=300),
        sa.Column('circuit_breaker_recovery_seconds', sa.Integer, nullable=True, default=600),
        sa.Column('meta', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_cache_policies_dataset', 'cache_policies', ['dataset'])

    # ==================== AUDIT LOG ====================
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True, comment='User who made change'),
        sa.Column('actor_type', sa.String(50), nullable=False, default='user', comment='user, system, api'),
        sa.Column('action', sa.String(100), nullable=False, comment='create, update, delete, enable, disable'),
        sa.Column('entity_type', sa.String(100), nullable=False, comment='feature_flag, api_provider, schedule'),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('entity_name', sa.String(200), nullable=True, comment='Human-readable name'),
        sa.Column('before_state', postgresql.JSONB, nullable=True, comment='State before change'),
        sa.Column('after_state', postgresql.JSONB, nullable=True, comment='State after change'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()'), index=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_audit_log_actor', 'audit_log', ['actor_id', 'timestamp'])
    op.create_index('ix_audit_log_entity', 'audit_log', ['entity_type', 'entity_id', 'timestamp'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action', 'timestamp'])
    op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])

    # ==================== SYSTEM SETTINGS ====================
    # Generic key-value store for system-wide settings
    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('category', sa.String(100), nullable=False, comment='database, celery, redis, general'),
        sa.Column('key', sa.String(200), nullable=False, comment='pool_size, timezone, max_connections'),
        sa.Column('value_type', sa.String(20), nullable=False, default='string', comment='string, number, boolean, json'),
        sa.Column('value', sa.Text, nullable=True),
        sa.Column('value_json', postgresql.JSONB, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_secret', sa.Boolean, nullable=False, default=False, comment='Mask in UI'),
        sa.Column('validation_regex', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_system_settings_category', 'system_settings', ['category'])
    op.create_index('idx_system_settings_unique', 'system_settings', ['category', 'key'], unique=True)

    # ==================== SEED DEFAULT DATA ====================

    # Seed default plans
    op.execute("""
        INSERT INTO plans (id, code, name, description, features, limits, is_active) VALUES
        (
            gen_random_uuid(),
            'free',
            'Free Plan',
            'Basic features for individual users',
            '{"eod_enabled": true, "news_enabled": false, "crypto_enabled": false}',
            '{"api_calls_per_day": 100, "llm_tokens_per_day": 1000}',
            true
        ),
        (
            gen_random_uuid(),
            'pro',
            'Pro Plan',
            'Advanced features for power users',
            '{"eod_enabled": true, "news_enabled": true, "crypto_enabled": true}',
            '{"api_calls_per_day": 1000, "llm_tokens_per_day": 10000}',
            true
        )
    """)

    # Seed default feature flags from discovery.md
    op.execute("""
        INSERT INTO feature_flags (id, key, value_type, value_boolean, env_scope, description, is_enabled) VALUES
        (gen_random_uuid(), 'EOD_ENABLE', 'boolean', false, 'all', 'Enable End-of-Day pipeline', true),
        (gen_random_uuid(), 'NEWS_ENABLE', 'boolean', false, 'all', 'Enable news aggregation', true),
        (gen_random_uuid(), 'FEATURE_CRYPTO_POSITIONS', 'boolean', false, 'all', 'Enable cryptocurrency positions', true),
        (gen_random_uuid(), 'NEWS_CACHE_ENABLED', 'boolean', true, 'all', 'Enable news caching', true),
        (gen_random_uuid(), 'NEWS_READ_CACHE_ENABLED', 'boolean', true, 'all', 'Enable news read cache', true),
        (gen_random_uuid(), 'NEWS_PROVIDER_FETCH_ENABLED', 'boolean', false, 'all', 'Enable active news fetching', true),
        (gen_random_uuid(), 'NEWS_PROVIDER_SHADOW_MODE', 'boolean', true, 'all', 'Test news providers without using results', true)
    """)

    # Seed default cache policies
    op.execute("""
        INSERT INTO cache_policies (id, dataset, ttl_seconds, swr_enabled, swr_stale_seconds, swr_refresh_threshold) VALUES
        (gen_random_uuid(), 'news', 300, false, null, null),
        (gen_random_uuid(), 'crypto_prices', 60, false, null, null),
        (gen_random_uuid(), 'insights', 86400, true, 7200, 900),
        (gen_random_uuid(), 'eod_prices', 3600, false, null, null)
    """)

    # Seed default API providers
    op.execute("""
        INSERT INTO api_providers (id, type, name, base_url, is_enabled, priority, timeout_seconds) VALUES
        (gen_random_uuid(), 'news', 'newsapi', 'https://newsapi.org', true, 1, 10),
        (gen_random_uuid(), 'news', 'finnhub', 'https://finnhub.io', false, 2, 10),
        (gen_random_uuid(), 'news', 'alphavantage', 'https://www.alphavantage.co', false, 3, 10),
        (gen_random_uuid(), 'crypto', 'binance', 'https://api.binance.com', true, 1, 10),
        (gen_random_uuid(), 'crypto', 'coingecko', 'https://api.coingecko.com', true, 2, 10),
        (gen_random_uuid(), 'llm', 'ollama', 'http://localhost:11434', true, 1, 30),
        (gen_random_uuid(), 'llm', 'openai', 'https://api.openai.com', false, 2, 30)
    """)


def downgrade():
    """Rollback admin tables"""
    op.drop_table('system_settings')
    op.drop_table('audit_log')
    op.drop_table('cache_policies')
    op.drop_table('schedules')
    op.drop_table('feature_flags')
    op.drop_table('plans')
    op.drop_table('quotas')
    op.drop_table('rate_limits')
    op.drop_table('api_credentials')
    op.drop_table('api_providers')
