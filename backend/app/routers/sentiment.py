"""
API роутер для анализа сентимента финансовых новостей
Включает внутренние батч-эндпойнты и UI интеграцию
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas_sentiment import (
    SentimentRequest, SentimentScoreResponse, PortfolioSentimentMetrics,
    SentimentGrouping, PositionSentimentData, PositionNewsItem
)
from app.services.sentiment_analysis import SentimentAnalysisService
from app.services.sentiment_cache import SentimentAggregationService
from app.models.position import Position
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/sentiment", tags=["sentiment-analysis"])

# =============================================================================
# Внутренние батч-эндпойнты (используются Celery задачами)
# =============================================================================

@router.post("/score", response_model=SentimentScoreResponse)
async def score_sentiment_batch(
    request: SentimentRequest
) -> SentimentScoreResponse:
    """
    Внутренний батч-эндпойнт для анализа сентимента новостей
    
    Используется Celery задачами и внутренними процессами.
    Возвращает только sentiment, confidence, strength (без творческих текстов).
    """
    
    logger.info(f"Sentiment batch scoring request: {request.model} for {len(request.items)} items")
    
    try:
        sentiment_service = SentimentAnalysisService()
        result = await sentiment_service.analyze_sentiment_batch(request)
        
        logger.info(f"Sentiment batch completed: {result.model}, {result.successful}/{result.total_processed} successful")
        
        return result
        
    except Exception as e:
        logger.error(f"Sentiment batch scoring failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentiment analysis failed: {str(e)}"
        )

# =============================================================================
# Агрегация данных (для обновления кэша)
# =============================================================================

@router.post("/aggregate/{symbol}")
async def aggregate_symbol_sentiment(
    symbol: str,
    sentiment_results: List[Dict[str, Any]],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Агрегация sentiment данных для конкретного символа
    """
    
    logger.info(f"Aggregating sentiment data for {symbol}")
    
    try:
        aggregation_service = SentimentAggregationService()
        
        # Конвертируем JSON в SentimentResult объекты
        from app.schemas_sentiment import SentimentResult, SentimentLabel
        
        results = []
        for item in sentiment_results:
            result = SentimentResult(
                symbol=item['symbol'],
                sentiment=SentimentLabel(item['sentiment']),
                confidence=item['confidence'],
                strength=item['strength'],
                note=item.get('note')
            )
            results.append(result)
        
        # Агрегируем для 7d и 30d окон
        sentiment_7d = aggregation_service.aggregate_symbol_sentiment(symbol, results, 7)
        sentiment_30d = aggregation_service.aggregate_symbol_sentiment(symbol, results, 30)
        
        # Кэшируем результат
        await aggregation_service.cache_sentiment_data(
            symbol, sentiment_7d, sentiment_30d, "finllama"
        )
        
        return {
            "symbol": symbol,
            "sentiment_7d": sentiment_7d,
            "sentiment_30d": sentiment_30d,
            "cached_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Sentiment aggregation failed for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Aggregation failed: {str(e)}"
        )

# =============================================================================
# UI интеграция (для Insights страницы)
# =============================================================================

@router.get("/portfolio/{user_id}", response_model=PortfolioSentimentMetrics)
async def get_portfolio_sentiment(
    user_id: UUID,
    window_days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db)
) -> PortfolioSentimentMetrics:
    """
    Получение сентимент метрик для портфеля пользователя
    """
    
    logger.info(f"Getting portfolio sentiment for user {user_id}, window: {window_days}d")
    
    try:
        # Получаем позиции пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        positions_query = (
            db.query(Position)
            .filter(Position.user_id == user_id)
            .all()
        )
        
        if not positions_query:
            # Пустой портфель
            return PortfolioSentimentMetrics(
                portfolio_sentiment_7d=0.0,
                portfolio_sentiment_30d=0.0,
                portfolio_coverage_7d=0,
                portfolio_coverage_30d=0,
                portfolio_delta_7v30=0.0,
                bullish_count=0,
                neutral_count=0,
                bear_count=0,
                weighted_by_position=True
            )
        
        # Извлекаем веса позиций
        position_weights = {}
        total_value = 0.0
        
        for position in positions_query:
            if position.symbol and position.current_value:
                position_weight = float(position.weight_percentage or 0)
                position_weights[position.symbol] = position_weight
                total_value += position.current_value
        
        # Нормализуем веса до 100%
        if total_value > 0:
            position_weights = {
                symbol: weight / total_value * 100 
                for symbol, weight in position_weights.items()
            }
        
        # Получаем sentiment данные из кэша
        aggregation_service = SentimentAggregationService()
        
        symbol_sentiment_7d = {}
        symbol_sentiment_30d = {}
        
        for symbol in position_weights.keys():
            cached_data = await aggregation_service.get_cached_sentiment(symbol)
            if cached_data:
                symbol_sentiment_7d[symbol] = {
                    'sentiment_score': cached_data.sentiment_score_7d,
                    'coverage_count': cached_data.coverage_count_7d,
                    'confidence_avg': cached_data.confidence_avg
                }
                symbol_sentiment_30d[symbol] = {
                    'sentiment_score': cached_data.sentiment_score_30d,
                    'coverage_count': cached_data.coverage_count_30d,
                    'confidence_avg': cached_data.confidence_avg
                }
        
        # Вычисляем портфельные метрики
        portfolio_metrics = aggregation_service.calculate_portfolio_sentiment(
            position_weights, symbol_sentiment_7d, symbol_sentiment_30d
        )
        
        return portfolio_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get portfolio sentiment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio sentiment analysis failed: {str(e)}"
        )

