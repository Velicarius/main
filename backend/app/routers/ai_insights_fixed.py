"""
Исправленный Insights API - простой и рабочий router для insights
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.unified_insights_service import (
    UnifiedInsightsService,
    UnifiedInsightsRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/insights/fixed", tags=["ai-insights-fixed"])

class InsightsRequest(BaseModel):
    """Упрощенный запрос для insights"""
    horizon_months: int = Field(default=6, ge=1, le=24)
    risk_profile: str = Field(default="Balanced")
    model: str = Field(default="llama3.1:8b")
    temperature: float = Field(default=0.2)
    language: str = Field(default="ru")
    cache_mode: str = Field(default="default")

# Создаем сервис
insights_service = UnifiedInsightsService()

@router.post("/")
async def get_insights_fixed(
    request: InsightsRequest,
    user_id: UUID = Query(..., description="ID пользователя"),
    db: Session = Depends(get_db)
):
    """Простой endpoint для получения insights"""
    
    try:
        # Use request settings or defaults from environment
        from app.core.config import settings
        
        model = request.model or settings.default_insights_model or "llama3.1:8b"
        provider = "ollama" if model.startswith(('llama', 'gemma', 'qwen', 'mistral', 'codellama')) else "openai"
        
        # Преобразуем запрос с настройками по умолчанию
        request_dict = request.dict()
        request_dict['model'] = model
        service_request = UnifiedInsightsRequest(**request_dict)
        
        # Получаем insights
        response = await insights_service.get_insights(user_id, service_request, db)
        
        # Возвращаем данные
        return {
            "success": True,
            "cached": response.cached,
            "model": response.model_name,
            "llm_ms": response.llm_ms,
            "compute_ms": response.compute_ms,
            "data": response.data
        }
        
    except Exception as e:
        logger.error(f"Insights request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )







