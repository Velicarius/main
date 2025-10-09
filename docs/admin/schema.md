# Admin Database Schema Documentation

**Generated:** 2025-10-08
**Migration:** `admin_001_create_admin_tables.py`
**Status:** Ready for deployment

---

## 📊 Entity Relationship Diagram

```mermaid
erDiagram
    API_PROVIDERS ||--o{ API_CREDENTIALS : has
    API_PROVIDERS {
        uuid id PK
        string type "news, crypto, llm, eod"
        string name UK
        string base_url
        boolean is_enabled
        boolean is_shadow_mode
        int priority
        int timeout_seconds
        jsonb meta
        timestamp created_at
        timestamp updated_at
        boolean is_deleted
        timestamp deleted_at
    }

    API_CREDENTIALS {
        uuid id PK
        uuid provider_id FK
        string key_name
        string masked_key
        text encrypted_key
        string status "active, expired, invalid"
        timestamp last_check_at
        string last_check_status
        timestamp expires_at
        text notes
        timestamp created_at
        timestamp updated_at
        boolean is_deleted
        timestamp deleted_at
    }

    RATE_LIMITS {
        uuid id PK
        string scope UK1 "user, plan, provider, endpoint, global"
        string scope_id UK1
        int window_seconds
        int limit
        int burst
        string policy "reject, queue, throttle"
        boolean is_enabled
        timestamp created_at
        timestamp updated_at
    }

    QUOTAS {
        uuid id PK
        string scope "user, plan, provider, resource"
        string scope_id
        string resource_type "llm_tokens, api_calls, storage"
        string period "hour, day, month"
        bigint hard_cap
        bigint soft_cap
        bigint current_usage
        timestamp period_start
        timestamp period_end
        string action_on_breach "block, notify, throttle"
        boolean is_enabled
        timestamp created_at
        timestamp updated_at
    }

    PLANS {
        uuid id PK
        string code UK "free, pro, enterprise"
        string name
        text description
        jsonb features
        jsonb limits
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    FEATURE_FLAGS {
        uuid id PK
        string key UK "EOD_ENABLE, NEWS_ENABLE"
        string value_type "boolean, string, json, number"
        boolean value_boolean
        text value_string
        jsonb value_json
        numeric value_number
        string env_scope "all, production, staging, dev"
        text description
        boolean is_enabled
        timestamp created_at
        timestamp updated_at
    }

    SCHEDULES {
        uuid id PK
        string task_name UK "prices.run_eod_refresh"
        string task_type "celery, cron, manual"
        string cron_expression "30 23 * * *"
        string timezone
        boolean is_enabled
        timestamp last_run_at
        string last_run_status "success, failure, timeout"
        int last_run_duration_ms
        timestamp next_run_at
        jsonb payload
        int retry_count
        int max_retries
        timestamp created_at
        timestamp updated_at
    }

    CACHE_POLICIES {
        uuid id PK
        string dataset UK "news, prices, insights"
        int ttl_seconds
        boolean swr_enabled
        int swr_stale_seconds
        int swr_refresh_threshold
        boolean etag_enabled
        boolean ims_enabled
        boolean purge_allowed
        boolean compression_enabled
        boolean circuit_breaker_enabled
        int circuit_breaker_threshold
        int circuit_breaker_window_seconds
        int circuit_breaker_recovery_seconds
        jsonb meta
        timestamp created_at
        timestamp updated_at
    }

    USERS ||--o{ AUDIT_LOG : performs
    AUDIT_LOG {
        uuid id PK
        uuid actor_id FK
        string actor_type "user, system, api"
        string action "create, update, delete, enable, disable"
        string entity_type "feature_flag, api_provider, schedule"
        uuid entity_id
        string entity_name
        jsonb before_state
        jsonb after_state
        timestamp timestamp
        string ip_address
        string user_agent
        string request_id
        jsonb metadata
    }

    SYSTEM_SETTINGS {
        uuid id PK
        string category UK1 "database, celery, redis, general"
        string key UK1
        string value_type "string, number, boolean, json"
        text value
        jsonb value_json
        text description
        boolean is_secret
        string validation_regex
        timestamp created_at
        timestamp updated_at
    }
```

---

## 📋 Table Descriptions

### 1. api_providers

**Purpose:** Configuration for external service providers

**Primary Use Cases:**
- Manage news providers (NewsAPI, Finnhub, AlphaVantage)
- Configure crypto price providers (Binance, CoinGecko)
- Set up LLM providers (OpenAI, Ollama)
- Enable/disable providers dynamically
- Shadow mode testing

