from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PortfolioValuationEODOut
from app.services.portfolio_valuation_eod import PortfolioValuationEODRepository

router = APIRouter(prefix="/portfolio-valuations", tags=["portfolio-valuations"])

@router.get("/{user_id}", response_model=List[PortfolioValuationEODOut])
def list_valuations(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    repo = PortfolioValuationEODRepository(db)
    return repo.list_by_user(user_id, start_date, end_date)

@router.get("/{user_id}/latest", response_model=PortfolioValuationEODOut)
def latest_valuation(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    repo = PortfolioValuationEODRepository(db)
    row = repo.latest_by_user(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="No valuation found")
    return row

@router.get("/{user_id}/history", response_model=List[PortfolioValuationEODOut])
def portfolio_history(
    user_id: UUID,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Get portfolio valuation history for chart display"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    repo = PortfolioValuationEODRepository(db)
    return repo.list_by_user(user_id, start_date, end_date)




