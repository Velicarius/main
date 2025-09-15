from fastapi import FastAPI
from celery import Celery
from .core.config import settings
from .routers import health, portfolio, dbtest, portfolio_value, prices_ingest, positions

app = FastAPI(title="AI Portfolio API", version="0.1.0")

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


@app.get("/", tags=["root"])
def root():
    return {"status": "ok", "env": settings.app_env}