**Key Fields:**
- `is_shadow_mode`: Test provider without using results
- `priority`: Lower number = higher priority for failover
- `meta`: Provider-specific config (rate limits, special headers, etc.)

**Example:**
```json
{
  "type": "news",
  "name": "newsapi",
  "base_url": "https://newsapi.org",
  "is_enabled": true,
  "priority": 1,
  "timeout_seconds": 10,
  "meta": {
    "rate_limit_per_day": 100,
    "supported_categories": ["business", "technology"]
  }
}
```

---

### 2. api_credentials

**Purpose:** Secure storage of API keys with encryption and masking

**Primary Use Cases:**
- Store encrypted API keys
- Track key expiration
- Monitor key health
- Mask keys in UI (show only `sk-...abc123`)

**Key Fields:**
- `masked_key`: Safe to display (e.g., `sk-...abc123`)
- `encrypted_key`: Actual key (encrypted at rest)
- `last_check_status`: Result of last health check

**Security:**
- Keys should be encrypted using Fernet or similar
- Never log `encrypted_key`
- Rotate keys regularly

---

### 3. rate_limits

**Purpose:** Request rate limiting per scope

**Primary Use Cases:**
- Limit API calls per user
- Protect admin endpoints
- Provider-specific rate limits
- Global API throttling

**Scopes:**
- `user`: Per-user limits
- `plan`: Plan-based limits (free/pro)
- `provider`: Provider API limits
- `endpoint`: Specific endpoint limits
- `global`: System-wide limits

**Example:**
```json
{
  "scope": "endpoint",
  "scope_id": "/admin/tasks/fetch-eod",
  "window_seconds": 60,
  "limit": 10,
  "burst": 2,
  "policy": "reject"
}
```

---

### 4. quotas

**Purpose:** Resource usage tracking and limits

**Primary Use Cases:**
- Track LLM token usage
- Monitor API call quotas
- Storage limits
- Per-user/plan resource caps

**Key Fields:**
- `current_usage`: Incremented on each use
- `soft_cap`: Warning threshold
- `hard_cap`: Hard stop
- `period_start`/`period_end`: Quota reset window

**Example:**
```json
{
  "scope": "user",
  "scope_id": "user-uuid",
  "resource_type": "llm_tokens",
  "period": "day",
  "hard_cap": 10000,
  "soft_cap": 8000,
  "current_usage": 5230,
  "action_on_breach": "block"
}
```

---

### 5. plans

**Purpose:** Subscription tier configuration

**Primary Use Cases:**
- Define free/pro/enterprise features
- Set plan-specific limits
- Feature flag overrides per plan

**Features JSONB:**
```json
{
  "eod_enabled": true,
  "news_enabled": true,
  "crypto_enabled": true,
  "max_portfolios": 5
}
```

**Limits JSONB:**
```json
{
  "api_calls_per_day": 1000,
  "llm_tokens_per_day": 10000,
  "storage_mb": 500
}
```

---

### 6. feature_flags

**Purpose:** Runtime feature toggles

**Primary Use Cases:**
- Enable/disable features without deployment
- A/B testing
- Gradual rollouts
- Environment-specific features

**Value Types:**
- `boolean`: Simple on/off
- `string`: Config strings
- `json`: Complex configuration
- `number`: Numeric thresholds

**Example:**
```json
{
  "key": "NEWS_ENABLE",
  "value_type": "boolean",
  "value_boolean": true,
  "env_scope": "production",
  "description": "Enable news aggregation",
  "is_enabled": true
}
```

---

### 7. schedules

**Purpose:** Celery task scheduling

**Primary Use Cases:**
- EOD refresh schedule
- News fetching schedule
- Portfolio valuation tasks
- Manual admin triggers

**Example:**
```json
{
  "task_name": "prices.run_eod_refresh",
  "task_type": "celery",
  "cron_expression": "30 23 * * *",
  "timezone": "Europe/Warsaw",
  "is_enabled": true,
  "max_retries": 3,
  "payload": {
    "symbols": ["AAPL", "GOOGL"]
  }
}
```

---

### 8. cache_policies

**Purpose:** Cache configuration per dataset

**Primary Use Cases:**
- TTL management
- Stale-While-Revalidate (SWR)
- Circuit breaker configuration
- HTTP caching (ETag, If-Modified-Since)

