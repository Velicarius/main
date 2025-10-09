# 📋 Implementation Tasks - Admin Panel

**Конкретные задачи для реализации Admin Panel**

---

## 🚨 CRITICAL - Fix Security Issues (Do First!)

### Task 1: Protect `/admin/tasks/*` endpoints
**Priority**: 🔴 CRITICAL
**Effort**: 15 minutes
**Risk**: High - public access to task triggers

**Files to modify**:
- `backend/app/routers/admin_tasks.py`

**Changes**:
```python
# Line 42
from app.routers.admin_eod import verify_admin_token

@router.post("/fetch-eod", response_model=TaskResponse)
async def trigger_fetch_eod(
    request: FetchEODRequest,
    admin_token: str = Depends(verify_admin_token)  # ADD THIS LINE
):
    # ... existing code

# Line 80
@router.get("/fetch-eod/{task_id}", response_model=dict)
async def get_task_status(
    task_id: str,
    admin_token: str = Depends(verify_admin_token)  # ADD THIS LINE
):
    # ... existing code
```

**Test**:
```bash
# Should fail without token
curl -X POST http://localhost:8001/admin/tasks/fetch-eod \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL.US"]}'
# Expected: 403 Forbidden

# Should work with token
curl -X POST http://localhost:8001/admin/tasks/fetch-eod \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_TOKEN" \
  -d '{"symbols": ["AAPL.US"]}'
# Expected: 200 OK
```

---

### Task 2: Add Rate Limiting
**Priority**: 🔴 HIGH
**Effort**: 1 hour
**Risk**: Medium - DoS vulnerability

**Install dependency**:
```bash
pip install slowapi
```

**Add to `requirements.txt`**:
```
slowapi==0.1.9
```

**Create new file**: `backend/app/middleware/rate_limit.py`
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Usage in routers:
# @router.post("/refresh")
# @limiter.limit("10/minute")
# async def trigger_eod_refresh(...):
```

**Modify `backend/app/main.py`**:
```python
from app.middleware.rate_limit import limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Apply to admin endpoints**:
```python
# admin_eod.py
from app.middleware.rate_limit import limiter

@router.post("/refresh", response_model=EODRefreshResponse)
@limiter.limit("10/minute")  # ADD THIS
async def trigger_eod_refresh(...):
```

---

### Task 3: Fix Hardcoded `localhost` in Cache Service
**Priority**: 🔴 HIGH
**Effort**: 10 minutes
**Risk**: High - breaks in Docker/production

**File**: `backend/app/services/unified_cache_service.py`

**Change line 56**:
```python
# BEFORE
REDIS_HOST = 'localhost'

# AFTER
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')  # 'redis' is Docker service name
```

**Change line 57-58**:
```python
# BEFORE
REDIS_PORT = 6379
REDIS_DB = 0

# AFTER
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
```

---

## 🟡 HIGH - Configuration Management

### Task 4: Move SWR Config to ENV
**Priority**: 🟡 HIGH
**Effort**: 30 minutes

**Add to `backend/app/core/config.py`**:
```python
# Line ~70 (after news_cache settings)

# Insights Cache (SWR)
insights_cache_ttl: int = Field(default=86400, alias="INSIGHTS_CACHE_TTL")  # 24h
insights_refresh_threshold: int = Field(default=900, alias="INSIGHTS_REFRESH_THRESHOLD")  # 15min
insights_stale_grace: int = Field(default=7200, alias="INSIGHTS_STALE_GRACE")  # 2h

# Circuit Breaker
circuit_breaker_failures: int = Field(default=3, alias="CIRCUIT_BREAKER_FAILURES")
circuit_breaker_window: int = Field(default=300, alias="CIRCUIT_BREAKER_WINDOW")  # 5min
circuit_breaker_recovery: int = Field(default=600, alias="CIRCUIT_BREAKER_RECOVERY")  # 10min
```

