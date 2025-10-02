"""
Схемы данных для FinLlama Sentiment Analysis
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# === Enum для типов сентимента ===

class SentimentLabel(str, Enum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"

class SentimentModel(str, Enum):
    FINLLAMA = "finllama"
    FINBERT = "finbert"

# === Входные данные ===

class SentimentRequest(BaseModel):
    """Запрос на анализ сентимента"""
    model: SentimentModel = Field(default=SentimentModel.FINLLAMA)
    items: List['SentimentItem'] = Field(..., min_items=1, max_items=100)

class SentimentItem(BaseModel):
    """Отдельная новость для анализа"""
    symbol: str = Field(..., min_length=1, max_length=10)
    published_at: datetime
    text: str = Field(..., min_length=10, max_length=500)
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Text cannot be empty')
        return v.strip()

# === Результаты анализа ===

class SentimentResult(BaseModel):
    """Результат анализа одной новости"""
    symbol: str
    sentiment: SentimentLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    strength: float = Field(..., ge=0.0, le=1.0)
    note: Optional[str] = None  # Для отметок типа "fallback", "low_confidence"

class SentimentScoreResponse(BaseModel):
    """Ответ API анализа сентимента"""
    model: SentimentModel
    results: List[SentimentResult]
    as_of: datetime = Field(default_factory=datetime.utcnow)
    
    # Статистика обработки
    total_processed: int
    successful: int
    failed: int
    avg_confidence: float
    
    @validator('results')
    def validate_results(cls, v):
        for result in v:
            if result.sentiment == SentimentLabel.NEUTRAL and result.confidence < 0.5:
                result.confidence = 0.0  # Нормализация low confidence
                result.note = "confidence_normalized"
        return v

# === Кэш и хранение ===

class CachedSentimentData(BaseModel):
    """Структура для кэша в Redis"""
    symbol: str
    sentiment_score_7d: float = Field(..., ge=-1.0, le=1.0)
    sentiment_score_30d: float = Field(..., ge=-1.0, le=1.0)
    coverage_count_7d: int = Field(..., ge=0)
    coverage_count_30d: int = Field(..., ge=0)
    delta_7v30: float  # Разница между 7d и 30d
    confidence_avg: float = Field(..., ge=0.0, le=1.0)
    model_used: SentimentModel
    last_updated: datetime
    ttl_hours: int = 12

class PortfolioSentimentMetrics(BaseModel):
    """Метрики сентимента для портфеля"""
    portfolio_sentiment_7d: float = Field(..., ge=-1.0, le=1.0)
    portfolio_sentiment_30d: float = Field(..., ge=-1.0, le=1.0)
    portfolio_coverage_7d: int = Field(..., ge=0)
    portfolio_coverage_30d: int = Field(..., ge=0)
    portfolio_delta_7v30: float
    bullish_count: int = Field(..., ge=0)
    neutral_count: int = Field(..., ge=0)
    bear_count: int = Field(..., ge=0)
    weighted_by_position: bool
    as_of: datetime = Field(default_factory=datetime.utcnow)

# === Группировки для UI ===

class SentimentBucket(BaseModel):
    """Корзина сентимента для группировки"""
    bucket_name: str  # "Bullish", "Neutral", "Bearish"
    sentiment_range: tuple[float, float]  # min, max для bucket
    weight_pct: float = Field(..., ge=0.0, le=100.0)
    avg_sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    positions: List[str]  # Список тикеров в группе
    count: int = Field(..., ge=0)

class SentimentGrouping(BaseModel):
    """Группировка позиций по сентименту"""
    timeframe: str  # "7d" или "30d"
    buckets: List[SentimentBucket]
    total_coverage: int = Field(..., ge=0)
    fallback_rate: float = Field(..., ge=0.0, le=1.0)

class PositionNewsItem(BaseModel):
    """Новость для позиции (top-3)"""
    headline: str = Field(..., max_length=200)
    published_at: datetime
    sentiment: SentimentLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_weight: float = Field(default=1.0, ge=0.0, le=2.0)

class PositionSentimentData(BaseModel):
    """Сентiment данные для конкретной позиции"""
    symbol: str
    sentiment_score_7d: float = Field(..., ge=-1.0, le=1.0)
    sentiment_score_30d: float = Field(..., ge=-1.0, le=1.0)
    confidence_7d: float = Field(..., ge=0.0, le=1.0)
    confidence_30d: float = Field(..., ge=0.0, le=1.0)
    delta_7v30: float
    coverage_count_7d: int = Field(..., ge=0)
    coverage_count_30d: int = Field(..., ge=0)
    top_news: List[PositionNewsItem] = Field(default_factory=list, max_items=3)
    has_data_gap: bool = False
    model_used: SentimentModel
    last_updated: datetime

# === Конфигурация ===

class SentimentConfig(BaseModel):
    """Конфигурация системы анализа сентимента"""
    
    model_config = {"protected_namespaces": ()}
    enabled: bool = Field(default=True)
    model_primary: SentimentModel = Field(default=SentimentModel.FINLLAMA)
    model_fallback: SentimentModel = Field(default=SentimentModel.FINBERT)
    default_window_days: int = Field(default=30)
    decay_halflife_days: float = Field(default=14.0)
    cache_ttl_hours: int = Field(default=12)
    batch_size_max: int = Field(default=100)
    confidence_threshold: float = Field(default=0.5)
    low_signal_threshold: float = Field(default=0.9)  # Если >90% neutral
    
    # Пороговые значения для UI
    bullish_threshold: float = Field(default=0.2)
    bearish_threshold: float = Field(default=-0.2)
    trend_threshold: float = Field(default=0.1)

# Обновление рекурсивных ссылок
SentimentRequest.model_rebuild()
