import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.price_service import PriceService

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health():
    return {"status": "ok"}

@router.get("/stooq")
def health_stooq(db: Session = Depends(get_db)):
    """Проверяет доступность Stooq API"""
    start_time = time.time()
    
    try:
        service = PriceService(db)
        is_available = service.check_stooq_availability()
        response_time = time.time() - start_time
        
        return {
            "status": "ok" if is_available else "error",
            "stooq_available": is_available,
            "response_time_ms": round(response_time * 1000, 2)
        }
    except Exception as e:
        response_time = time.time() - start_time
        return {
            "status": "error",
            "stooq_available": False,
            "response_time_ms": round(response_time * 1000, 2),
            "error": str(e)
        }