**Modify `backend/app/services/unified_cache_service.py`**:
```python
# Remove @dataclass
# Remove hardcoded values
# Change to:

class UnifiedCacheConfig:
    """Dynamic configuration from settings"""

    def __init__(self, settings):
        self.REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
        self.REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
        self.REDIS_DB = int(os.getenv('REDIS_DB', '0'))

        # From settings object
        self.DEFAULT_TTL = settings.insights_cache_ttl
        self.REFRESH_THRESHOLD = settings.insights_refresh_threshold
        self.STALE_GRACE = settings.insights_stale_grace

        # ... rest
```

**Update `.env.example`**:
```bash
# === Insights Cache (SWR) ===
INSIGHTS_CACHE_TTL=86400           # 24 hours
INSIGHTS_REFRESH_THRESHOLD=900     # 15 minutes
INSIGHTS_STALE_GRACE=7200          # 2 hours

# === Circuit Breaker ===
CIRCUIT_BREAKER_FAILURES=3
CIRCUIT_BREAKER_WINDOW=300         # 5 minutes
CIRCUIT_BREAKER_RECOVERY=600       # 10 minutes
```

---

### Task 5: Fix Duplicate NEWS_CACHE_TTL
**Priority**: 🟡 MEDIUM
**Effort**: 20 minutes

**Decision**: Remove `NEWS_CACHE_TTL`, keep `NEWS_CACHE_TTL_SECONDS`

**In `backend/app/core/config.py`**:
```python
# Line 48 - REMOVE this line:
# news_cache_ttl: int = Field(default=300, alias="NEWS_CACHE_TTL")

# Keep only:
news_cache_ttl_seconds: int = Field(default=300, alias="NEWS_CACHE_TTL_SECONDS")
```

**Search and replace in all files**:
```bash
grep -r "settings.news_cache_ttl" backend/app --include="*.py"
# Replace with: settings.news_cache_ttl_seconds
```

**Deprecation warning** (optional):
```python
@property
def news_cache_ttl(self) -> int:
    """Deprecated: use news_cache_ttl_seconds instead"""
    import warnings
    warnings.warn("news_cache_ttl is deprecated, use news_cache_ttl_seconds", DeprecationWarning)
    return self.news_cache_ttl_seconds
```

---

### Task 6: Configurable Celery Timezone
**Priority**: 🟡 MEDIUM
**Effort**: 15 minutes

**Add to `backend/app/core/config.py`**:
```python
# Celery Configuration
celery_timezone: str = Field(default="Europe/Warsaw", alias="CELERY_TIMEZONE")
celery_retry_delay: int = Field(default=60, alias="CELERY_RETRY_DELAY")
celery_max_retries: int = Field(default=3, alias="CELERY_MAX_RETRIES")
celery_result_expires: int = Field(default=3600, alias="CELERY_RESULT_EXPIRES")
```

**Update `backend/app/celery_app.py`**:
```python
# Line 86-109
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.celery_timezone,  # FROM SETTINGS
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,

    # Retry settings
    task_default_retry_delay=settings.celery_retry_delay,  # FROM SETTINGS
    task_max_retries=settings.celery_max_retries,  # FROM SETTINGS

    # Result backend settings
    result_expires=settings.celery_result_expires,  # FROM SETTINGS
    result_persistent=True,
)
```

**Update `.env.example`**:
```bash
# === Celery Configuration ===
CELERY_TIMEZONE=Europe/Warsaw
CELERY_RETRY_DELAY=60             # seconds
CELERY_MAX_RETRIES=3
CELERY_RESULT_EXPIRES=3600        # 1 hour
```

---

## 🟢 MEDIUM - Audit & Logging

### Task 7: Add Audit Logging
**Priority**: 🟢 MEDIUM
**Effort**: 2 hours

**Create new file**: `backend/app/models/audit_log.py`
```python
from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
from app.models.base import Base
from app.dbtypes import GUID
import uuid

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(GUID(), nullable=True)  # Nullable for anonymous/admin
    action = Column(String(100), nullable=False)  # e.g., "admin.eod.refresh"
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    request_body = Column(JSON, nullable=True)
    response_status = Column(String(10), nullable=True)
    error = Column(String(1000), nullable=True)
```

