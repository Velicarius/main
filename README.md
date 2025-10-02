# AI Portfolio Starter

A minimal, production-minded scaffold for an AI-driven portfolio analytics app.

## Stack
- **Backend**: FastAPI + Pydantic
- **Data**: Postgres (positions, users), Qdrant (vector search), Redis (tasks/cache)
- **Workers**: Celery (background jobs), Flower (monitoring)
- **Infra**: Docker Compose (local), GitHub Actions (CI), Terraform skeleton (AWS)
- **AI**: OpenAI-compatible client (optional), local rule-based fallback
- **Quality**: pre-commit (ruff/black), pytest

## Quick start (local)
```bash
# 1) Copy env template
cp .env.example .env

# 2) Start services (API, Postgres, Qdrant, Redis, Worker, Flower)
docker compose -f infra/docker-compose.yml up --build

# 3) Open http://localhost:8002/docs for API
#    Flower: http://localhost:5555
```

## Локальная разработка

Для разработки рекомендуется запускать только инфраструктурные сервисы в Docker, а API локально:

```bash
# 1) Поднять только сервисы БД/Redis/Qdrant
docker compose -f infra/docker-compose.yml up -d postgres redis qdrant

# 2) Запуск локального API
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

- **Swagger UI**: http://127.0.0.1:8001/docs
- **OpenAPI JSON**: http://127.0.0.1:8001/openapi.json

## Миграции

### Применение миграций
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8=1
alembic -c alembic.ini upgrade head
```

### Создание новой миграции
```powershell
alembic -c alembic.ini revision --autogenerate -m "описание изменений"
```

## Structure
```
ai-portfolio-starter/
  backend/
    app/
      main.py
      routers/
        health.py
        portfolio.py
      core/config.py
      services/
        ai.py
        features.py
        ingestion.py
        vectors.py
    tests/
      test_health.py
    pyproject.toml
  infra/
    docker-compose.yml
    prometheus.yml
    terraform/
      main.tf
      variables.tf
      outputs.tf
  .github/workflows/ci.yml
  .pre-commit-config.yaml
  .devcontainer/devcontainer.json
  Makefile
  .env.example
```

## Troubleshooting
- Legacy shim: `app.quotes.stooq` re-exports `app.marketdata.stooq_client`

## Next steps
- Hook your market data sources in `services/ingestion.py`
- Implement embeddings and retrieval in `services/vectors.py`
- Expand portfolio analytics in `services/features.py`
- Wire your own models or an API key in `services/ai.py`
- Add authentication and persistence beyond demo purposes