**SWR Example:**
```json
{
  "dataset": "insights",
  "ttl_seconds": 86400,
  "swr_enabled": true,
  "swr_stale_seconds": 7200,
  "swr_refresh_threshold": 900,
  "circuit_breaker_enabled": true,
  "circuit_breaker_threshold": 3
}
```

**Explanation:**
- Fresh for 24h (`ttl_seconds`)
- Serve stale for 2h while revalidating (`swr_stale_seconds`)
- Trigger refresh 15min before expiry (`swr_refresh_threshold`)

---

### 9. audit_log

**Purpose:** Immutable audit trail

**Primary Use Cases:**
- Track all admin changes
- Security auditing
- Compliance (GDPR, SOC2)
- Debugging configuration issues

**Tracked Actions:**
- `create`, `update`, `delete`
- `enable`, `disable`
- `assign_role`, `remove_role`

**Example:**
```json
{
  "actor_id": "admin-user-uuid",
  "action": "update",
  "entity_type": "feature_flag",
  "entity_id": "flag-uuid",
  "entity_name": "NEWS_ENABLE",
  "before_state": {"value_boolean": false},
  "after_state": {"value_boolean": true},
  "timestamp": "2025-10-08T10:30:00Z",
  "ip_address": "192.168.1.100"
}
```

---

### 10. system_settings

**Purpose:** Generic key-value configuration

**Primary Use Cases:**
- Database pool settings
- Celery worker config
- Redis connection settings
- Timezone, locale settings

**Categories:**
- `database`: Connection pool, timeouts
- `celery`: Worker count, retry policy
- `redis`: Max connections, timeout
- `general`: Timezone, debug mode

**Example:**
```json
{
  "category": "celery",
  "key": "worker_prefetch_multiplier",
  "value_type": "number",
  "value": "1",
  "description": "How many tasks each worker prefetches",
  "is_secret": false
}
```

---

## 🔒 Security Considerations

### 1. Soft Delete Pattern
**Tables with soft delete:**
- `api_providers`
- `api_credentials`

**Reason:** Preserve audit trail and prevent cascading data loss

### 2. Foreign Key Cascade Rules

| Relationship | On Delete | Reason |
|--------------|-----------|---------|
| `api_credentials.provider_id → api_providers.id` | CASCADE | Delete credentials when provider is deleted |
| `audit_log.actor_id → users.id` | SET NULL | Preserve audit log even if user deleted |

### 3. Encryption
**Fields requiring encryption:**
- `api_credentials.encrypted_key`

**Recommended:** Use `cryptography.fernet` with key stored in ENV

### 4. Masking
**Fields to mask in UI/logs:**
- `api_credentials.encrypted_key` (never show)
- `api_credentials.masked_key` (show as `sk-...abc123`)
- `system_settings.value` (if `is_secret = true`)

---

## 📈 Indexing Strategy

### High-Traffic Queries

```sql
-- Find enabled providers by type
SELECT * FROM api_providers
WHERE type = 'news' AND is_enabled = true AND is_deleted = false
ORDER BY priority;
-- Index: ix_api_providers_type, ix_api_providers_enabled, ix_api_providers_priority

-- Check rate limit
SELECT * FROM rate_limits
WHERE scope = 'user' AND scope_id = 'user-uuid' AND is_enabled = true;
-- Index: ix_rate_limits_scope, idx_rate_limit_unique

-- Get feature flag
SELECT * FROM feature_flags
WHERE key = 'NEWS_ENABLE' AND is_enabled = true;
-- Index: ix_feature_flags_key (unique)

-- Audit log by entity
SELECT * FROM audit_log
WHERE entity_type = 'feature_flag' AND entity_id = 'flag-uuid'
ORDER BY timestamp DESC;
-- Index: ix_audit_log_entity

-- Audit log by actor
SELECT * FROM audit_log
WHERE actor_id = 'user-uuid'
ORDER BY timestamp DESC
LIMIT 100;
-- Index: ix_audit_log_actor
```

---

## 🚀 Migration Instructions

### 1. Run Migration

```bash
cd backend
alembic upgrade admin_001
```

### 2. Verify Tables Created

```sql
\dt api_providers
\dt api_credentials
\dt rate_limits
\dt quotas
\dt plans
\dt feature_flags
\dt schedules
\dt cache_policies
\dt audit_log
\dt system_settings
```

### 3. Check Seeded Data

