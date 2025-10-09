from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from celery import Celery
from app.core.config import settings
from app.routers import health, portfolio, dbtest, portfolio_value, prices_ingest, positions, admin_tasks, admin_eod, portfolio_valuations
from app.routers import admin_eod_sync, symbols_external, ai_portfolio, auth, users, prices_eod, llm_proxy, debug_net, insights_v2, insights_optimized, sentiment, ai_insights_swr, ai_insights_fixed, strategy, news, crypto_quotes, news_ingest, news_read, news_admin, jwt_auth
from app.routers.admin import users_router as admin_users_router
from app.routers import admin_feature_flags, admin_api_providers, admin_rate_limits, admin_schedules, admin_cache_policies, admin_system_settings, admin_audit_log, admin_user_intelligence
from app.database import SessionLocal
from app.db.seed import seed_demo_data

import os
import logging

log = logging.getLogger(__name__)

app = FastAPI(title="AI Portfolio API", version="0.1.0")

# Configure CORS для фронтенда и UI
# Зачем: Позволяем фронтенду (React/Vite) и встроенному UI обращаться к API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (React frontend)
        "http://127.0.0.1:5173",
        "http://localhost:8080",  # Альтернативный порт для фронтенда
        "http://127.0.0.1:8080",
        "http://localhost:8000",  # Встроенный UI (FastAPI static files)
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,  # Разрешаем cookies для аутентификации
    allow_methods=["*"],     # Разрешаем все HTTP методы (GET, POST, PUT, DELETE)
    allow_headers=["*"],     # Разрешаем все заголовки (Content-Type, Authorization)
)

# Session cookie для OAuth
# Validate SESSION_SECRET in production
if settings.app_env in ("production", "prod"):
    if not settings.session_secret or settings.session_secret in ("dev-secret-change-me", "dev-secret"):
        raise ValueError("SESSION_SECRET must be set to a secure random value in production")
    SESSION_SECRET = settings.session_secret
else:
    SESSION_SECRET = settings.session_secret or "dev-secret-change-me"

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")

# Activity Tracker для логирования запросов пользователей
# Зачем: Отслеживаем все API запросы для аналитики, квот и аудита
from app.middleware.activity_tracker import ActivityTrackerMiddleware
app.add_middleware(ActivityTrackerMiddleware)

# Инициализируем Celery только если не в тестовом режиме
celery_app = None
if not getattr(app.state, "TEST_MODE", False):
    celery_app = Celery(
        "ai-portfolio",
        broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
        backend=f"redis://{settings.redis_host}:{settings.redis_port}/1",
    )

# Подключаем все роутеры к FastAPI приложению
# Зачем: Каждый роутер добавляет свои endpoints к API
app.include_router(health.router)              # /health - проверка состояния API
app.include_router(jwt_auth.router)            # /api/auth - JWT аутентификация (НОВОЕ)
app.include_router(admin_users_router)         # /api/admin/v1 - управление пользователями и ролями (admin only)
app.include_router(portfolio.router)           # /portfolio - управление портфелями
app.include_router(dbtest.router)              # /dbtest - тестирование БД
app.include_router(portfolio_value.router)     # /portfolio-value - расчет стоимости
app.include_router(positions.router)           # /positions - управление позициями (JWT protected)
app.include_router(prices_ingest.router)       # /prices-ingest - загрузка цен
app.include_router(prices_eod.router)          # /prices-eod - EOD цены
app.include_router(admin_tasks.router)         # /admin/tasks - админские задачи
app.include_router(admin_eod.router)           # /admin/eod - EOD админка
app.include_router(admin_eod_sync.router)      # /admin/eod-sync - синхронизация EOD
app.include_router(portfolio_valuations.router) # /portfolio-valuations - оценки портфеля
app.include_router(symbols_external.router)    # /symbols-external - внешние символы
app.include_router(ai_portfolio.router)        # /ai-portfolio - AI анализ портфеля
app.include_router(auth.router)                # /auth - OAuth аутентификация
app.include_router(users.router)               # /users - управление пользователями
app.include_router(llm_proxy.router)           # /llm - прокси к локальным LLM через Ollama
app.include_router(insights_v2.router)         # /insights/v2 - новый анализатор портфеля v2
app.include_router(insights_optimized.router)  # /insights - оптимизированный анализатор с кэшированием
app.include_router(sentiment.router)           # /ai/sentiment - анализатор сентимента финансовых новостей
app.include_router(ai_insights_swr.router)     # /ai/insights-swr - SWR API с полным кэшированием
app.include_router(ai_insights_fixed.router)   # /ai/insights/fixed - исправленный упрощенный API
app.include_router(strategy.router)            # /strategy - управление инвестиционными стратегиями
app.include_router(news.router)                # /news - агрегация новостей из нескольких источников
app.include_router(news_ingest.router)         # /internal/news - внутренний API для ингеста новостей
app.include_router(news_read.router)           # /news - чтение сохраненных новостей
app.include_router(news_admin.router)          # /internal/news - админ API для управления новостями
app.include_router(crypto_quotes.router)       # /crypto/quotes - крипто-цены

# Import news cache router
from app.routers import news_cache
app.include_router(news_cache.router)          # /news/cache - управление кэшем новостей
app.include_router(debug_net.router)           # /debug - диагностика сетевых подключений (только для разработки)

# Admin configuration routers (all require admin role)
app.include_router(admin_feature_flags.router)      # /api/admin/v1/feature-flags - управление feature flags
app.include_router(admin_api_providers.router)      # /api/admin/v1/api-providers - управление API провайдерами
app.include_router(admin_rate_limits.router)        # /api/admin/v1/rate-limits - управление rate limits и квотами
app.include_router(admin_schedules.router)          # /api/admin/v1/schedules - управление расписаниями задач
app.include_router(admin_cache_policies.router)     # /api/admin/v1/cache-policies - управление политиками кэширования
app.include_router(admin_system_settings.router)    # /api/admin/v1/system-settings - управление системными настройками
app.include_router(admin_audit_log.router)          # /api/admin/v1/audit-log - просмотр логов аудита (read-only)
app.include_router(admin_user_intelligence.router)  # /api/admin/v1 - user intelligence endpoints (portfolio, activity, usage)


# Подключаем статические файлы для встроенного UI
# Зачем: Позволяем открывать HTML страницы напрямую через FastAPI
ui_dir = os.path.join(os.path.dirname(__file__), "web", "ui")
if os.path.exists(ui_dir):
    app.mount("/ui", StaticFiles(directory=ui_dir, html=True), name="ui")
    print("✅ Embedded UI served at /ui")
    print("💡 LLM Test UI: http://localhost:8000/ui/llm_test.html")


@app.on_event("startup")
def startup_event():
    """Startup event handler"""
    # Add password_hash column if it doesn't exist
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);"))
        db.commit()
        log.info("Password hash column ensured")
    except Exception as e:
        log.error(f"Failed to add password_hash column: {e}")
    finally:
        db.close()
    
    if os.getenv("SEED_DEMO") == "1":
        log.info("SEED_DEMO=1 detected, seeding demo data...")
        db = SessionLocal()
        try:
            seed_demo_data(db)
        except Exception as e:
            log.error(f"Failed to seed demo data: {e}")
        finally:
            db.close()


@app.get("/", tags=["root"])
def root():
    return {"status": "ok", "env": settings.app_env}

    # --- demo seeding on startup (idempotent) ---
import os
from app.database import SessionLocal
from app.db.seed import seed_positions

if os.getenv("SEED_DEMO", "0") == "1":
    try:
        with SessionLocal() as db:
            seed_positions(db)  # добавляет демо-позиции, если их нет
        print("[seed] Demo positions ensured")
    except Exception as e:
        print(f"[seed] failed: {e}")
# --- end seeding ---

