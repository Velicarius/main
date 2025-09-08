from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from ..database import get_db
from ..models import Price
import csv
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/prices", tags=["prices"])

@router.post("/load_csv")
def load_prices_csv(
    path: str = Query(..., description="Путь к CSV внутри контейнера API, напр. /app/backend/data/prices.csv"),
    db: Session = Depends(get_db),
):
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"CSV not found: {path}")

    added = 0
    skipped = 0
    with p.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # ожидаем колонки: symbol, ts, close
        for row in reader:
            try:
                symbol = row["symbol"].strip()
                ts = datetime.fromisoformat(row["ts"].strip())
                close = float(row["close"])
            except Exception as e:
                skipped += 1
                continue

            stmt = insert(Price.__table__).values(
                symbol=symbol,
                ts=ts,
                close=close,
            ).on_conflict_do_nothing(
                index_elements=["symbol", "ts"]
            )
            db.execute(stmt)
            added += 1
    db.commit()
    return {"status": "ok", "added": added, "skipped": skipped}