@router.get("/grouping/{user_id}", response_model=SentimentGrouping)
async def get_sentiment_grouping(
    user_id: UUID,
    timeframe: str = Query(default="30d", regex="^(7d|30d)$"),
    db: Session = Depends(get_db)
) -> SentimentGrouping:
    """
    Получение группировки позиций по сентименту
    """
    
    logger.info(f"Getting sentiment grouping for user {user_id}, timeframe: {timeframe}")
    
    try:
        # Получаем позиции и кэшированные sentiment данные
        positions_query = (
            db.query(Position)
            .filter(Position.user_id == user_id)
            .all()
        )
        
        if not positions_query:
            return SentimentGrouping(
                timeframe=timeframe,
                buckets=[],
                total_coverage=0,
                fallback_rate=0.0
            )
        
        # Извлекаем данные позиций
        position_weights = {}
        total_value = sum(p.current_value or 0 for p in positions_query)
        
        for position in positions_query:
            if position.symbol and position.current_value:
                weight_pct = (position.current_value / total_value * 100) if total_value > 0 else 0
                position_weights[position.symbol] = weight_pct
        
        # Получаем sentiment данные
        aggregation_service = SentimentAggregationService()
        
        symbol_sentiment_data = {}
        for symbol in position_weights.keys():
            cached_data = await aggregation_service.get_cached_sentiment(symbol)
            if cached_data:
                key = 'sentiment_score_30d' if timeframe == '30d' else 'sentiment_score_7d'
                coverage_key = 'coverage_count_30d' if timeframe == '30d' else 'coverage_count_7d'
                
                symbol_sentiment_data[symbol] = {
                    'sentiment_score': getattr(cached_data, key),
                    'coverage_count': getattr(cached_data, coverage_key),
                    'confidence_avg': cached_data.confidence_avg
                }
        
        # Создаем группировку
        grouping = aggregation_service.create_sentiment_grouping(
            symbol_sentiment_data, position_weights, timeframe
        )
        
        return grouping
        
    except Exception as e:
        logger.error(f"Failed to get sentiment grouping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentiment grouping failed: {str(e)}"
        )

@router.get("/positions/{user_id}", response_model=List[PositionSentimentData])
async def get_positions_sentiment(
    user_id: UUID,
    top_news_count: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db)
) -> List[PositionSentimentData]:
    """
    Получение sentiment данных для всех позиций пользователя
    """
    
    logger.info(f"Getting positions sentiment for user {user_id}")
    
    try:
        # Получаем позиции
        positions_query = (
            db.query(Position)
            .filter(Position.user_id == user_id)
            .all()
        )
        
        if not positions_query:
            return []
        
        # Получаем sentiment данные для каждой позиции
        aggregation_service = SentimentAggregationService()
        position_sentiment_data = []
        
        for position in positions_query:
            if not position.symbol:
                continue
            
            cached_data = await aggregation_service.get_cached_sentiment(position.symbol)
            
            if cached_data:
                # Получаем топ новости (симуляция - обычно тут был бы отдельный запрос)
                top_news = [
                  PositionNewsItem(
                      headline=f"Recent news about {position.symbol}",
                      published_at=datetime.utcnow() - timedelta(hours=i*6),
                      sentiment="positive" if i % 3 == 0 else "neutral",
                      confidence=0.7 + i * 0.1,
                      source_weight=1.0
                  )
                  for i in range(min(top_news_count, 3))
                ]
                
                position_data = PositionSentimentData(
                    symbol=position.symbol,
                    sentiment_score_7d=cached_data.sentiment_score_7d,
                    sentiment_score_30d=cached_data.sentiment_score_30d,
                    confidence_7d=cached_data.confidence_avg,
                    confidence_30d=cached_data.confidence_avg,
                    delta_7v30=cached_data.delta_7v30,
                    coverage_count_7d=cached_data.coverage_count_7d,
                    coverage_count_30d=cached_data.coverage_count_30d,
                    top_news=top_news,
                    has_data_gap=cached_data.coverage_count_30d == 0,
                    model_used=cached_data.model_used,
                    last_updated=cached_data.last_updated
                )
            else:
                # Данных нет - создаем пустую структуру
                position_data = PositionSentimentData(
                    symbol=position.symbol,
                    sentiment_score_7d=0.0,
                    sentiment_score_30d=0.0,
                    confidence_7d=0.0,
                    confidence_30d=0.0,
                    delta_7v30=0.0,
                    coverage_count_7d=0,
                    coverage_count_30d=0,
                    top_news=[],
                    has_data_gap=True,
                    model_used="none",
                    last_updated=datetime.utcnow()
                )
            
            position_sentiment_data.append(position_data)
        
        return position_sentiment_data
        
    except Exception as e:
        logger.error(f"Failed to get positions sentiment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Positions sentiment analysis failed: {str(e)}"
        )

# =============================================================================
# Управление кэшем (административные эндпойнты)
# =============================================================================

@router.delete("/cache/{symbol}")
async def invalidate_sentiment_cache(
    symbol: str
) -> Dict[str, str]:
    """
    Инвалидация кэша для конкретного символа (для форс-рефреша)
    """
    
    try:
        aggregation_service = SentimentAggregationService()
        await aggregation_service.invalidate_cache(symbol)
        
        return {"message": f"Cache invalidated for {symbol}"}
        
    except Exception as e:
        logger.error(f"Cache invalidation failed for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {str(e)}"
        )

@router.delete("/cache")
async def invalidate_all_sentiment_cache() -> Dict[str, str]:
    """
    Полная инвалидация sentiment кэша
    """
    
    try:
        aggregation_service = SentimentAggregationService()
        await aggregation_service.invalidate_cache()
        
        return {"message": "All sentiment cache invalidated"}
        
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {str(e)}"
        )
