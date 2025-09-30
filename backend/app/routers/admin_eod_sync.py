from __future__ import annotations
import os
from decimal import Decimal
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.services.price_eod import PriceEODRepository
from app.services.portfolio_valuation_eod import PortfolioValuationEODRepository
from app.marketdata.stooq_client import fetch_latest_from_stooq, StooqFetchError
from app.models.position import Position

router = APIRouter(prefix="/admin", tags=["admin"])

def verify_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

# --- EOD: один тикер (sync) ---
@router.post("/eod/{symbol}/refresh-sync")
def refresh_eod_sync(symbol: str, _auth: None = Depends(verify_admin), db: Session = Depends(get_db)):
    symbol = symbol.strip().lower()
    try:
        latest = fetch_latest_from_stooq(symbol)
    except StooqFetchError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if not latest:
        raise HTTPException(status_code=404, detail=f"No EOD data from Stooq for {symbol}")
    repo = PriceEODRepository(db)
    count = repo.upsert_prices(symbol, [latest])
    return {"status": "ok", "symbol": symbol, "as_of": str(latest["date"]), "records_processed": count, "source": "stooq"}

# --- EOD: все тикеры из positions (sync) ---
@router.post("/eod/refresh-sync-all")
def refresh_eod_sync_all(_auth: None = Depends(verify_admin), db: Session = Depends(get_db)):
    symbols = [row[0] for row in db.query(func.lower(Position.symbol)).distinct().all()]
    if not symbols:
        return {"status": "ok", "processed": 0, "symbols": [], "errors": []}
    repo = PriceEODRepository(db)
    processed, results, errors = 0, [], []
    for sym in symbols:
        s = (sym or "").strip().lower()
        if not s:
            continue
        try:
            latest = fetch_latest_from_stooq(s)
            if not latest:
                errors.append({"symbol": s, "error": "no_data_from_stooq"}); continue
            repo.upsert_prices(s, [latest])
            results.append({"symbol": s, "as_of": str(latest["date"])})
            processed += 1
        except StooqFetchError as e:
            errors.append({"symbol": s, "error": f"fetch_failed: {e}"})
        except Exception as e:
            errors.append({"symbol": s, "error": f"upsert_failed: {e}"})
    return {"status": "ok", "processed": processed, "symbols": results, "errors": errors}

# --- ПЕРЕСЧЁТ: только посчитать (без сохранения) ---
@router.post("/portfolio/revalue-eod-sync")
def revalue_portfolios_eod_sync(_auth: None = Depends(verify_admin), db: Session = Depends(get_db)):
    price_repo = PriceEODRepository(db)
    user_ids = [row[0] for row in db.query(Position.user_id).distinct().all()]
    results, errors = [], []
    for uid in user_ids:
        positions = db.query(Position).filter(Position.user_id == uid).all()
        total = Decimal("0"); used_dates = []
        for pos in positions:
            sym = (pos.symbol or "").strip().lower()
            last = price_repo.get_latest_price(sym)
            if not last: continue
            total += Decimal(str(pos.quantity)) * Decimal(str(last.close))
            used_dates.append(last.date)
        results.append({
            "user_id": str(uid),
            "total_value": float(total),
            "positions": [],  # краткий ответ; подробности смотрим в save-ручке/логике
            "missing_prices": []
        })
    return {"status": "ok", "users": results, "errors": errors}

# --- ПЕРЕСЧЁТ И СОХРАНЕНИЕ: upsert в portfolio_valuations_eod ---
@router.post("/portfolio/revalue-eod-sync-save")
def revalue_portfolios_eod_sync_save(_auth: None = Depends(verify_admin), db: Session = Depends(get_db)):
    from app.services.price_eod import PriceEODRepository  # локально на случай циклов
    price_repo = PriceEODRepository(db)
    pv_repo = PortfolioValuationEODRepository(db)

    user_ids = [row[0] for row in db.query(Position.user_id).distinct().all()]
    saved, results, errors = 0, [], []
    for uid in user_ids:
        positions = db.query(Position).filter(Position.user_id == uid).all()
        total = Decimal("0"); used_dates = []
        for pos in positions:
            sym = (pos.symbol or "").strip().lower()
            last = price_repo.get_latest_price(sym)
            if not last: continue
            total += Decimal(str(pos.quantity)) * Decimal(str(last.close))
            used_dates.append(last.date)
        if not used_dates:
            results.append({"user_id": str(uid), "skipped": True, "reason": "no_prices"})
            continue
        as_of = max(used_dates)
        try:
            pv_repo.upsert(uid, as_of, total, currency="USD")
            results.append({"user_id": str(uid), "as_of": str(as_of), "total_value": float(total)})
            saved += 1
        except Exception as e:
            errors.append({"user_id": str(uid), "error": f"save_failed: {e}"})
    return {"status": "ok", "saved": saved, "results": results, "errors": errors}