"""
Insights v2 Data Schemas согласно техническому заданию
Focus: строгий контракт, разделение вычислений и генерации текста, валидация
"""

from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID


# === Request/Response Models ===

class InsightsV2Request(BaseModel):
    """Request для полного анализа Insights v2"""
    horizon_months: int = Field(default=12, ge=1, le=60, description="Горизонт анализа в месяцах")
    risk_profile: Literal['conservative', 'balanced', 'aggressive'] = Field(
        default='balanced', description="Профиль риска"
    )
    model: str = Field(default="llama-3.1-8b", description="Модель LLM для анализа")


class InsightsV2Response(BaseModel):
    """Response для полного анализа Insights v2"""
    status: Literal['ok', 'partial', 'error', 'stale']
    model: str
    prepared_data: 'PreparedInsights'
    llm_data: Optional['LLMInsightsResponse'] = None
    errors: List[str] = Field(default_factory=list)
    positions_with_insights: List['PositionAnalysis']
    escalation_rate: Optional[float] = None


# === Utility Functions ===

def validateInsightsResponse(response_data: Dict[str, Any]) -> bool:
    """Валидация данных response для UI"""
    try:
        # Основные проверки
        required_fields = ['status', 'model', 'prepared_data', 'positions_with_insights']
        
        for field in required_fields:
            if field not in response_data:
                return False
        
        # Проверяем статус
        if response_data['status'] not in ['ok', 'partial', 'error', 'stale']:
            return False
        
        # Проверяем prepared_data
        prepared = response_data['prepared_data']
        if not isinstance(prepared, dict):
            return False
            
        required_prepared = ['summary', 'grouping', 'positions']
        for field in required_prepared:
            if field not in prepared:
                return False
        
        return True
        
    except (KeyError, TypeError, ValueError):
        return False


# === Шаг A: PreparedInsights (чистые числа, детерминированно) ===

class PositionPrepared(BaseModel):
    """Подготовленные данные позиции для LLM"""
    symbol: str = Field(..., description="Символ инструмента")
    name: str = Field(..., description="Название компании")
    industry: str = Field(..., description="Отрасль")
    weight_pct: float = Field(..., description="Вес в портфеле (%)")
    growth_forecast_pct: Optional[float] = Field(None, description="Прогноз роста (%)")
    risk_score_0_100: Optional[float] = Field(None, description="Оценка риска 0-100")
    expected_return_horizon_pct: float = Field(..., description="Ожидаемая доходность за горизонт (%)")
    volatility_pct: Optional[float] = Field(None, description="Волатильность (%)")

    @validator('weight_pct')
    def validate_weight(cls, v):
        if v < 0:
            raise ValueError('Weight cannot be negative')
        return v


class PortfolioSummary(BaseModel):
    """Сводные KPI портфеля"""
    total_equity_usd: float = Field(..., description="Общая стоимость")
    free_usd: float = Field(..., description="Свободные средства USD")
    portfolio_value_usd: float = Field(..., description="Стоимость портфеля")
    expected_return_horizon_pct: float = Field(..., description="Ожидаемая доходность за горизонт")
    volatility_annualized_pct: Optional[float] = Field(None, description="Волатильность аннуализированная")
    risk_score_0_100: Optional[float] = Field(None, description="Оценка риска портфеля")
    risk_class: Literal['Low', 'Moderate', 'High'] = Field(..., description="Класс риска")
    as_of: str = Field(..., description="Дата расчета")


class GroupingData(BaseModel):
    """Группировка позиций"""
    name: str = Field(..., description="Название группы")
    weight_pct: float = Field(..., description="Общий вес группы (%)")
    avg_expected_return_pct: Optional[float] = Field(None, description="Средневзвешенная доходность")
    avg_risk_score: Optional[float] = Field(None, description="Средневзвешенный риск")
    positions: List[str] = Field(..., description="Символы позиций в группе")