```sql
-- Default plans
SELECT code, name FROM plans;
-- Expected: free, pro

-- Default feature flags
SELECT key, value_boolean FROM feature_flags;
-- Expected: EOD_ENABLE, NEWS_ENABLE, etc.

-- Default cache policies
SELECT dataset, ttl_seconds FROM cache_policies;
-- Expected: news, crypto_prices, insights, eod_prices

-- Default providers
SELECT type, name, is_enabled FROM api_providers;
-- Expected: newsapi, binance, ollama, etc.
```

---

## 🔄 Data Migration from ENV

After running the migration, populate from existing ENV vars:

### Script: `scripts/migrate_env_to_db.py`

```python
from app.models.admin import FeatureFlag, CachePolicy, ApiProvider
from app.core.config import settings
from app.database import SessionLocal

db = SessionLocal()

# Migrate feature flags
flags = {
    'EOD_ENABLE': settings.eod_enable,
    'NEWS_ENABLE': settings.news_enable,
    'FEATURE_CRYPTO_POSITIONS': settings.feature_crypto_positions,
}

for key, value in flags.items():
    flag = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    if flag:
        flag.value_boolean = value
        db.commit()

# Migrate cache policies
if settings.news_cache_ttl_seconds:
    policy = db.query(CachePolicy).filter(CachePolicy.dataset == 'news').first()
    if policy:
        policy.ttl_seconds = settings.news_cache_ttl_seconds
        db.commit()

print("✅ Migration complete")
```

---

## 📊 Usage Examples

### Example 1: Enable Shadow Mode for New Provider

```sql
-- Add new provider in shadow mode
INSERT INTO api_providers (id, type, name, base_url, is_enabled, is_shadow_mode, priority)
VALUES (
    gen_random_uuid(),
    'news',
    'bloomberg',
    'https://api.bloomberg.com',
    true,
    true,  -- Shadow mode
    99     -- Low priority
);
```

### Example 2: Set Up Rate Limit for Admin Endpoint

```sql
INSERT INTO rate_limits (id, scope, scope_id, window_seconds, limit, burst, policy)
VALUES (
    gen_random_uuid(),
    'endpoint',
    '/admin/tasks/fetch-eod',
    60,    -- 1 minute window
    10,    -- 10 requests max
    2,     -- Allow 2 burst
    'reject'
);
```

### Example 3: Track LLM Token Usage

```sql
-- Create quota
INSERT INTO quotas (id, scope, scope_id, resource_type, period, hard_cap, soft_cap, current_usage, period_start, period_end)
VALUES (
    gen_random_uuid(),
    'user',
    'user-uuid-here',
    'llm_tokens',
    'day',
    10000,  -- Hard cap
    8000,   -- Soft cap (warning)
    0,      -- Initial usage
    NOW(),
    NOW() + INTERVAL '1 day'
);

-- Increment usage
UPDATE quotas
SET current_usage = current_usage + 500
WHERE scope = 'user' AND scope_id = 'user-uuid-here' AND resource_type = 'llm_tokens';

-- Check if over limit
SELECT current_usage >= hard_cap AS is_blocked
FROM quotas
WHERE scope = 'user' AND scope_id = 'user-uuid-here' AND resource_type = 'llm_tokens';
```

---

## 🎯 Next Steps

1. ✅ Run migration: `alembic upgrade admin_001`
2. ✅ Verify seeded data
3. ⬜ Create admin API endpoints (CRUD for each table)
4. ⬜ Implement audit logging middleware
5. ⬜ Build admin UI (React components)
6. ⬜ Migrate ENV vars to database
7. ⬜ Set up encryption for API keys
8. ⬜ Implement rate limiting middleware

---

## 📝 Files Created

```
backend/
├── migrations/versions/
│   └── admin_001_create_admin_tables.py
├── app/models/admin/
│   ├── __init__.py
│   ├── api_provider.py
│   ├── rate_limit.py
│   ├── plan.py
│   ├── feature_flag.py
│   ├── schedule.py
│   ├── cache_policy.py
│   ├── audit_log.py
│   └── system_setting.py
└── app/schemas/admin/
    ├── __init__.py
    ├── api_provider.py
    ├── rate_limit.py
    ├── plan.py
    ├── feature_flag.py
    ├── schedule.py
    ├── cache_policy.py
    ├── audit_log.py
    └── system_setting.py

docs/admin/
└── schema.md (this file)
```

---

**Status:** ✅ **Ready for Review and Deployment**
