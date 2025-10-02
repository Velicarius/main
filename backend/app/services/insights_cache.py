"""
Сервис кэширования для оптимизации LLM вызовов на странице insights
Реализует SWR (Stale-While-Revalidate) паттерн с single-flight
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import redis
from fastapi import HTTPException, status

from app.utils.cache_fingerprint import (
    CacheFingerprintService, ChangeDetector, CacheKeyBuilder,
    InsightsFingerprintData
)

logger = logging.getLogger(__name__)

# === Конфигурация кэширования ===

class CacheConfig:
    """Конфигурация параметров кэширования"""
    
    # TTL для различных типов данных
    FRESH_TTL = 12 * 3600      # 12 часов fresh
    SWR_TTL = 36 * 3600        # 36 часов SWR (total)
    POSITION_TTL = 24 * 3600   # 24 часа для позиций
    PREPARED_TTL = 6 * 3600    # 6 часов для prepared данных
    SENTIMENT_TTL = 6 * 3600   # 6 часов для сентимента
    
    # Single-flight параметры
    SINGLE_FLIGHT_TTL = 90     # 90 секунд блокировка
    MAX_RETRIES = 3            # Максимум ретраев
    RETRY_JITTER = 0.1         # 10% джиттер
    
    # Rate limiting
    RATE_LIMIT_TTL = 3600      # 1 час
    MAX_CALLS_PER_HOUR = 1     # Максимум вызовов в час
    
    # Circuit breaker
    ERROR_THRESHOLD = 0.2      # 20% ошибок
    CIRCUIT_TIMEOUT = 900      # 15 минут таймаут

class CacheStatus:
    """Статус кэша для SWR логики"""
    
    FRESH = "fresh"           # Свежий, не требует обновления
    STALE = "stale"           # Старый, можно показать но нужен refresh
    MISSING = "missing"       # Отсутствует, нужен новый запрос
    LOADING = "loading"       # Загружается другим запросом
    ERROR = "error"           # Ошибка получения

@dataclass
class CacheResult:
    """Результат операции с кэшем"""
    status: str
    data: Optional[Dict[str, Any]] = None
    cached_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    retry_after: Optional[int] = None
    error: Optional[str] = None

class InsightsCacheService:
    """Основной сервис кэширования insights данных"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        self.config = CacheConfig()
    
    async def get_insights_cache(
        self, 
        user_id: str, 
        fingerprint: str,
        force_refresh: bool = False
    ) -> CacheResult:
        """
        Получение данных из кэша с SWR логикой
        
        Args:
            user_id: ID пользователя
            fingerprint: отпечаток входных данных
            force_refresh: принудительное обновление
            
        Returns:
            CacheResult со статусом и данными
        """
        
        cache_key = CacheKeyBuilder.insights_llm_key(user_id, fingerprint)
        
        try:
            # Проверяем существующие данные
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                cache_payload = json.loads(cached_data)
                cached_at = datetime.fromisoformat(cache_payload['cached_at'])
                ttl_remaining = self.redis_client.ttl(cache_key)
                
                # Определяем статус данных
                if ttl_remaining > self.config.FRESH_TTL:
                    status = CacheStatus.FRESH
                    logger.info(f"Fresh cache hit for user {user_id}, fingerprint {fingerprint[:8]}...")
                    
                elif ttl_remaining > 0:
                    status = CacheStatus.STALE
                    logger.info(f"Stale cache hit for user {user_id}, fingerprint {fingerprint[:8]}...")
                    
                    # Запускаем фоновое обновление
                    if not force_refresh:
                        await self._schedule_background_refresh(user_id, fingerprint)
                else:
                    status = CacheStatus.MISSING
                    logger.info(f"Cache expired for user {user_id}, fingerprint {fingerprint[:8]}...")
                
                return CacheResult(
                    status=status,
                    data=cache_payload['data'],
                    cached_at=cached_at,
                    expires_at=datetime.now() + timedelta(seconds=ttl_remaining),
                    error=cache_payload.get('error')
                )
            
            else:
                logger.info(f"Cache miss for user {user_id}, fingerprint {fingerprint[:8]}...")
                return CacheResult(status=CacheStatus.MISSING)
            
        except Exception as e:
            logger.error(f"Cache read error for user {user_id}: {e}")
            return CacheResult(status=CacheStatus.ERROR, error=str(e))
    
    async def set_insights_cache(
        self,
        user_id: str,
        fingerprint: str,
        data: Dict[str, Any],
        error: Optional[str] = None
    ) -> None:
        """
        Сохранение данных в кэш
        
        Args:
            user_id: ID пользователя
            fingerprint: отпечаток входных данных
            data: данные для сохранения
            error: ошибка если есть
        """
        
        cache_key = CacheKeyBuilder.insights_llm_key(user_id, fingerprint)
        
        try:
            # Создаем payload с метаданными
            cache_payload = {
                "data": data,
                "cached_at": datetime.utcnow().isoformat(),
                "fingerprint": fingerprint,
                "schema_version": "insights",
                "model": "llama-3.1-8b",
                "error": error
            }
            
            # Сохраняем с двухуровневом TTL (SWR)
            self.redis_client.setex(
                cache_key,
                self.config.SWR_TTL,
                json.dumps(cache_payload)
            )
            
            logger.info(f"Cached insights for user {user_id}, fingerprint {fingerprint[:8]}...")
            
        except Exception as e:
            logger.error(f"Cache write error for user {user_id}: {e}")
    
    async def acquire_single_flight_lock(
        self, 
        fingerprint: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Получение распределенного лока для single-flight
        
        Args:
            fingerprint: отпечаток для лока
            
        Returns:
            (success, subscriber_key)
        """
        
        lock_key = CacheKeyBuilder.insights_lock_key(fingerprint)
        
        try:
            # Пытаемся получить эксклюзивный лок
            if self.redis_client.setnx(lock_key, "locked"):
                # Устанавливаем TTL для лока
                self.redis_client.expire(lock_key, self.config.SINGLE_FLIGHT_TTL)
                logger.info(f"Acquired single-flight lock for fingerprint {fingerprint[:8]}...")
                return True, None
            
            else:
                # Лок уже взят другим запросом
                subscriber_key = lock_key + ":wait"
                logger.info(
                    f"Single-flight deduplication for fingerprint {fingerprint[:8]}..."
                )
                return False, subscriber_key
                
        except Exception as e:
            logger.error(f"Lock acquisition error: {e}")
            return False, None
    
    async def release_single_flight_lock(self, fingerprint: str) -> None:
        """Освобождение single-flight лока"""
        
        lock_key = CacheKeyBuilder.insights_lock_key(fingerprint)
        
        try:
            self.redis_client.delete(lock_key)
            logger.info(f"Released single-flight lock for fingerprint {fingerprint[:8]}...")
            
        except Exception as e:
            logger.error(f"Lock release error: {e}")
    
    async def subscribe_to_result(
        self, 
        fingerprint: str, 
        timeout: int = 120
    ) -> Optional[CacheResult]:
        """
        Подписка на результат выполнения запроса другим процессом
        
        Args:
            fingerprint: отпечаток запроса
            timeout: таймаут ожидания в секундах
            
        Returns:
            CacheResult или None при таймауте
        """
        
        subscriber_key = CacheKeyBuilder.insights_lock_key(fingerprint) + ":result"
        
        try:
            # Ждем результат с таймаутом
            start_time = time.time()
            
            while (time.time() - start_time) < timeout:
                result_data = self.redis_client.get(subscriber_key)
                
                if result_data:
                    result_dict = json.loads(result_data)
                    
                    # Удаляем временный ключ результата
                    self.redis_client.delete(subscriber_key)
                    
                    cached_at = None
                    expires_at = None
                    
                    if result_dict.get('cached_at'):
                        cached_at = datetime.fromisoformat(result_dict['cached_at'])
                    if result_dict.get('expires_at'):
                        expires_at = datetime.fromisoformat(result_dict['expires_at'])
                    
                    return CacheResult(
                        status=result_dict.get('status', CacheStatus.ERROR),
                        data=result_dict.get('data'),
                        cached_at=cached_at,
                        expires_at=expires_at,
                        error=result_dict.get('error')
                    )
                
                # Короткий сон между проверками
                time.sleep(0.5)
            
            logger.warning(f"Subscription timeout for fingerprint {fingerprint[:8]}...")
            return None
            
        except Exception as e:
            logger.error(f"Subscription error: {e}")
            
            # Cleanup в случае ошибки
            try:
                self.redis_client.delete(subscriber_key)
            except:
                pass
            
            return None
    
    async def notify_subscribers(
        self,
        fingerprint: str,
        result: CacheResult
    ) -> None:
        """
        Уведомление подписчиков о результате
        
        Args:
            fingerprint: отпечаток запроса
            result: результат выполнения
        """
        
        subscriber_key = CacheKeyBuilder.insights_lock_key(fingerprint) + ":result"
        
        try:
            # Создаем payload для подписчиков
            notification_data = {
                "status": result.status,
                "data": result.data,
                "cached_at": result.cached_at.isoformat() if result.cached_at else None,
                "expires_at": result.expires_at.isoformat() if result.expires_at else None,
                "error": result.error
            }
            
            # Сохраняем результат на короткое время
            self.redis_client.setex(
                subscriber_key,
                60,  # 60 секунд
                json.dumps(notification_data)
            )
            
            logger.info(f"Notified subscribers for fingerprint {fingerprint[:8]}...")
            
        except Exception as e:
            logger.error(f"Notification error: {e}")
    
    async def get_position_cache(
        self, 
        user_id: str, 
        symbol: str, 
        mini_fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получение кэшированных данных для позиции
        
        Args:
            user_id: ID пользователя
            symbol: символ позиции
            mini_fingerprint: мини-отпечаток позиции
            
        Returns:
            Кэшированные данные или None
        """
        
        cache_key = CacheKeyBuilder.insights_positions_key(user_id, symbol, mini_fingerprint)
        
        try:
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Position cache read error: {e}")
            return None
    
    async def set_position_cache(
        self,
        user_id: str,
        symbol: str,
        mini_fingerprint: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Сохранение кэша для позиции
        
        Args:
            user_id: ID пользователя
            symbol: символ позиции
            mini_fingerprint: мини-отпечаток позиции
            data: данные позиции
        """
        
        cache_key = CacheKeyBuilder.insights_positions_key(user_id, symbol, mini_fingerprint)
        
        try:
            self.redis_client.setex(
                cache_key,
                self.config.POSITION_TTL,
                json.dumps(data)
            )
            
            logger.info(f"Cached position {symbol} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Position cache write error: {e}")
    
    async def invalidate_cache(
        self, 
        user_id: Optional[str] = None,
        symbol: Optional[str] = None,
        fingerprint: Optional[str] = None,
        full_invalidate: bool = False
    ) -> Dict[str, Any]:
        """
        Инвалидация кэша
        
        Args:
            user_id: ID пользователя
            symbol: конкретный символ
            fingerprint: конкретный отпечаток
            full_invalidate: полная очистка
            
        Returns:
            Статистика инвалидации
        """
        
        try:
            if full_invalidate:
                # Полная очистка всех insights кэшей
                pattern = "insights:*"
                keys = self.redis_client.keys(pattern)
                
                if keys:
                    deleted_count = self.redis_client.delete(*keys)
                    logger.info(f"Full cache invalidation: {deleted_count} keys removed")
                    
                    return {
                        "invalidated_keys": deleted_count,
                        "type": "full"
                    }
            
            else:
                # Селективная инвалидация
                patterns = []
                
                if fingerprint:
                    patterns.append(f"insights:llm:*:{fingerprint}")
                    patterns.append(f"insights:lock:{fingerprint}")
                    patterns.append(f"insights:lock:{fingerprint}:*")
                
                if user_id and symbol:
                    patterns.append(f"insights:llmpos:{user_id}:{symbol}:*")
                
                if user_id and not symbol:
                    patterns.extend([
                        f"insights:llm:{user_id}:*",
                        f"irsights:llmpos:{user_id}:*",
                        f"insights:prepared:{user_id}:*"
                    ])
                
                deleted_count = 0
                
                for pattern in patterns:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        deleted_count += self.redis_client.delete(*keys)
                
                logger.info(f"Selective cache invalidation: {deleted_count} keys removed")
                
                return {
                    "invalidated_keys": deleted_count,
                    "patterns": patterns,
                    "type": "selective"
                }
        
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cache invalidation failed: {str(e)}"
            )
    
    async def _schedule_background_refresh(
        self, 
        user_id: str, 
        fingerprint: str
    ) -> None:
        """
        Планирование фонового обновления для SWR
        
        Args:
            user_id: ID пользователя
            fingerprint: отпечаток для обновления
        """
        
        try:
            # Здесь можно запустить Celery задачу для обновления
            logger.info(f"Scheduled background refresh for user {user_id}, fingerprint {fingerprint[:8]}...")
            
        except Exception as e:
            logger.error(f"Background refresh scheduling error: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Получение статистики кэширования"""
        
        try:
            insights_pattern = "insights:*"
            keys = self.redis_client.keys(insights_pattern)
            
            stats_keys = {
                "llm_cache": 0,
                "position_cache": 0,
                "lock_keys": 0,
                "other": 0
            }
            
            for key in keys:
                if ":llm:" in key:
                    stats_keys["llm_cache"] += 1
                elif ":llmpos:" in key:
                    stats_keys["position_cache"] += 1
                elif ":lock:" in key:
                    stats_keys["lock_keys"] += 1
                else:
                    stats_keys["other"] += 1
            
            return {
                "total_keys": len(keys),
                "breakdown": stats_keys,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Stats collection error: {e}")
            return {"error": str(e)}