class PreparedInsights(BaseModel):
    """Шаг A: Подготовленные данные для UI и LLM"""
    schema_version: Literal['insights.v2'] = 'insights.v2'
    summary: PortfolioSummary
    grouping: Dict[str, List[GroupingData]] = Field(
        ..., 
        description="Группировки: by_industry, by_growth_bucket, by_risk_bucket"
    )
    positions: List[PositionPrepared]
    
    @validator('positions')
    def validate_positions(cls, v):
        if not v:
            raise ValueError('Must have at least one position')
        return v

    @validator('positions')
    def validate_weights(cls, v):
        """Проверяем что сумма весов приблизительно равна 100%"""
        total_weight = sum(p.weight_pct for p in v)
        if abs(total_weight - 100.0) > 5.0:  # допуск ±5%
            # Автоматическая нормализация для диаграмм
            for p in v:
                p.weight_pct = (p.weight_pct / total_weight) * 100.0
        return v


# === Шаг B: LLM Request/Response схема ===

class LLMInsightSignals(BaseModel):
    """Сигналы оценок LLM"""
    valuation: Literal['cheap', 'fair', 'expensive'] = Field(
        ..., 
        description="Оценка дороговизны"
    )
    momentum: Literal['up', 'flat', 'down', 'neutral'] = Field(
        ..., 
        description="Моментум движение"
    )
    quality: Literal['high', 'med', 'low'] = Field(
        ..., 
        description="Качество компании"
    )


class LLMInsight(BaseModel):
    """Пер-позиционный инсайт от LLM"""
    thesis: str = Field(..., description="Краткий тезис до 240 символов")
    risks: List[str] = Field(..., description="Список рисков (1-3 пункта)")
    action: Literal['Add', 'Hold', 'Trim', 'Hedge'] = Field(
        ..., 
        description="Рекомендуемое действие"
    )
    signals: LLMInsightSignals

    @validator('thesis')
    def validate_thesis_length(cls, v):
        if len(v) > 240:
            return v[:237] + "..."
        return v

    @validator('risks')
    def validate_risks(cls, v):
        if len(v) < 1:
            raise ValueError('Must have at least one risk')
        if len(v) > 3:
            return v[:3]
        return v


class LLMInsightPosition(BaseModel):
    """Позиция с инсайтом для UI"""
    symbol: str = Field(..., description="Символ должен совпадать с запросом")
    insights: LLMInsight


class LLMInsightsResponse(BaseModel):
    """Шаг B: Ответ LLM (только тексты)"""
    schema_version: Literal['insights.v2'] = 'insights.v2'
    as_of_copy: Optional[str] = Field(None, description="Эхо даты для трассировки")
    positions: List[LLMInsightPosition]


# === Объединенный финальный ответ для UI ===

class PositionAnalysis(BaseModel):
    """Финальная анализная позиция для UI"""
    symbol: str
    name: str
    industry: str
    weight_pct: float
    growth_forecast_pct: Optional[float]
    risk_score_0_100: Optional[float]
    expected_return_horizon_pct: float
    volatility_pct: Optional[float]
    
    # Данные от LLM
    insights: Optional[LLMInsight] = Field(None, description="LLM инсайт для этой позиции")

    # Computed свойства
    @property
    def risk_class(self) -> Literal['Low', 'Moderate', 'High']:
        """UI вычисляет бейдж самостоятельно"""
        if not self.risk_score_0_100:
            return 'Moderate'
        if self.risk_score_0_100 <= 33:
            return 'Low'
        elif self.risk_score_0_100 <= 66:
            return 'Moderate'
        else:
            return 'High'

    @property
    def growth_category(self) -> Literal['High', 'Mid', 'Low']:
        """UI вычисляет бейдж самостоятельно"""
        if not self.growth_forecast_pct:
            return 'Low'
        if self.growth_forecast_pct >= 15:
            return 'High'
        elif self.growth_forecast_pct >= 5:
            return 'Mid'
        else:
            return 'Low'


