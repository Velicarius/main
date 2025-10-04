from typing import List, Dict, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import desc

from app.models.price_eod import PriceEOD


def _normalize_symbol(sym: str) -> str:
    """Normalize symbol to uppercase for consistent storage"""
    return (sym or "").strip().upper()


class PriceEODRepository:
    """Repository for PriceEOD operations"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_prices(self, symbol: str, prices: List[Dict]) -> int:
        """
        Upsert (insert or update) price data for a symbol.
        rows: [{'date': date, 'open':..., 'high':..., 'low':..., 'close':..., 'volume':..., 'source':...}]
        """
        if not prices:
            return 0

        sym = _normalize_symbol(symbol)

        payload: List[Dict] = []
        now_utc = datetime.utcnow()
        for p in prices:
            payload.append({
                "symbol": sym,
                "date": p["date"],
                "open": p.get("open"),
                "high": p.get("high"),
                "low": p.get("low"),
                "close": p["close"],
                "volume": p.get("volume"),
                "source": p.get("source"),
                "ingested_at": now_utc,
            })

        insert_stmt = insert(PriceEOD).values(payload)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                "open": insert_stmt.excluded.open,
                "high": insert_stmt.excluded.high,
                "low": insert_stmt.excluded.low,
                "close": insert_stmt.excluded.close,
                "volume": insert_stmt.excluded.volume,
                "source": insert_stmt.excluded.source,
                "ingested_at": insert_stmt.excluded.ingested_at,
            },
        )

        self.db.execute(stmt)
        self.db.commit()
        return len(payload)

    def get_prices(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[PriceEOD]:
        sym = _normalize_symbol(symbol)
        q = self.db.query(PriceEOD).filter(PriceEOD.symbol == sym)
        if start_date:
            q = q.filter(PriceEOD.date >= start_date)
        if end_date:
            q = q.filter(PriceEOD.date <= end_date)
        return q.order_by(PriceEOD.date.asc()).all()

    def get_latest_price(self, symbol: str) -> Optional[PriceEOD]:
        sym = _normalize_symbol(symbol)
        obj = (
            self.db.query(PriceEOD)
            .filter(PriceEOD.symbol == sym)
            .order_by(desc(PriceEOD.date))
            .first()
        )
        if obj is None and "." not in sym:
            alt = f"{sym}.us"
            obj = (
                self.db.query(PriceEOD)
                .filter(PriceEOD.symbol == alt)
                .order_by(desc(PriceEOD.date))
                .first()
            )
        return obj

    def delete_prices(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        sym = _normalize_symbol(symbol)
        q = self.db.query(PriceEOD).filter(PriceEOD.symbol == sym)
        if start_date:
            q = q.filter(PriceEOD.date >= start_date)
        if end_date:
            q = q.filter(PriceEOD.date <= end_date)
        count = q.count()
        q.delete(synchronize_session=False)
        self.db.commit()
        return count

    def get_price_on_date(self, symbol: str, target_date: date) -> Optional[PriceEOD]:
        """Получить цену на определенную дату"""
        sym = _normalize_symbol(symbol)
        obj = (
            self.db.query(PriceEOD)
            .filter(PriceEOD.symbol == sym)
            .filter(PriceEOD.date == target_date)
            .first()
        )
        if obj is None and "." not in sym:
            alt = f"{sym}.us"
            obj = (
                self.db.query(PriceEOD)
                .filter(PriceEOD.symbol == alt)
                .filter(PriceEOD.date == target_date)
                .first()
            )
        return obj

    def get_symbols(self) -> List[str]:
        """Get all unique symbols that have price data"""
        symbols = self.db.query(PriceEOD.symbol).distinct().all()
        return [symbol[0] for symbol in symbols]
