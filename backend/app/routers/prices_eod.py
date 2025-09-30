from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.price_eod import PriceEOD
from app.schemas import PriceEODResponse, PriceEODCreate, PriceEODUpdate
from app.services.price_eod import PriceEODRepository

router = APIRouter(prefix="/prices-eod", tags=["prices-eod"])


@router.post("/{symbol}/upsert", response_model=dict)
async def upsert_prices(
    symbol: str,
    prices: List[PriceEODCreate],
    db: Session = Depends(get_db)
):
    """Upsert price data for a symbol"""
    try:
        repository = PriceEODRepository(db)
        
        # Convert schema objects to dictionaries
        price_data = []
        for price in prices:
            price_data.append({
                'date': price.date,
                'open': price.open,
                'high': price.high,
                'low': price.low,
                'close': price.close,
                'volume': price.volume,
                'source': price.source
            })
        
        count = repository.upsert_prices(symbol, price_data)
        
        return {
            "status": "success",
            "symbol": symbol,
            "records_processed": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}", response_model=List[PriceEODResponse])
async def get_prices(
    symbol: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get price data for a symbol within a date range"""
    try:
        repository = PriceEODRepository(db)
        prices = repository.get_prices(symbol, start_date, end_date)
        
        return [PriceEODResponse.from_orm(price) for price in prices]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/latest", response_model=PriceEODResponse)
async def get_latest_price(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get the latest price data for a symbol"""
    try:
        repository = PriceEODRepository(db)
        price = repository.get_latest_price(symbol)
        
        if not price:
            raise HTTPException(status_code=404, detail=f"No price data found for symbol {symbol}")
        
        return PriceEODResponse.from_orm(price)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{symbol}", response_model=dict)
async def delete_prices(
    symbol: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Delete price data for a symbol within a date range"""
    try:
        repository = PriceEODRepository(db)
        count = repository.delete_prices(symbol, start_date, end_date)
        
        return {
            "status": "success",
            "symbol": symbol,
            "records_deleted": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