**Create middleware**: `backend/app/middleware/audit.py`
```python
from fastapi import Request
from app.models.audit_log import AuditLog
from app.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

async def log_admin_action(
    request: Request,
    action: str,
    user_id: str = None,
    response_status: int = None,
    error: str = None
):
    """Log admin action to database"""
    try:
        db = SessionLocal()
        log_entry = AuditLog(
            action=action,
            endpoint=str(request.url.path),
            method=request.method,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            user_id=user_id,
            response_status=str(response_status) if response_status else None,
            error=error
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit entry: {e}")
    finally:
        db.close()
```

**Use in admin endpoints**:
```python
# admin_eod.py
from app.middleware.audit import log_admin_action

@router.post("/refresh")
async def trigger_eod_refresh(
    request: Request,  # ADD THIS
    admin_token: str = Depends(verify_admin_token)
):
    try:
        # ... existing code
        await log_admin_action(request, "admin.eod.refresh", response_status=200)
        return response
    except Exception as e:
        await log_admin_action(request, "admin.eod.refresh", error=str(e), response_status=500)
        raise
```

**Migration**:
```bash
cd backend
alembic revision --autogenerate -m "Add audit logs table"
alembic upgrade head
```

---

## 🟢 LOW - Admin UI

### Task 8: Create Admin Dashboard (React)
**Priority**: 🟢 LOW
**Effort**: 8-16 hours

**Structure**:
```
frontend/src/pages/Admin/
├── index.tsx                 # Admin main page
├── FeatureFlags.tsx         # Toggle feature flags
├── CacheManagement.tsx      # Clear cache, view stats
├── TaskMonitor.tsx          # Celery task status
├── ProviderStatus.tsx       # API provider health
├── AuditLog.tsx             # View audit logs
└── ConfigEditor.tsx         # Edit ENV values (careful!)
```

**Example**: `FeatureFlags.tsx`
```typescript
import { useState, useEffect } from 'react';

interface FeatureFlag {
  name: string;
  key: string;
  value: boolean;
  description: string;
}

export default function FeatureFlags() {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);

  useEffect(() => {
    fetch('/admin/config/flags', {
      headers: { 'X-Admin-Token': localStorage.getItem('adminToken') }
    })
      .then(res => res.json())
      .then(data => setFlags(data.flags));
  }, []);

  const toggleFlag = async (key: string) => {
    await fetch(`/admin/config/flags/${key}/toggle`, {
      method: 'POST',
      headers: { 'X-Admin-Token': localStorage.getItem('adminToken') }
    });
    // Refresh flags
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Feature Flags</h2>
      {flags.map(flag => (
        <div key={flag.key} className="flex items-center justify-between p-4 border rounded">
          <div>
            <h3 className="font-semibold">{flag.name}</h3>
            <p className="text-sm text-gray-600">{flag.description}</p>
          </div>
          <button
            onClick={() => toggleFlag(flag.key)}
            className={`px-4 py-2 rounded ${flag.value ? 'bg-green-500' : 'bg-gray-300'}`}
          >
            {flag.value ? 'ON' : 'OFF'}
          </button>
        </div>
      ))}
    </div>
  );
}
```

**Backend endpoint**: `backend/app/routers/admin_config.py`
```python
from fastapi import APIRouter, Depends
from app.routers.admin_eod import verify_admin_token
from app.core.config import settings

router = APIRouter(prefix="/admin/config", tags=["admin-config"])

@router.get("/flags")
async def get_feature_flags(admin_token: str = Depends(verify_admin_token)):
    return {
        "flags": [
            {
                "name": "EOD Data Fetching",
                "key": "EOD_ENABLE",
                "value": settings.eod_enable,
                "description": "Enable end-of-day price data fetching"
            },
            {
                "name": "News Aggregation",
                "key": "NEWS_ENABLE",
                "value": settings.news_enable,
                "description": "Enable news aggregation from providers"
            },
            # ... more flags
        ]
    }

@router.post("/flags/{key}/toggle")
async def toggle_feature_flag(
    key: str,
    admin_token: str = Depends(verify_admin_token)
):
    # Note: This requires writing to .env or using a database
    # For now, return error
    raise HTTPException(
        status_code=501,
        detail="Feature flag runtime toggle not implemented. Update .env and restart."
    )
```

