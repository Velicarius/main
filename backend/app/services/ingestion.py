# Placeholder for market data ingestion (quotes, fundamentals, news, etc.).
# Implement your adapters here—e.g., Polygon.io, Finnhub, Alpha Vantage, NewsAPI.
# For live usage, add Celery tasks that fetch & store data in Postgres and vectors in Qdrant.
from typing import List, Dict

def upsert_positions(user_id: str, positions: List[Dict]):
    # TODO: persist to Postgres via SQLAlchemy.
    return {"status": "ok", "count": len(positions)}
