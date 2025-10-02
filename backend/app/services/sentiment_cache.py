"""
Сервис для агрегации, кэширования и управления sentiment данных
Включает вычисление взвешенных средних, portfolio метрик и группировок
"""

import logging
import json
import redis
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import math

from app.schemas_sentiment import (
    SentimentScoreResponse, SentimentResult, SentimentLabel, SentimentBucket,
    SentimentGrouping, PortfolioSentimentMetrics, PositionSentimentData,
    PositionNewsItem, CachedSentimentData, SentimentConfig
)

logger = logging.getLogger(__name__)

class SentimentAggregationService:
    """Сервис для агрегации sentiment данных по временным окнам"""
    
    def __init__(self):
        self.config = SentimentConfig()
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        
    def calculate_exponential_decay_weight(self, age_hours: float, halflife_days: float) -> float:
        """Вычисление экспоненциального веса по возрасту новости"""
        
        # Конвертируем период полураспада в часы
        halflife_hours = halflife_days * 24
        
        # Экспоненциальное убывание: weight = 2^(-age / halflife)
        decay_factor = age_hours / halflife_hours
        weight = math.pow(2, -decay_factor)
        
        return min(1.0, max(0.001, weight))  # Минимальный вес чтобы избежать нуля
    
    def aggregate_symbol_sentiment(
        self, 
        symbol: str, 
        sentiment_results: List[SentimentResult],
        window_days: int
    ) -> Dict[str, float]:
        """Агрегация sentiment для конкретного тикера по окну"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=window_days)
        
        # Фильтруем результаты по окну
        relevant_results = [
            r for r in sentiment_results 
            if datetime.fromisoformat(r.symbol.split('_')[1] if '_' in r.symbol else str(datetime.utcnow())) >= cutoff_date
        ]
        
        if not relevant_results:
            return {
                'sentiment_score': 0.0,
                'coverage_count': 0,
                'confidence_avg': 0.0,
                'positive_count': 0,
                'neutral_count': 0,
                'negative_count': 0
            }
        
        # Вычисляем взвешенные средние
        total_weight = 0.0
        weighted_sentiment_sum = 0.0
        confidence_sum = 0.0
        
        # Считаем количество по категориям
        category_counts = defaultdict(int)
        
        for result in relevant_results:
            # Конвертируем sentiment в числовую шкалу [-1, 1]
            sentiment_score = self._sentiment_to_score(result.sentiment) * result.strength
            
            # Вес на основе возраста и источника
            age_hours = (datetime.utcnow() - datetime.fromisoformat(result.symbol.split('_')[1] if '_' in result.symbol else str(datetime.utcnow()))).total_seconds() / 3600
            weight = self.calculate_exponential_decay_weight(age_hours, self.config.decay_halflife_days)
            
            # Вес источника (предполагаем базовый 1.0, можно расширить)
            source_weight = 1.0
            
            total_weight += weight * source_weight
            weighted_sentiment_sum += sentiment_score * weight * source_weight
            confidence_sum += result.confidence
            
            # Подсчет категорий
            if result.sentiment == SentimentLabel.POSITIVE:
                category_counts['positive'] += 1
            elif result.sentiment == SentimentLabel.NEGATIVE:
                category_counts['negative'] += 1
            else:
                category_counts['neutral'] += 1
        
        # Вычисляем финальные метрики
        final_sentiment_score = weighted_sentiment_sum / total_weight if total_weight > 0 else 0.0
        avg_confidence = confidence_sum / len(relevant_results)
        
        return {
            'sentiment_score': max(-1.0, min(1.0, final_sentiment_score)),
            'coverage_count': len(relevant_results),
            'confidence_avg': avg_confidence,
            'positive_count': category_counts['positive'],
            'neutral_count': category_counts['neutral'],
            'negative_count': category_counts['negative']
        }
    
    def _sentiment_to_score(self, sentiment: SentimentLabel) -> float:
        """Конвертация sentiment в числовую шкалу"""
        mapping = {
            SentimentLabel.NEGATIVE: -1.0,
            SentimentLabel.NEUTRAL: 0.0,
            SentimentLabel.POSITIVE: 1.0
        }
        return mapping.get(sentiment, 0.0)
    
    def calculate_portfolio_sentiment(
        self,
        position_weights: Dict[str, float],
        symbol_sentiment_7d: Dict[str, Dict[str, float]],
        symbol_sentiment_30d: Dict[str, Dict[str, float]]
    ) -> PortfolioSentimentMetrics:
        """Вычисление портфельного сентимента с учетом весов позиций"""
        
        portfolio_weight_sum_7d = 0.0
        portfolio_weight_sum_30d = 0.0
        portfolio_sentiment_sum_7d = 0.0
        portfolio_sentiment_sum_30d = 0.0
        
        bullish_count = 0
        neutral_count = 0
        bear_count = 0
        
        # Взвешенная сумма
        for symbol, position_weight in position_weights.items():
            if symbol in symbol_sentiment_7d:
                sentiment_7d = symbol_sentiment_7d[symbol]['sentiment_score']
                coverage_7d = symbol_sentiment_7d[symbol]['coverage_count']
                
                portfolio_weight_sum_7d += position_weight
                portfolio_sentiment_sum_7d += sentiment_7d * position_weight
            
            if symbol in symbol_sentiment_30d:
                sentiment_30d = symbol_sentiment_30d[symbol]['sentiment_score']
                coverage_30d = symbol_sentiment_30d[symbol]['coverage_count']
                
                portfolio_weight_sum_30d += position_weight
                portfolio_sentiment_sum_30d += sentiment_30d * position_weight
                
                # Категоризация для подсчета
                if sentiment_30d >= self.config.bullish_threshold:
                    bullish_count += 1
                elif sentiment_30d <= self.config.bearish_threshold:
                    bear_count += 1
                else:
                    neutral_count += 1
        
        # Финальные расчеты (избегаем деления на ноль)
        portfolio_sentiment_7d = portfolio_sentiment_sum_7d / portfolio_weight_sum_7d if portfolio_weight_sum_7d > 0 else 0.0
        portfolio_sentiment_30d = portfolio_sentiment_sum_30d / portfolio_weight_sum_30d if portfolio_weight_sum_30d > 0 else 0.0
        
        # Дельта между окнами
        delta_7v30 = portfolio_sentiment_30d - portfolio_sentiment_7d
        
        return PortfolioSentimentMetrics(
            portfolio_sentiment_7d=max(-1.0, min(1.0, portfolio_sentiment_7d)),
            portfolio_sentiment_30d=max(-1.0, min(1.0, portfolio_sentiment_30d)),
            portfolio_coverage_7d=int(sum(data.get('coverage_count', 0) for data in symbol_sentiment_7d.values())),
            portfolio_coverage_30d=int(sum(data.get('coverage_count', 0) for data in symbol_sentiment_30d.values())),
            portfolio_delta_7v30=delta_7v30,
            bullish_count=bullish_count,
            neutral_count=neutral_count,
            bear_count=bear_count,
            weighted_by_position=True,
            as_of=datetime.utcnow()
        )
    
    def create_sentiment_grouping(
        self,
        symbol_sentiment_30d: Dict[str, Dict[str, float]],
        position_weights: Dict[str, float],
        timeframe: str = "30d"
    ) -> SentimentGrouping:
        """Создание группировки позиций по сентименту"""
        
        buckets = []
        bullish_symbols = []
        neutral_symbols = []
        bear_symbols = []
        
        # Категоризация символов
        for symbol, sentiment_data in symbol_sentiment_30d.items():
            sentiment_score = sentiment_data['sentiment_score']
            
            if sentiment_score >= self.config.bullish_threshold:
                bullish_symbols.append(symbol)
            elif sentiment_score <= self.config.bearish_threshold:
                bear_symbols.append(symbol)
            else:
                neutral_symbols.append(symbol)
        
        # Создаем корзины
        if bullish_symbols:
            bullish_weight = sum(position_weights.get(s, 0) for s in bullish_symbols)
            bullish_avg = sum(symbol_sentiment_30d[s]['sentiment_score'] for s in bullish_symbols) / len(bullish_symbols)
            
            buckets.append(SentimentBucket(
                bucket_name="Bullish",
                sentiment_range=(self.config.bullish_threshold, 1.0),
                weight_pct=bullish_weight,
                avg_sentiment_score=bullish_avg,
                positions=bullish_symbols,
                count=len(bullish_symbols)
            ))
        
        if neutral_symbols:
            neutral_weight = sum(position_weights.get(s, 0) for s in neutral_symbols)
            neutral_avg = sum(symbol_sentiment_30d[s]['sentiment_score'] for s in neutral_symbols) / len(neutral_symbols) if neutral_symbols else 0.0
            
            buckets.append(SentimentBucket(
                bucket_name="Neutral",
                sentiment_range=(self.config.bearish_threshold, self.config.bullish_threshold),
                weight_pct=neutral_weight,
                avg_sentiment_score=neutral_avg,
                positions=neutral_symbols,
                count=len(neutral_symbols)
            ))
        
        if bear_symbols:
            bear_weight = sum(position_weights.get(s, 0) for s in bear_symbols)
            bear_avg = sum(symbol_sentiment_30d[s]['sentiment_score'] for s in bear_symbols) / len(bear_symbols)
            
            buckets.append(SentimentBucket(
                bucket_name="Bearish",
                sentiment_range=(-1.0, self.config.bearish_threshold),
                weight_pct=bear_weight,
                avg_sentiment_score=bear_avg,
                positions=bear_symbols,
                count=len(bear_symbols)
            ))
        
        # Общий подсчет покрытия
        total_coverage = sum(data.get('coverage_count', 0) for data in symbol_sentiment_30d.values())
        
        return SentimentGrouping(
            timeframe=timeframe,
            buckets=buckets,
            total_coverage=total_coverage,
            fallback_rate=1.0 - (sum(data.get('confidence_avg', 0) for data in symbol_sentiment_30d.values()) / len(symbol_sentiment_30d) if symbol_sentiment_30d else 0)
        )
    
    async def cache_sentiment_data(
        self,
        symbol: str,
        sentiment_7d: Dict[str, float],
        sentiment_30d: Dict[str, float],
        model_used: str
    ) -> None:
        """Сохранение агрегированных данных в Redis кэш"""
        
        cache_key = f"sentiment:{symbol}"
        
        cached_data = CachedSentimentData(
            symbol=symbol,
            sentiment_score_7d=sentiment_7d['sentiment_score'],
            sentiment_score_30d=sentiment_30d['sentiment_score'],
            coverage_count_7d=sentiment_7d['coverage_count'],
            coverage_count_30d=sentiment_30d['coverage_count'],
            delta_7v30=sentiment_30d['sentiment_score'] - sentiment_7d['sentiment_score'],
            confidence_avg=(sentiment_7d.get('confidence_avg', 0) + sentiment_30d.get('confidence_avg', 0)) / 2,
            model_used=model_used,
            last_updated=datetime.utcnow(),
            ttl_hours=self.config.cache_ttl_hours
        )
        
        try:
            # Сохраняем с TTL
            self.redis_client.setex(
                cache_key,
                timedelta(hours=self.config.cache_ttl_hours),
                json.dumps(cached_data.dict(), default=str)
            )
            
            logger.info(f"Cached sentiment data for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to cache sentiment data for {symbol}: {e}")
    
    async def get_cached_sentiment(self, symbol: str) -> Optional[CachedSentimentData]:
        """Получение кэшированных sentiment данных"""
        
        cache_key = f"sentiment:{symbol}"
        
        try:
            cached_json = self.redis_client.get(cache_key)
            if cached_json:
                cached_data = json.loads(cached_json)
                return CachedSentimentData(**cached_data)
        except Exception as e:
            logger.error(f"Failed to get cached sentiment for {symbol}: {e}")
        
        return None
    
    async def invalidate_cache(self, symbol: Optional[str] = None) -> None:
        """Инвалидация кэша (для форс-рефреша)"""
        
        if symbol:
            cache_key = f"sentiment:{symbol}"
            self.redis_client.delete(cache_key)
            logger.info(f"Invalidated cache for {symbol}")
        else:
            # Удаляем все sentiment кэши
            pattern = "sentiment:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} sentiment cache entries")
