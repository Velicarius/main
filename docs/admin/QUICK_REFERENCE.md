# 🚀 Quick Reference - Admin Configuration

**Быстрый доступ к ключевым настройкам**

---

## 🔑 API Keys (6 штук)

```bash
# Security (required in production)
JWT_SECRET_KEY=         # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
SESSION_SECRET=         # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=            # Legacy, still used

# Admin (⚠️ migrate to JWT)
ADMIN_TOKEN=           # Simple token for /admin/* endpoints

# LLM
OPENAI_API_KEY=        # Optional, for OpenAI models

# News Providers (all optional)
FINNHUB_API_KEY=
ALPHAVANTAGE_API_KEY=
NEWSAPI_API_KEY=
```

---

## 🎛️ Feature Flags (11 штук)

```bash
# Core Features
EOD_ENABLE=false                    # Enable EOD price fetching
NEWS_ENABLE=false                   # Enable news aggregation
FEATURE_CRYPTO_POSITIONS=false      # Enable crypto assets

# Cache Control
NEWS_CACHE_ENABLED=true
NEWS_READ_CACHE_ENABLED=true

# News Fetching
NEWS_PROVIDER_FETCH_ENABLED=false   # Active news fetching
NEWS_PROVIDER_SHADOW_MODE=true      # Test providers without using data
```

---

## ⏱️ Cache TTL Settings

```bash
# News
NEWS_CACHE_TTL_SECONDS=300          # 5 minutes

# Crypto Prices
CRYPTO_PRICE_TTL_SECONDS=60         # 1 minute

# ⚠️ HARDCODED (needs fix):
# - Insights cache: 24 hours (unified_cache_service.py:61)
# - SWR refresh: 15 minutes (unified_cache_service.py:62)
# - Stale grace: 2 hours (unified_cache_service.py:63)
```

---

## 📅 Celery Schedules

```bash
# EOD Price Refresh
EOD_SCHEDULE_CRON="30 23 * * *"     # 23:30 Europe/Warsaw

# News Planner
NEWS_PLANNER_RUN_HOUR_LOCAL=6       # 6:00 local time
NEWS_PLANNER_RUN_MINUTE_LOCAL=30    # 6:30 local time

# ⚠️ HARDCODED:
# - Timezone: "Europe/Warsaw" (celery_app.py:91)
# - Portfolio valuation: +15 min after EOD
```

---

## 🔌 Provider Configuration

### News Providers

```bash
NEWS_TIMEOUT=10                     # Request timeout (seconds)
NEWS_DAILY_LIMIT=80                 # Max articles per day
NEWS_DAILY_SYMBOLS=20               # Max symbols per day
NEWS_PROVIDER_DEFAULT=newsapi       # Primary provider
NEWS_SHADOW_PROVIDERS=              # Comma-separated test providers
```

### Crypto Providers

```bash
CRYPTO_PRICE_PRIMARY=binance
CRYPTO_ALLOWED_SYMBOLS="BTC,ETH,SOL,BNB,ADA,XRP,DOGE,AVAX,MATIC"
```

### LLM Models

```bash
# Insights
DEFAULT_INSIGHTS_MODEL=llama3.1:8b
DEFAULT_INSIGHTS_PROVIDER=ollama

# News Analysis
DEFAULT_NEWS_MODEL=llama3.1:8b
DEFAULT_NEWS_PROVIDER=ollama

# OpenAI (if using)
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

---

## 🛡️ Security Checklist

### ✅ Implemented
- [x] JWT authentication for user endpoints
- [x] Secret validation in production
- [x] Password hashing (bcrypt)

### ❌ Missing (HIGH PRIORITY)
- [ ] `/admin/tasks/*` endpoints **NOT PROTECTED**
- [ ] No rate limiting on any endpoints
- [ ] Admin auth uses simple token (not JWT)
- [ ] No audit logging

### 🔧 Quick Fixes

**1. Protect admin endpoints immediately:**
```python
# In admin_tasks.py:42
from app.routers.admin_eod import verify_admin_token

@router.post("/fetch-eod")
async def trigger_fetch_eod(
    request: FetchEODRequest,
    admin_token: str = Depends(verify_admin_token)  # ADD THIS
):
```

**2. Add to .env:**
```bash
# Generate admin token
ADMIN_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

---

## 🐛 Known Issues

### Critical (fix immediately)
1. **Unprotected endpoints**: `/admin/tasks/*` has NO authentication
2. **Hardcoded localhost**: `unified_cache_service.py:56`
3. **Duplicate config**: `NEWS_CACHE_TTL` and `NEWS_CACHE_TTL_SECONDS`

### Medium (fix this week)
4. **Hardcoded SWR params**: 3 values in `unified_cache_service.py`
5. **Hardcoded timezone**: `celery_app.py:91`
6. **Sync blocking ops**: `/admin/eod/refresh-sync-all` can hang server

### Low (fix this month)
7. **No rate limiting**: All endpoints unlimited
8. **No quota tracking**: External API usage not monitored
9. **Missing TODOs**: 2 TODOs in codebase

---

## 🔧 Quick Commands

### Start services
```bash
# Local development
docker compose -f infra/docker-compose.yml up postgres redis qdrant

# Run API
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### Test admin endpoints
```bash
# EOD refresh (⚠️ needs ADMIN_TOKEN)
curl -X POST http://localhost:8001/admin/eod/refresh \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"

# Task trigger (⚠️ NO AUTH - SECURITY ISSUE!)
curl -X POST http://localhost:8001/admin/tasks/fetch-eod \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL.US"]}'
```

### Check Celery
```bash
# View beat schedule
celery -A app.celery_app inspect scheduled

# View active tasks
celery -A app.celery_app inspect active

# Flower monitoring
# http://localhost:5555
```

---

## 📊 Monitoring Endpoints

```bash
# Health check
GET /health

# API root
GET /

# EOD config (requires admin token)
GET /admin/eod/config
```

---

## 🎯 Next Steps

### This Week
1. Fix `/admin/tasks/*` authentication
2. Move hardcoded `localhost` to ENV
3. Add rate limiting with `slowapi`

### This Month
1. Create admin UI dashboard
2. Implement audit logging
3. Add API quota tracking
4. Migrate admin auth to JWT

### This Quarter
1. Real-time monitoring dashboard
2. Alert rules engine
3. Automated config backup
4. Multi-region support

---

## 📚 See Also

- Full discovery report: `docs/admin/discovery.md`
- Security fixes: `SECURITY_FIXES_SUMMARY.md`
- Environment setup: `.env.example`
- Configuration reference: `backend/app/core/config.py`
