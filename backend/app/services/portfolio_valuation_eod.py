from __future__ import annotations
from typing import Optional, List
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import desc

from app.models.portfolio_valuation_eod import PortfolioValuationEOD

class PortfolioValuationEODRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, user_id, as_of: date, total_value: Decimal, currency: str = "USD") -> None:
        payload = {
            "user_id": user_id,
            "as_of": as_of,
            "total_value": Decimal(str(total_value)),
            "currency": currency,
        }
        ins = insert(PortfolioValuationEOD).values(**payload)
        stmt = ins.on_conflict_do_update(
            constraint="uq_portfolio_valuations_eod_user_asof",
            set_={
                "total_value": ins.excluded.total_value,
                "currency": ins.excluded.currency,
            },
        )
        self.db.execute(stmt)
        self.db.commit()

    def list_by_user(
        self,
        user_id,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[PortfolioValuationEOD]:
        q = self.db.query(PortfolioValuationEOD).filter(PortfolioValuationEOD.user_id == user_id)
        if start_date:
            q = q.filter(PortfolioValuationEOD.as_of >= start_date)
        if end_date:
            q = q.filter(PortfolioValuationEOD.as_of <= end_date)
        return q.order_by(PortfolioValuationEOD.as_of.asc()).all()

    def latest_by_user(self, user_id) -> Optional[PortfolioValuationEOD]:
        return (
            self.db.query(PortfolioValuationEOD)
            .filter(PortfolioValuationEOD.user_id == user_id)
            .order_by(desc(PortfolioValuationEOD.as_of))
            .first()
        )
