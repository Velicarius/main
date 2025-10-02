"""
Unified Cache Service согласно спецификации Cursor Prompt
Реализует явные режимы кэширования: default/bypass/refresh с прозрачностью
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import redis
from string import Template

logger = logging.getLogger(__name__)


class CacheMode:
    """Режимы кэширования согласно спецификации"""
    DEFAULT = "default"    # используем кэш если валиден
    BYPASS = "bypass"      # игнорируем кэш, не читаем/не пишем
    REFRESH = "refresh"    # пересчёт и перезапись кэша


class CacheState:
    """Состояния кэша для response headers"""
    HIT = "HIT"           # свежий кэш найден
    MISS = "MISS"         # кэш не найден или истёк
    BYPASS = "BYPASS"     # кэш пропущен
    REFRESH = "REFRESH"   # кэш принудительно обновлён
    STALE = "STALE"       # устаревший кэш (опционально)


@dataclass
class CacheMetadata:
    """Метаданные кэша для ответа API с SWR"""
    cached: bool                      # из кэша или свежий?
    cache_key: str                   # ключ кэша
    model_name: str               # имя модели
    last_updated: datetime           # когда обновлён
    compute_ms: int                  # время вычисления (LLM+postprocess)
    llm_latency_ms: int = 0         # время чистого LLM вызова
    
    # SWR поддержка
    cache_age: int = 0               # возраст кэша в секундах
    etag: str = ""                   # ETag для conditional requests
    is_stale: bool = False           # является ли кэш устаревшим
    can_stale_while_revalidate: bool = False  # можно ли отдать stale с фоновым обновлением


@dataclass
class UnifiedCacheConfig:
    """Конфигурация унифицированного кэширования с SWR и Circuit Breaker"""
    # Базовые параметры
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0
    
    # TTL согласно спецификации SWR
    DEFAULT_TTL = 24 * 60 * 60         # 24 часа основной TTL  
    REFRESH_THRESHOLD = 15 * 60        # 15 минут refresh threshold
    STALE_GRACE = 2 * 60 * 60          # 2 часа stale grace period
    
    # Circuit Breaker параметры
    CIRCUIT_BREAKER_FAILURES = 3       # N=3 consecutive failures
    CIRCUIT_BREAKER_WINDOW = 5 * 60    # 5 минут окно
    CIRCUIT_BREAKER_RECOVERY = 10 * 60 # 10 минут использовать кэш
    
    # Schema версии для инвалидации
    SCHEMA_VERSION = "insights_v2"      # версия схемы результата  
    CIRCUIT_BREAKER_KEY = "insights:circuit_breaker_llm"
    
    # ETag поддержка
    ETAG_SEED = "insights-etag-v2"
    
    # Single-flight защита от штормов
    SINGLE_FLIGHT_TTL = 120          # 2 минуты блокировка
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0


class UnifiedCacheService:
    """
    Унифицированный сервис кэширования согласно спецификации
    
    Реализует:
    - Режимы default/bypass/refresh
    - Детерминированные ключи кэша с нормализацией входа
    - Прозрачность через headers и JSON поля
    - Метрики задержки (LLM + E2E)
    - Защиту от штормов через single-flight
    """
    
    def __init__(self):
        # Получаем конфигурацию из переменных окружения или используем значения по умолчанию
        redis_host = os.getenv('REDIS_HOST', UnifiedCacheConfig.REDIS_HOST)
        redis_port = int(os.getenv('REDIS_PORT', UnifiedCacheConfig.REDIS_PORT))
        redis_db = int(os.getenv('REDIS_DB', UnifiedCacheConfig.REDIS_DB))
        
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        self.config = UnifiedCacheConfig()
    
    def normalize_inputs(
        self,
        prompt_data: Dict[str, Any],
        model_params: Dict[str, Any],
        request_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Нормализация входных данных для детерминированного ключа кэша
        
        Args:
            prompt_data: данные промпта (позиции, метрики)
            model_params: параметры модели (model, temperature, top_p)
            request_params: параметры запроса (horizon_months, risk_profile)
        
        Returns:
            Нормализованные данные
        """
        # Нормализуем промпт данные
        normalized_positions = [
            {
                "symbol": pos.get("symbol"),
                "quantity": pos.get("quantity"),
                "price": pos.get("price")  # не включаем timestamp цены
            }
            for pos in prompt_data.get("positions", [])
        ]
        
        # Сортируем позиции для консистентности
        normalized_positions.sort(key=lambda x: x["symbol"] or "")
        
        return {
            "positions": normalized_positions,
            "model": model_params.get("model"),
            "temperature": model_params.get("temperature", 0.2),
            "top_p": model_params.get("top_p", 1.0),
            "max_tokens": model_params.get("max_tokens", 400),
            "horizon_months": request_params.get("horizon_months"),
            "risk_profile": request_params.get("risk_profile"),
            "schema_version": self.config.SCHEMA_VERSION,
            # Не включаем timestamp для детерминированности
        }
    
    def create_cache_key(
        self,
        user_id: str,
        normalized_inputs: Dict[str, Any]
    ) -> str:
        """
        Создание детерминированного ключа кэша
        
        Args:
            user_id: ID пользователя
            normalized_inputs: нормализованные входные данные
        
        Returns:
            Ключ кэша в формате: insights:user:{user_id}:{fingerprint_hash}
        """
        # Создаем строку для хеширования
        cache_input = json.dumps(normalized_inputs, sort_keys=True, separators=(',', ':'))
        
        # Простое хеширование для детерминированного ключа
        import hashlib
        fingerprint = hashlib.md5(cache_input.encode()).hexdigest()
        
        return f"insights:unified:{user_id}:{fingerprint}"
    
    def get_cache_entry(
        self,
        cache_key: str,
        mode: str = CacheMode.DEFAULT
    ) -> Tuple[Optional[Dict], Optional[CacheMetadata], str]:
        """
        Получение данных из кэша согласно режиму
        
        Args:
            cache_key: ключ кэша
            mode: режим кэширования
        
        Returns:
            (data, metadata, state) где state один из CacheState
        """
        if mode == CacheMode.BYPASS:
            logger.info(f"Cache BYPASS for key {cache_key}")
            return None, None, CacheState.BYPASS
        
        try:
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                cache_payload = json.loads(cached_data)
                
                metadata = CacheMetadata(
                    cached=True,
                    cache_key=cache_key,
                    model_name=cache_payload.get("model_version", "unknown"),
                    last_updated=datetime.fromisoformat(cache_payload["last_updated"]),
                    compute_ms=cache_payload.get("compute_ms", 0),
                    llm_latency_ms=cache_payload.get("llm_latency_ms", 0)
                )
                
                if mode == CacheMode.REFRESH:
                    logger.info(f"Cache REFRESH requested for key {cache_key}")
                    return cache_payload["data"], metadata, CacheState.REFRESH
                else:
                    logger.info(f"Cache HIT for key {cache_key}")
                    return cache_payload["data"], metadata, CacheState.HIT
            
            else:
                logger.info(f"Cache MISS for key {cache_key}")
                return None, None, CacheState.MISS
                
        except Exception as e:
            logger.error(f"Cache read error for key {cache_key}: {e}")
            return None, None, CacheState.MISS
    
    def set_cache_entry(
        self,
        cache_key: str,
        data: Dict[str, Any],
        model_name: str,
        compute_ms: int,
        llm_latency_ms: int = 0,
        mode: str = CacheMode.DEFAULT
    ) -> None:
        """
        Сохранение данных в кэш согласно режиму
        
        Args:
            cache_key: ключ кэша
            data: данные для сохранения
            model_name: имя модели
            compute_ms: время вычисления
            llm_latency_ms: время LLM вызова
            mode: режим кэширования (bypass не сохраняет)
        """
        if mode == CacheMode.BYPASS:
            logger.info(f"Cache BYPASS set for key {cache_key} - skipping save")
            return
        
        try:
            cache_payload = {
                "data": data,
                "model_version": model_name,
                "last_updated": datetime.utcnow().isoformat(),
                "compute_ms": compute_ms,
                "llm_latency_ms": llm_latency_ms,
                "schema_version": self.config.SCHEMA_VERSION,
            }
            
            self.redis_client.setex(
                cache_key,
                self.config.DEFAULT_TTL,
                json.dumps(cache_payload)
            )
            
            logger.info(f"Cached insights data for key {cache_key}")
            
        except Exception as e:
            logger.error(f"Cache write error for key {cache_key}: {e}")
    
    def acquire_computation_lock(self, cache_key: str) -> Tuple[bool, Optional[str]]:
        """
        Получение распределенного лока для single-flight
        
        Args:
            cache_key: ключ кэша для лока
        
        Returns:
            (success, lock_key) - успех и ключ лока
        """
        lock_key = f"lock:{cache_key}"
        
        try:
            if self.redis_client.setnx(lock_key, "locked"):
                self.redis_client.expire(lock_key, self.config.SINGLE_FLIGHT_TTL)
                logger.info(f"Acquired single-flight lock {lock_key}")
                return True, lock_key
            else:
                logger.info(f"Single-flight deduplication for {lock_key}")
                return False, lock_key
                
        except Exception as e:
            logger.error(f"Lock acquisition error for {lock_key}: {e}")
            return False, None
    
    def release_computation_lock(self, lock_key: str) -> None:
        """Освобождение лока вычисления"""
        try:
            self.redis_client.delete(lock_key)
            logger.info(f"Released single-flight lock {lock_key}")
        except Exception as e:
            logger.error(f"Lock release error for {lock_key}: {e}")
    
    def invalidate_user_cache(self, user_id: str) -> Dict[str, Any]:
        """
        Инвалидация кэша пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Статистика инвалидации
        """
        try:
            pattern = f"insights:unified:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted_count} cache entries for user {user_id}")
                return {
                    "invalidated_keys": deleted_count,
                    "user_id": user_id,
                    "type": "user_cache_clear"
                }
            else:
                return {
                    "invalidated_keys": 0,
                    "user_id": user_id,
                    "type": "no_entries_found"
                }
                
        except Exception as e:
            logger.error(f"Cache invalidation error for user {user_id}: {e}")
            return {
                "invalidated_keys": 0,
                "user_id": user_id,
                "type": "error",
                "error": str(e)
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        try:
            pattern = "insights:unified:*"
            keys = self.redis_client.keys(pattern)
            
            # Статистика по пользователям
            user_counts = {}
            for key in keys:
                parts = key.split(':')
                if len(parts) >= 3:
                    user_id = parts[2]
                    user_counts[user_id] = user_counts.get(user_id, 0) + 1
            
            return {
                "total_entries": len(keys),
                "unique_users": len(user_counts),
                "user_breakdown": user_counts,
                "timestamp": datetime.utcnow().isoformat(),
                "estimated_memory_bytes": len(keys) * 1000,  # примерная оценка
            }
            
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"error": str(e)}
    
    def log_cache_operation(
        self,
        operation: str,
        cache_key: str,
        cache_state: str,
        elapsed_ms: Optional[int] = None,
        llm_ms: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        Логирование операции кэш согласно спецификации
        
        Args:
            operation: тип операции (get_insights, refresh_insights)
            cache_key: ключ кэша (усечённый для логов)
            cache_state: состояние кэша (HIT/MISS/BYPASS/REFRESH)
            elapsed_ms: общее время выполнения
            llm_ms: время LLM вызова
            **kwargs: дополнительные параметры
        """
        truncated_key = cache_key[:16] + "..." if len(cache_key) > 16 else cache_key
        
        log_data = {
            "operation": operation,
            "cache_key": truncated_key,
            "cache_state": cache_state,
            "ttl": self.config.DEFAULT_TTL,
        }
        
        if elapsed_ms is not None:
            log_data["total_ms"] = elapsed_ms
        if llm_ms is not None:
            log_data["llm_ms"] = llm_ms
        
        log_data.update(kwargs)
        
        logger.info(f"Cache operation: {log_data}")
    
    def _compute_portfolio_hash(self, user_id: str, request_data: Dict[str, Any]) -> str:
        """Вычисляет детерминированный хеш портфеля для ключа кэша"""
        # Нормализуем данные для воспроизводимого хеша
        normalized_data = {
            'user_id': user_id,
            'horizon_months': request_data.get('horizon_months', 6),
            'risk_profile': request_data.get('risk_profile', 'Balanced'),
            'model': request_data.get('model', 'llama3.1:8b'),
            'schema_version': self.config.SCHEMA_VERSION
        }
        
        # Сортируем ключи для консистентности
        sorted_items = sorted(normalized_data.items())
        hash_input = ''.join(f"{k}={v}" for k, v in sorted_items)
        
        # Простой хеш для демонстрации (в продакшене используйте hashlib.sha256)
        return str(hash(hash_input))[:16]
    
    def _generate_etag(self, user_id: str, timestamp: str, content_hash: str) -> str:
        """Генерирует ETag на основе контента"""
        etag_input = f"{self.config.ETAG_SEED}:{user_id}:{timestamp}:{content_hash}"
        return str(hash(etag_input))[-16:]  # последние 16 символов хеша
    
    def _check_etag_match(self, etag: str, if_none_match: Optional[str]) -> bool:
        """Проверяет соответствие ETag для conditional requests (304)"""
        return if_none_match and etag in if_none_match.split(', ')
    
    def _update_circuit_breaker(self, success: bool) -> bool:
        """Обновляет состояние circuit breaker. Возвращает True если circuit открыт (следует использовать кэш)"""
        now = time.time()
        current_state = self.redis_client.hgetall(self.config.CIRCUIT_BREAKER_KEY)
        
        if success:
            # Сброс circuit breaker при успехе
            self.redis_client.delete(self.config.CIRCUIT_BREAKER_KEY)
            logger.info("Circuit breaker reset due to success")
            return False
        else:
            # Увеличиваем счетчик ошибок
            failures = int(current_state.get('failures', 0)) + 1
            windowStart = float(current_state.get('window_start', now))
            
            # Создаем новое окно если прошло время
            if now - windowStart > self.config.CIRCUIT_BREAKER_WINDOW:
                windowStart = now
                failures = 1
            
            # Сохраняем состояние
            self.redis_client.hset(self.config.CIRCUIT_BREAKER_KEY, mapping={
                'failures': failures,
                'window_start': windowStart,
                'last_failure': now
            })
            
            # Circuit открыт если превышен лимит ошибок
            if failures >= self.config.CIRCUIT_BREAKER_FAILURES:
                self.redis_client.expire(self.config.CIRCUIT_BREAKER_KEY, self.config.CIRCUIT_BREAKER_RECOVERY)
                logger.warning(f"Circuit breaker OPEN after {failures} failures within {self.config.CIRCUIT_BREAKER_WINDOW}s")
                return True
            
            return False
    
    def _is_circuit_breaker_open(self) -> bool:
        """Проверяет открыт ли circuit breaker"""
        try:
            circuit_state = self.redis_client.exists(self.config.CIRCUIT_BREAKER_KEY)
            return bool(circuit_state)
        except Exception as e:
            logger.error(f"Failed to check circuit breaker: {e}")
            return False
    
    def get_insights_with_swr(self, 
                             user_id: str,
                             request_data: Dict[str, Any],
                             if_none_match: Optional[str] = None) -> Tuple[Optional[CacheMetadata], Optional[Dict], bool]:
        """
        Получение инсайтов с полной поддержкой SWR (Stale-While-Revalidate)
        
        SWR поведение:
        - FRESH (age < 15min): HIT, отдаем немедленно, background=false
        - STALE (15min < age < 2h): STALE, отдаем немедленно, background=true  
        - EXPIRED (age > 2h): MISS, блокируем клиента, жду fresh data
        
        Returns:
            (metadata, data, should_revalidate_background)
        """
        portfolio_hash = self._compute_portfolio_hash(user_id, request_data)
        cache_key = f"insights:{portfolio_hash}:{self.config.SCHEMA_VERSION}"
        
        try:
            cached_entry = self.redis_client.get(cache_key)
            
            if not cached_entry:
                logger.info(f"Cache MISS for key {cache_key[:20]}... (no entry)")
                return (None, None, False)
            
            cache_payload = json.loads(cached_entry)
            
            # Вычисляем возраст кэша в секундах
            cache_timestamp = datetime.fromisoformat(cache_payload["last_updated"])
            cache_age_seconds = int((datetime.now() - cache_timestamp).total_seconds())
            
            # Проверяем ETag для 304 Not Modified
            content_hash = str(hash(str(cache_payload["data"])))[-8:]
            etag = self._generate_etag(user_id, cache_payload["last_updated"], content_hash)
            
            if self._check_etag_match(etag, if_none_match):
                logger.info(f"ETag match, returning 304 for {cache_key[:20]}...")
                return (CacheMetadata(
                    cached=True,
                    cache_key=cache_key,
                    model_name=cache_payload.get("model_version", "unknown"),
                    last_updated=cache_timestamp,
                    compute_ms=0,
                    cache_age=cache_age_seconds,
                    etag=etag,
                    is_stale=False,
                    can_stale_while_revalidate=False
                ), None, False)  # Возвращаем None data для 304
            
            # 🎯 SWR состояние определение по возрасту кэша
            
            # FRESH: возраст меньше refresh threshold - отдаем без фона
            if cache_age_seconds <= self.config.REFRESH_THRESHOLD:
                logger.info(f"Cache HIT (FRESH) for {cache_key[:20]}... (age: {cache_age_seconds}s)")
                metadata = CacheMetadata(
                    cached=True,
                    cache_key=cache_key,
                    model_name=cache_payload.get("model_version", "unknown"),
                    last_updated=cache_timestamp,
                    compute_ms=cache_payload.get("compute_ms", 0),
                    llm_latency_ms=cache_payload.get("llm_latency_ms", 0),
                    cache_age=cache_age_seconds,
                    etag=etag,
                    is_stale=False,
                    can_stale_while_revalidate=False
                )
                return (metadata, cache_payload["data"], False)
            
            # STALE: возраст больше refresh но меньше stale grace - SWR
            elif cache_age_seconds <= self.config.STALE_GRACE:
                logger.info(f"Cache STALE for {cache_key[:20]}... (age: {cache_age_seconds}s) - background refresh")
                metadata = CacheMetadata(
                    cached=True,
                    cache_key=cache_key,
                    model_name=cache_payload.get("model_version", "unknown"),
                    last_updated=cache_timestamp,
                    compute_ms=cache_payload.get("compute_ms", 0),
                    llm_latency_ms=cache_payload.get("llm_latency_ms", 0),
                    cache_age=cache_age_seconds,
                    etag=etag,
                    is_stale=True,
                    can_stale_while_revalidate=True
                )
                return (metadata, cache_payload["data"], True)  # 🔄 Background refresh!
            
            # EXPIRED: возраст больше stale grace - чистый MISS 
            else:
                logger.info(f"Cache EXPIRED for {cache_key[:20]}... (age: {cache_age_seconds}s) - removing from cache")
                # Удаляем expired запись
                self.redis_client.delete(cache_key)
                return (None, None, False)
            
        except Exception as e:
            logger.error(f"Cache read error for key {cache_key[:20]}...: {e}")
            return (None, None, False)
    
    def save_insights_with_swr(self,
                               user_id: str,
                               request_data: Dict[str, Any],
                               data: Dict[str, Any],
                               compute_ms: int,
                               llm_latency_ms: int = 0) -> Tuple[str, str]:
        """
        Сохранение инсайтов с правильными ключами SWR
        
        Returns:
            (cache_key, etag)
        """
        portfolio_hash = self._compute_portfolio_hash(user_id, request_data)
        cache_key = f"insights:{portfolio_hash}:{self.config.SCHEMA_VERSION}"
        
        try:
            now = datetime.now()
            
            # Создаем payload с правильной структурой
            cache_payload = {
                "data": data,
                "model_version": request_data.get("model", "unknown"),
                "last_updated": now.isoformat(),
                "compute_ms": compute_ms,
                "llm_latency_ms": llm_latency_ms,
                "schema_version": self.config.SCHEMA_VERSION,
                "portfolio_hash": portfolio_hash,
                "request_metadata": {
                    "user_id": user_id,
                    "horizon_months": request_data.get("horizon_months", 6),
                    "risk_profile": request_data.get("risk_profile", "Balanced")
                }
            }
            
            # Сохраняем с полным TTL (24 часа)
            self.redis_client.setex(
                cache_key,
                self.config.DEFAULT_TTL,
                json.dumps(cache_payload, default=str)
            )
            
            # Генерируем ETag
            content_hash = str(hash(str(data)))[-8:]
            etag = self._generate_etag(user_id, now.isoformat(), content_hash)
            
            logger.info(f"Saved insights to cache: {cache_key[:20]}... (TTL: {self.config.DEFAULT_TTL}s)")
            
            return (cache_key, etag)
            
        except Exception as e:
            logger.error(f"Failed to save insights to cache: {e}")
            return ("", "")
    
    def schedule_background_refresh(self,
                                   user_id: str,
                                   request_data: Dict[str, Any],
                                   llm_callback) -> bool:
        """
        Планирует фоновое обновление для STALE данных
        
        llm_callback: функция которая возвращает новые данные для кэша
        Returns:
            True если планирование успешно
        """
        portfolio_hash = self._compute_portfolio_hash(user_id, request_data)
        cache_key = f"insights:{portfolio_hash}:{self.config.SCHEMA_VERSION}"
        lock_key = f"{cache_key}:refresh_lock"
        
        try:
            # Проверяем есть ли уже обновление в процессе
            if self.redis_client.exists(lock_key):
                logger.info(f"Background refresh already in progress for {cache_key[:20]}...")
                return True
            
            # Устанавливаем lock на 10 минут (время на LLM генерацию)
            if self.redis_client.setnx(lock_key, str(time.time())):
                self.redis_client.expire(lock_key, 600)  # 10 минут lock
                
                # В реальной реализации здесь был бы Celery/fastapi-background-tasks
                # Для демонстрации просто логируем что планируем обновление
                logger.warning(f"✏️ Background refresh QUEUED for {cache_key[:20]}... "
                             f"(Real implementation would call {llm_callback.__name__})")
                
                return True
            else:
                logger.info(f"Background refresh lock already exists for {cache_key[:20]}...")
                return True
                
        except Exception as e:
            logger.error(f"Failed to schedule background refresh: {e}")
            return False
