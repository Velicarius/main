"""Crypto quotes API endpoint"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.database import get_db
from app.pricing.crypto.service import get_crypto_price_service
from app.core.config import settings
from app.pricing.crypto.types import ALLOWED_CRYPTO_SYMBOLS
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crypto/quotes", tags=["crypto-quotes"])


@router.get("")
async def get_crypto_quotes(
    symbols: Optional[str] = Query(None, description="Comma-separated crypto symbols (e.g., 'BTC,ETH,SOL')"),
    db: Session = Depends(get_db)
):
    """
    Get current crypto prices for symbols
    
    Args:
        symbols: Comma-separated list of crypto symbols
        
    Returns:
        Dict with symbol -> price mapping
    """
    if not settings.feature_crypto_positions:
        raise HTTPException(status_code=403, detail="Crypto positions feature is disabled")
    
    if not symbols:
        raise HTTPException(status_code=400, detail="symbols parameter is required")
    
    # Parse symbols
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="No valid symbols provided")
    
    # Validate symbols
    invalid_symbols = [s for s in symbol_list if s not in ALLOWED_CRYPTO_SYMBOLS]
    if invalid_symbols:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid symbols: {invalid_symbols}. Allowed symbols: {', '.join(sorted(ALLOWED_CRYPTO_SYMBOLS))}"
        )
    
    try:
        crypto_service = get_crypto_price_service()
        
        if len(symbol_list) == 1:
            # Single symbol request
            symbol = symbol_list[0]
            crypto_price = await crypto_service.get_price(symbol)
            
            if crypto_price:
                return {
                    "success": True,
                    "data": {
                        symbol: {
                            "price_usd": float(crypto_price.price_usd),
                            "timestamp": crypto_price.timestamp.isoformat(),
                            "source": crypto_price.source
                        }
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get price for {symbol}",
                    "data": {}
                }
        else:
            # Batch request
            prices = await crypto_service.get_batch_prices(symbol_list)
            
            result_data = {}
            for symbol, crypto_price in prices.items():
                if crypto_price:
                    result_data[symbol] = {
                        "price_usd": float(crypto_price.price_usd),
                        "timestamp": crypto_price.timestamp.isoformat(),
                        "source": crypto_price.source
                    }
                else:
                    result_data[symbol] = None
            
            return {
                "success": True,
                "data": result_data
            }
            
    except Exception as e:
        logger.error(f"Error getting crypto quotes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get crypto quotes: {str(e)}")


@router.get("/allowed")
async def get_allowed_crypto_symbols():
    """Get list of allowed crypto symbols"""
    if not settings.feature_crypto_positions:
        raise HTTPException(status_code=403, detail="Crypto positions feature is disabled")
    
    return {
        "success": True,
        "allowed_symbols": sorted(list(ALLOWED_CRYPTO_SYMBOLS)),
        "count": len(ALLOWED_CRYPTO_SYMBOLS)
    }


@router.get("/cache-stats")
async def get_cache_stats():
    """Get crypto price service cache statistics"""
    if not settings.feature_crypto_positions:
        raise HTTPException(status_code=403, detail="Crypto positions feature is disabled")
    
    try:
        crypto_service = get_crypto_price_service()
        stats = crypto_service.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")
