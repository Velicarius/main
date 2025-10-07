"""
News Cache Service - кэширование новостей для снижения нагрузки на внешние API
"""

import json
import logging
import redis
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID

from app.schemas.news import NormalizedNews
from app.core.config import settings

logger = logging.getLogger(__name__)


class NewsCacheService:
    """Сервис кэширования новостей с TTL и инвалидацией"""
    
    def __init__(self):
        # Use Redis service name in Docker, localhost in development
        import os
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_client = redis.Redis(
            host=redis_host,
            port=6379,
            db=0,
            decode_responses=True
        )
        self.default_ttl = settings.news_cache_ttl_seconds
        self.max_articles_per_ticker = settings.news_cache_max_articles
        
    def get_cached_news(
        self, 
        ticker: str, 
        hours_back: int = 24,
        limit: int = 50
    ) -> Optional[List[NormalizedNews]]:
        """
        Получить новости из кэша
        
        Args:
            ticker: Тикер акции
            hours_back: Сколько часов назад искать
            limit: Максимум статей
            
        Returns:
            Список новостей или None если нет в кэше
        """
        try:
            cache_key = self._generate_news_key(ticker, hours_back, limit)
            cached_data = self.redis_client.get(cache_key)
            
            if not cached_data:
                logger.debug(f"No cached news found for {ticker}")
                return None
                
            # Парсим кэшированные данные
            data = json.loads(cached_data)
            articles = []
            
            for article_data in data.get('articles', []):
                try:
                    # Преобразуем строки дат обратно в datetime
                    if 'published_at' in article_data:
                        article_data['published_at'] = datetime.fromisoformat(article_data['published_at'])
                    
                    article = NormalizedNews(**article_data)
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to parse cached article: {e}")
                    continue
            
            logger.info(f"Cache hit for {ticker}: {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error reading news cache for {ticker}: {e}")
            return None
    
    def cache_news(
        self, 
        ticker: str, 
        articles: List[NormalizedNews],
        hours_back: int = 24,
        limit: int = 50,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Сохранить новости в кэш
        
        Args:
            ticker: Тикер акции
            articles: Список новостей
            hours_back: Сколько часов назад искали
            limit: Лимит статей
            ttl: Время жизни кэша в секундах
            
        Returns:
            True если успешно сохранено
        """
        try:
            if not articles:
                logger.debug(f"No articles to cache for {ticker}")
                return False
                
            cache_key = self._generate_news_key(ticker, hours_back, limit)
            
            # Преобразуем статьи в JSON-сериализуемый формат
            cache_data = {
                'ticker': ticker,
                'cached_at': datetime.now().isoformat(),
                'hours_back': hours_back,
                'limit': limit,
                'articles': []
            }
            
            for article in articles[:self.max_articles_per_ticker]:
                try:
                    article_dict = article.dict()
                    # Преобразуем datetime в строку для JSON
                    if 'published_at' in article_dict and article_dict['published_at']:
                        article_dict['published_at'] = article_dict['published_at'].isoformat()
                    
                    cache_data['articles'].append(article_dict)
                except Exception as e:
                    logger.warning(f"Failed to serialize article for cache: {e}")
                    continue
            
            # Сохраняем в кэш
            cache_ttl = ttl or self.default_ttl
            self.redis_client.setex(cache_key, cache_ttl, json.dumps(cache_data))
            
            logger.info(f"Cached {len(cache_data['articles'])} articles for {ticker} (TTL: {cache_ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error caching news for {ticker}: {e}")
            return False
    
    def invalidate_ticker_cache(self, ticker: str) -> bool:
        """
        Инвалидировать кэш для конкретного тикера
        
        Args:
            ticker: Тикер для инвалидации
            
        Returns:
            True если успешно
        """
        try:
            # Генерируем паттерн для поиска всех ключей тикера
            pattern = f"news:{ticker.upper()}:*"
            
            # Получаем все ключи по паттерну
            keys = self.redis_client.keys(pattern)
            
            if keys:
                # Удаляем все найденные ключи
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for {ticker}")
                return True
            else:
                logger.debug(f"No cache entries found for {ticker}")
                return True
                
        except Exception as e:
            logger.error(f"Error invalidating cache for {ticker}: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Получить статистику кэша новостей
        
        Returns:
            Словарь со статистикой
        """
        try:
            # Получаем все ключи новостей
            news_keys = self.redis_client.keys("news:*")
            
            stats = {
                'total_keys': len(news_keys),
                'tickers': set(),
                'oldest_entry': None,
                'newest_entry': None
            }
            
            if news_keys:
                # Анализируем ключи
                for key in news_keys:
                    parts = key.split(':')
                    if len(parts) >= 2:
                        stats['tickers'].add(parts[1])
                
                # Получаем TTL для нескольких ключей
                sample_keys = news_keys[:10]  # Берем первые 10 для анализа
                ttls = []
                
                for key in sample_keys:
                    ttl = self.redis_client.ttl(key)
                    if ttl > 0:
                        ttls.append(ttl)
                
                if ttls:
                    stats['avg_ttl_seconds'] = sum(ttls) / len(ttls)
                    stats['min_ttl_seconds'] = min(ttls)
                    stats['max_ttl_seconds'] = max(ttls)
            
            stats['tickers'] = list(stats['tickers'])
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def _generate_news_key(self, ticker: str, hours_back: int, limit: int) -> str:
        """Генерирует ключ кэша для новостей"""
        return f"news:{ticker.upper()}:{hours_back}h:{limit}"


# Singleton instance
_news_cache_service: Optional[NewsCacheService] = None

def get_news_cache_service() -> NewsCacheService:
    """Получить singleton instance сервиса кэширования новостей"""
    global _news_cache_service
    if _news_cache_service is None:
        _news_cache_service = NewsCacheService()
    return _news_cache_service