---

## 📊 Testing Tasks

### Task 9: Write Tests for Admin Endpoints
**Priority**: 🟡 MEDIUM
**Effort**: 4 hours

**Create**: `backend/tests/test_admin_endpoints.py`
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_admin_eod_refresh_requires_token():
    """Test that EOD refresh requires admin token"""
    response = client.post("/admin/eod/refresh")
    assert response.status_code == 403

def test_admin_eod_refresh_with_valid_token(admin_token):
    """Test EOD refresh with valid token"""
    response = client.post(
        "/admin/eod/refresh",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code in [200, 503]  # 503 if EOD disabled

def test_admin_tasks_fetch_eod_requires_token():
    """Test that task trigger requires token"""
    response = client.post(
        "/admin/tasks/fetch-eod",
        json={"symbols": ["AAPL.US"]}
    )
    # After fix, should be 403
    # Currently, it's 200 (BUG!)
    assert response.status_code == 403

def test_rate_limiting_on_admin_endpoints(admin_token):
    """Test rate limiting works"""
    # Make 11 requests (limit is 10/minute)
    for i in range(11):
        response = client.post(
            "/admin/eod/refresh",
            headers={"X-Admin-Token": admin_token}
        )
        if i < 10:
            assert response.status_code in [200, 503]
        else:
            assert response.status_code == 429  # Too Many Requests
```

---

## 📝 Documentation Tasks

### Task 10: Update README with Admin Guide
**Priority**: 🟢 LOW
**Effort**: 1 hour

Add to `README.md`:
```markdown
## Admin Panel

### Accessing Admin Endpoints

All admin endpoints require authentication via `X-Admin-Token` header:

\`\`\`bash
export ADMIN_TOKEN="your-secret-token"

# Trigger EOD refresh
curl -X POST http://localhost:8001/admin/eod/refresh \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# Check task status
curl http://localhost:8001/admin/eod/status/TASK_ID \
  -H "X-Admin-Token: $ADMIN_TOKEN"
\`\`\`

### Available Admin Endpoints

- `POST /admin/eod/refresh` - Trigger EOD data refresh
- `GET /admin/eod/status/{task_id}` - Check task status
- `GET /admin/eod/config` - View EOD configuration
- `POST /admin/tasks/fetch-eod` - Trigger manual EOD fetch
- ... (see docs/admin/discovery.md for full list)

### Security

⚠️ **Important**: Admin endpoints use simple token authentication.
In production, ensure `ADMIN_TOKEN` is:
- Strong (32+ characters)
- Secret (never committed to git)
- Rotated regularly

Roadmap: Migrate to JWT-based admin auth with roles.
```

---

## 🎯 Prioritized Execution Plan

### Week 1 (Security Focus)
- [ ] Day 1: Task 1 - Protect `/admin/tasks/*`
- [ ] Day 2: Task 2 - Add rate limiting
- [ ] Day 3: Task 3 - Fix hardcoded localhost
- [ ] Day 4: Task 9 - Write admin endpoint tests
- [ ] Day 5: Code review & deployment

### Week 2 (Configuration)
- [ ] Day 1-2: Task 4 - Move SWR config to ENV
- [ ] Day 3: Task 5 - Fix duplicate TTL
- [ ] Day 4: Task 6 - Configurable Celery
- [ ] Day 5: Documentation updates

### Week 3-4 (Features)
- [ ] Week 3: Task 7 - Audit logging
- [ ] Week 4: Task 8 - Admin UI dashboard

---

## ✅ Definition of Done

For each task, consider it "Done" when:
- [ ] Code implemented and tested locally
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] Verified in staging environment
- [ ] No regressions detected

---

## 🚀 Deployment Checklist

Before deploying admin changes to production:
- [ ] All secrets set in production ENV
- [ ] Admin token is strong (32+ characters)
- [ ] Rate limiting configured
- [ ] Audit logging enabled
- [ ] Monitoring alerts configured
- [ ] Backup plan in place
- [ ] Rollback plan tested
