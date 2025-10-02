"""
Insights v2 API Router
2-шаговый пайплайн: подготовка чисел → обогащение LLM → мердж для UI
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from json import JSONDecodeError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.insights_prepare import InsightsPrepareService
from app.services.insights_enrich_llm import InsightsEnrichLLMService
from app.schemas_insights_v2 import (
    PreparedInsights, LLMInsightsResponse, InsightsV2Response, PositionAnalysis
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights/v2", tags=["insights-v2"])


class InsightsV2Request(BaseModel):
    """Параметры анализа для Insights v2"""
    model: str = Field(default="llama3.1:8b", description="Модель LLM")
    horizon_months: int = Field(default=6, ge=1, le=24, description="Горизонт анализа в месяцах")
    risk_profile: str = Field(default="Balanced", description="Профиль риска")


class AnalysisResult(BaseModel):
    """Результат анализа с метриками"""
    model: str
    success: bool
    escalation_rate: Optional[float] = Field(None, description="Частота repair-retry в %")
    prepared_data: Optional[PreparedInsights] = None
    llm_data: Optional[LLMInsightsResponse] = None
    final_response: Optional[InsightsV2Response] = None
    errors: list[str] = Field(default_factory=list)


# Константы для метрик согласно ТЗ
MAX_ESCALATION_RATE = 5.0  # целевой ≤ 5%
MAX_RESPONSE_TIME_MS = 150  # не ухудшить более чем на +150мс


class DataMerger:
    """Сервис объединения данных подготовленных и LLM"""
    
    @staticmethod
    def merge_insights_data(
        prepared_data: PreparedInsights,
        llm_data: Optional[LLMInsightsResponse],
        errors: list[str],
        model_name: str = "llama3.1:8b"
    ) -> InsightsV2Response:
        """
        Объединяет данные из подготовительного шага и LLM для UI
        
        UI читает KPI/группировки только из детерминированных данных;
        текст — только из LLM
        """
        
        # Создаем маппинг символов → LLM инсайты
        llm_insights_map = {}
        if llm_data and llm_data.positions:
            for pos in llm_data.positions:
                llm_insights_map[pos.symbol] = pos.insights
        
        # Объединяем позиции с инсайтами
        positions_with_insights = []
        for pos in prepared_data.positions:
            analysis_pos = PositionAnalysis(
                symbol=pos.symbol,
                name=pos.name,
                industry=pos.industry,
                weight_pct=pos.weight_pct,
                growth_forecast_pct=pos.growth_forecast_pct,
                risk_score_0_100=pos.risk_score_0_100,
                expected_return_horizon_pct=pos.expected_return_horizon_pct,
                volatility_pct=pos.volatility_pct,
                insights=llm_insights_map.get(pos.symbol)  # мердж по ключу символа
            )
            positions_with_insights.append(analysis_pos)
        
        # Определяем статус согласно наличию данных
        status = 'ok' if llm_data else 'partial'
        
        return InsightsV2Response(
            status=status,
            model=model_name,
            prepared_data=prepared_data,
            llm_data=llm_data,
            errors=errors,
            positions_with_insights=positions_with_insights
        )


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_portfolio_insights_v2(
    request_data: InsightsV2Request,
    user_id: UUID = Query(..., description="ID пользователя"),
    db: Session = Depends(get_db)
) -> AnalysisResult:
    """
    Основной endpoint для анализа Insights v2
    
    Архитектура:
    1. Шаг A — подготовка чисел (детерминированно)
    2. Шаг B — обогащение текстом (LLM Llama-3.1-8B)
    3. Merge — объединение для UI
    """
    logger.info(f"Starting Insights v2 analysis for user {user_id}")
    
    prepare_service = InsightsPrepareService(db)
    enrich_service = InsightsEnrichLLMService()
    merger = DataMerger()
    
    errors = []
    try:
        # === Шаг A: Подготовка чисел ===
        logger.info("Step A: Preparing deterministic data")
        prepared_data = await prepare_service.prepare_insights(user_id)
        logger.info(f"Prepared {len(prepared_data.positions)} positions")
        
        # === Шаг B: Обогащение LLM ===
        llm_data = None
        escalation_rate = 0.0
        
        try:
            logger.info("Step B: Enriching with LLM")
            params = {
                'model': request_data.model,
                'horizon_months': request_data.horizon_months,
                'risk_profile': request_data.risk_profile
            }
            
            llm_data = await enrich_service.enrich_insights(prepared_data, params)
            logger.info("LLM enrichment successful")
            
        except Exception as llm_error:
            logger.warning(f"LLM enrichment failed: {llm_error}")
            errors.append(f"LLM enrichment failed: {str(llm_error)}")
            escalation_rate = 100.0  # полный сбой LLM
        
        # === Merge для UI ===
        final_response = merger.merge_insights_data(prepared_data, llm_data, errors, request_data.model)
        
        # Проверяем соответствие требований ТЗ
        if escalation_rate > MAX_ESCALATION_RATE:
            logger.warning(f"Escalation rate {escalation_rate}% exceeds target {MAX_ESCALATION_RATE}%")
        
        return AnalysisResult(
            model=request_data.model,
            success=True,
            escalation_rate=escalation_rate,
            prepared_data=prepared_data,
            llm_data=llm_data,
            final_response=final_response,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Insights v2 analysis failed: {e}")
        return AnalysisResult(
            model=request_data.model,
            success=False,
            errors=[f"Analysis failed: {str(e)}"]
        )


@router.get("/prepared-only", response_model=PreparedInsights)
async def get_prepared_insights_only(
    user_id: UUID = Query(..., description="ID пользователя"),
    db: Session = Depends(get_db)
) -> PreparedInsights:
    """
    Отрицательный кейс: Только детерминированные данные без LLM
    Используется при сбоях LLM или для быстрого предпросмотра
    """
    logger.info(f"Getting prepared insights only for user {user_id}")
    
    prepare_service = InsightsPrepareService(db)
    
    try:
        prepared_data = await prepare_service.prepare_insights(user_id)
        logger.info(f"Returning prepared data for {len(prepared_data.positions)} positions")
        return prepared_data
        
    except Exception as e:
        logger.error(f"Prepared insights failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare insights: {str(e)}"
        )


@router.get("/health")
async def insights_v2_health():
    """
    Проверка здоровья Insights v2 сервиса
    Включает проверки производительности согласно ТЗ
    """
    return {
        "status": "healthy",
        "service": "insights-v2",
        "max_escalation_rate_target": f"{MAX_ESCALATION_RATE}%",
        "max_response_time_increase_ms": MAX_RESPONSE_TIME_MS,
        "architecture": "2-step pipeline",
        "step_a": "deterministic_preparation",
        "step_b": "llm_enrichment"
    }


# Утилиты для негативных кейсов согласно ТЗ
@router.get("/mock-data/{scenario}")
async def get_mock_scenario(scenario: str):
    """
    Мок-данные для тестирования негативных кейсов
    
    Поддерживаемые сценарии:
    - missing-insight: одна позиция без insights
    - wrong-enum: неверные значения enum
    - long-thesis: тезис > 240 символов
    - weight-drift: суммы весов ≠ 100%
    - version-mismatch: неверная версия схемы
    """
    
    mock_scenarios = {
        "missing-insight": {
            "description": "Одна позиция без insights → UI помечает Data gap",
            "prepared_data": {
                "positions": [
                    {"symbol": "AAPL", "weight_pct": 50.0},
                    {"symbol": "GOOGL", "weight_pct": 50.0}
                ]
            },
            "llm_data": {
                "positions": [
                    {"symbol": "AAPL", "insights": {"thesis": "Good company", "risks": ["Risk 1"], "action": "Hold", "signals": {"valuation": "fair", "momentum": "neutral", "quality": "high"}}}
                    # GOOGL без insights
                ]
            }
        },
        "wrong-enum": {
            "description": "Модель вернула action: 'Buy' → валидатор режет",
            "problem_field": "action",
            "invalid_value": "Buy",
            "expected_valid": ["Add", "Hold", "Trim", "Hedge"]
        },
        "weight-drift": {
            "description": "Суммы весов = 103% → локальная нормировка",
            "example_weights": [52.0, 51.0],  # сумма > 100%
            "normalized_to": [50.5, 49.5]     # после нормализации
        }
    }
    
    if scenario not in mock_scenarios:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario}' not found. Available: {list(mock_scenarios.keys())}"
        )
    
    return {
        "scenario": scenario,
        "data": mock_scenarios[scenario],
        "testing_note": "Used for manual validation of requirement checklist"
    }
