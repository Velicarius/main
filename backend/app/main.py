from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from celery import Celery
from app.core.config import settings
from app.routers import health, portfolio, dbtest, portfolio_value, prices_ingest, positions, admin_tasks, admin_eod, portfolio_valuations
from app.routers import admin_eod_sync, symbols_external, ai_portfolio, auth, users, prices_eod
from app.database import SessionLocal
from app.db.seed import seed_demo_data

import os
import logging

log = logging.getLogger(__name__)

app = FastAPI(title="AI Portfolio API", version="0.1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session cookie для OAuth
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-me")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")

# Инициализируем Celery только если не в тестовом режиме
celery_app = None
if not getattr(app.state, "TEST_MODE", False):
    celery_app = Celery(
        "ai-portfolio",
        broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
        backend=f"redis://{settings.redis_host}:{settings.redis_port}/1",
    )

app.include_router(health.router)
app.include_router(portfolio.router)
app.include_router(dbtest.router)
app.include_router(portfolio_value.router)
app.include_router(positions.router)
app.include_router(prices_ingest.router)
app.include_router(prices_eod.router)
app.include_router(admin_tasks.router)
app.include_router(admin_eod.router)
app.include_router(admin_eod_sync.router)
app.include_router(portfolio_valuations.router)
app.include_router(symbols_external.router)
app.include_router(ai_portfolio.router)
app.include_router(auth.router)
app.include_router(users.router)


# Mount static files for UI
ui_dir = os.path.join(os.path.dirname(__file__), "web", "ui")
if os.path.exists(ui_dir):
    app.mount("/ui", StaticFiles(directory=ui_dir, html=True), name="ui")
    print("✅ Embedded UI served at /ui")


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

