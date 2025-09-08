from fastapi import FastAPI
from .routers import health, portfolio
from .core.config import settings
from celery import Celery

app = FastAPI(title="AI Portfolio API", version="0.1.0")

# Celery
celery_app = Celery(
    "ai-portfolio",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/1",
)

app.include_router(health.router)
app.include_router(portfolio.router)

@app.get("/", tags=["root"])
def root():
    return {"status": "ok", "env": settings.app_env}
