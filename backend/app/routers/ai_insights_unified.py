"""
Unified AI Insights API согласно спецификации Cursor Prompt
Реализует контракт с явными режимами кэширования и прозрачностью
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from app.database import get_db
from app.services.unified_cache_service import (
    UnifiedCacheService, 
    CacheMode, 
    CacheState, 
    CacheMetadata,
    UnifiedCacheConfig
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/insights", tags=["ai-insights-unified"])

# === Pydantic модели ===

class UnifiedInsightsRequest(BaseModel):
    """Расширенный запрос для unified insights"""
    # Основные параметры анализа
    horizon_months: int = Field(default=6, ge=1, le=24, description="Горизонт анализа в месяцах")
    risk_profile: str = Field(default="Balanced", description="Профиль риска")
    
    # Параметры модели
    model: str = Field(default="llama3.1:8b", description="Модель LLM")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Температура модели")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p параметр")
    max_tokens: int = Field(default=400, ge=50, le=2000, description="Максимум токенов")
    
    # Дополнительные параметры
    locale: str = Field(default="en", description="Язык ответа")
    include_signals: bool = Field(default=True, description="Включать торговые сигналы")


class UnifiedInsightsResponse(BaseModel):
    """Ответ согласно спецификации с прозрачностью кэша"""
    # Поля прозрачности согласно спецификации
    cached: bool
    cache_key: str
    model_name: str  # Переименовано чтобы избежать конфликта с protected namespace
    last_updated: str  # ISO timestamp
    compute_ms: int    # server-side compute время
    llm_ms: int = 0   # чистое время LLM вызова
    
    # Основные данные инсайтов
    data: Dict[str, Any]
    
    model_config = ConfigDict(protected_namespaces=())


class CacheInvalidateRequest(BaseModel):
    """Запрос на инвалидацию кэша"""
    user_id: Optional[str] = None
    full_clear: bool = False


# === Основной сервис ===

class UnifiedInsightsService:
    """Основной сервис unified insights с кэшированием"""
    
    def __init__(self):
        self.cache_service = UnifiedCacheService()
    
    async def get_insights(
        self,
        user_id: UUID,
        request: UnifiedInsightsRequest,
        cache_param: str = CacheMode.DEFAULT,
        db: Session = None,
        if_none_match: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
        """
        Получение инсайтов согласно спецификации SWR (Stale-While-Revalidate)
        
        Args:
            user_id: ID пользователя
            request: параметры запроса
            cache_param: режим кэширования (default/bypass/refresh)
            db: сессия базы данных
            if_none_match: ETag для conditional requests
        
        Returns:
            (response_data, headers) - данные ответа и заголовки согласно спецификации
        """
        start_time = time.time()
        request_data = request.dict()
        
        logger.info(f"🔄 Unified insights SWR request for user {user_id}, mode={cache_param}")
        
        # 🎯 Проверяем SWR кэш первым делом для Bypass/Refresh режимов
        if cache_param == CacheMode.DEFAULT:
            cache_metadata, cached_data, needs_background_refresh = self.cache_service.get_insights_with_swr(
                str(user_id), request_data, if_none_match
            )
            
            # 🎯 Обрабатываем результаты SWR
            
            # 304 Not Modified - возвращаем только заголовки
            if cached_data is None and cache_metadata:
                return None, {
                    "ETag": cache_metadata.etag,
                    "X-Cache": "HIT",
                    "X-Cache-Age": str(cache_metadata.cache_age),
                    "X-Generated-At": cache_metadata.last_updated.isoformat(),
                    "X-LLM-Model": cache_metadata.model_name,
                    "X-Features-Version": "v2",
                }  # 304 response (None content)
            
            # FRESH или STALE кэш найден
            if cache_metadata and cached_data:
                computation_ms = int((time.time() - start_time) * 1000)
                
                # Строим response согласно спецификации
                response_data = {
                    "cached": True,
                    "cache_key": cache_metadata.cache_key,
                    "model_name": cache_metadata.model_name,
                    "last_updated": cache_metadata.last_updated.isoformat(),
                    "compute_ms": computation_ms,
                    "llm_ms": cache_metadata.llm_latency_ms,
                    "data": cached_data
                }
                
                headers = {
                    "ETag": cache_metadata.etag,
                    "X-Cache": "STALE" if cache_metadata.is_stale else "HIT",
                    "X-Cache-Age": str(cache_metadata.cache_age),
                    "X-Generated-At": cache_metadata.last_updated.isoformat(),
                    "X-LLM-Model": cache_metadata.model_name,
                    "X-Features-Version": "v2",
                    "X-Cache-Key": cache_metadata.cache_key[:16] + "...",
                    "X-LLM-Latency-MS": str(cache_metadata.llm_latency_ms),
                }
                
                # 🔄 Планируем фоновое обновление для STALE данных
                if needs_background_refresh:
                    logger.info(f"🚀 Scheduling background refresh for stale cache {cache_metadata.cache_key[:16]}...")
                    self.cache_service.schedule_background_refresh(
                        str(user_id), request_data, self._generate_fresh_insights
                    )
                
                return response_data, headers
            
            # Cache MISS или Bypass режим - продолжаем генерацию
            logger.info(f"Cache MISS or BYPASS for user {user_id}")
        
        # 🔥 Генерация свежих данных
        
        # Готовим данные портфеля
        prompt_data = await self._prepare_prompt_data(user_id, db, request)
        
        # 🔥 Генерируем свежие данные с LLM
        computation_start = time.time()
        llm_start = time.time()
        
        logger.info(f"🚀 Computing fresh insights for user {user_id}")
        
        insights_data = await self._compute_insights(user_id, request, db)
        llm_ms = int((time.time() - llm_start) * 1000)
        compute_ms = int((time.time() - computation_start) * 1000)
        
        # 💾 Сохраняем в новый SWR кэш
        cache_key, etag = self.cache_service.save_insights_with_swr(
            str(user_id), request_data, insights_data, compute_ms, llm_ms
        )
        
        # 📊 Строим response согласно спецификации SWR
        response_data = {
            "cached": False,
            "cache_key": cache_key,
            "model_name": request.model,
            "last_updated": datetime.now().isoformat(),
            "compute_ms": compute_ms,
            "llm_ms": llm_ms,
            "data": insights_data
        }
        
        headers = {
            "ETag": etag,
            "X-Cache": "MISS",
            "X-Cache-Age": "0",
            "X-Cache-Key": cache_key[:16] + "...",
            "X-LLM-Model": request.model,
            "X-LLM-Latency-MS": str(llm_ms),
            "X-Generated-At": datetime.now().isoformat(),
            "X-Features-Version": "v2"
        }
        
        # Логируем операцию согласно спецификации
        total_elapsed = int((time.time() - start_time) * 1000)
        self.cache_service.log_cache_operation(
            operation="get_insights_swr",
            cache_key=cache_key[:16] + "...",
            cache_state="MISS",
            elapsed_ms=total_elapsed,
            llm_ms=llm_ms,
            user_id=str(user_id)
        )
        
        return response_data, headers
    
    async def _prepare_prompt_data(self, user_id: UUID, db: Session, request: UnifiedInsightsRequest) -> Dict[str, Any]:
                "model_name": cache_metadata.model_name,
                "last_updated": cache_metadata.last_updated.isoformat(),
                "compute_ms": 0,  # из кэша, времени не тратили
                "llm_ms": 0,
                "data": cached_data
            }
            
            headers = {
                "X-Cache": CacheState.HIT,
                "X-Cache-Key": cache_key,
                "X-LLM-Latency-MS": "0"
            }
            
        elif cache_state == CacheState.BYPASS or cache_param == CacheMode.BYPASS:
            # Принудительное игнорирование кэша
            logger.info(f"Cache BYPASS for user {user_id}")
            
            # Вычисляем инсайты без кэша
            insights_data = await self._compute_insights(user_id, request, db)
            llm_ms = int((time.time() - llm_start) * 1000)
            compute_ms = int((time.time() - computation_start) * 1000)
            
            response_data = {
                "cached": False,
                "cache_key": cache_key,
                "model_name": request.model,
                "last_updated": datetime.utcnow().isoformat(),
                "compute_ms": compute_ms,
                "llm_ms": llm_ms,
                "data": insights_data
            }
            
            headers = {
                "X-Cache": CacheState.BYPASS,
                "X-Cache-Key": cache_key,
                "X-LLM-Latency-MS": str(llm_ms)
            }
            
        elif cache_state == CacheState.REFRESH or cache_param == CacheMode.REFRESH:
            # Принудительное обновление кэша
            logger.info(f"Cache REFRESH for user {user_id}")
            
            # Вычисляем новые инсайты
            insights_data = await self._compute_insights(user_id, request, db)
            llm_ms = int((time.time() - llm_start) * 1000)
            compute_ms = int((time.time() - computation_start) * 1000)
            
            # Сохраняем в кэш
            self.safe_cache_save(
                cache_key, insights_data, request.model, compute_ms, llm_ms, CacheMode.DEFAULT
            )
            
            response_data = {
                "cached": False,
                "cache_key": cache_key,
                "model_name": request.model,
                "last_updated": datetime.utcnow().isoformat(),
                "compute_ms": compute_ms,
                "llm_ms": llm_ms,
                "data": insights_data
            }
            
            headers = {
                "X-Cache": CacheState.REFRESH,
                "X-Cache-Key": cache_key,
                "X-LLM-Latency-MS": str(llm_ms)
            }
            
        else:
            # MISS - вычислим и сохраним
            logger.info(f"Cache MISS for user {user_id}")
            
            # Проверяем single-flight лок
            locked, lock_key = self.cache_service.acquire_computation_lock(cache_key)
            
            if not locked:
                # Кто-то уже вычисляет, ждём или возвращаем ошибку
                # В реальном проекте здесь была бы подписка на результат
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Computation in progress, please retry shortly"
                )
            
            try:
                # Вычисляем инсайты
                insights_data = await self._compute_insights(user_id, request, db)
                llm_ms = int((time.time() - llm_start) * 1000)
                compute_ms = int((time.time() - computation_start) * 1000)
                
                # Сохраняем в кэш
                self.safe_cache_save(
                    cache_key, insights_data, request.model, compute_ms, llm_ms, CacheMode.DEFAULT
                )
                
                response_data = {
                    "cached": False,
                    "cache_key": cache_key,
                    "model_name": request.model,
                    "last_updated": datetime.utcnow().isoformat(),
                    "compute_ms": compute_ms,
                    "llm_ms": llm_ms,
                    "data": insights_data
                }
                
                headers = {
                    "X-Cache": CacheState.MISS,
                    "X-Cache-Key": cache_key,
                    "X-LLM-Latency-MS": str(llm_ms)
                }
                
            finally:
                # Освобождаем лок
                self.cache_service.release_computation_lock(lock_key)
        
        # Логируем операцию согласно спецификации
        total_elapsed = int((time.time() - start_time) * 1000)
        self.cache_service.log_cache_operation(
            operation="get_insights",
            cache_key=cache_key,
            cache_state=cache_state,
            elapsed_ms=total_elapsed,
            llm_ms=response_data.get("llm_ms", 0),
            user_id=str(user_id),
            model_version=response_data["model_name"]
        )
        
        return response_data, headers
    
    async def _prepare_prompt_data(
        self,
        user_id: UUID,
        db: Session,
        request: UnifiedInsightsRequest
    ) -> Dict[str, Any]:
        """Подготовка данных для промпта (детерминирующая часть)"""
        # Здесь заглушка - в реальном проекте брать данные из БД
        # Аналогично тому что есть в InsightsPrepareService
        
        return {
            "positions": [
                {
                    "symbol": "AAPL",
                    "quantity": 100,
                    "price": 150.0
                },
                {
                    "symbol": "GOOGL", 
                    "quantity": 50,
                    "price": 2800.0
                }
            ],
            "metrics": {
                "total_value": 290000.0,
                "number_of_positions": 2,
                "top_concentration": 0.48
            }
        }
    
    async def _compute_insights(
        self,
        user_id: UUID,
        request: UnifiedInsightsRequest,
        db: Session
    ) -> Dict[str, Any]:
        """Вычисление AI инсайтов (эмулируем)"""
        # Здесь заглушка - вызов реального LLM
        # В реальном проекте здесь был бы вызов InsightsEnrichLLMService
        
        return {
            "portfolio_summary": {
                "risk_score": "Medium",
                "diversification": "Fair",
                "recommendation": "Consider adding international exposure"
            },
            "positions_analysis": [
                {
                    "symbol": "AAPL",
                    "insights": {
                        "valuation": "Fairly valued",
                        "momentum": "Strong",
                        "action": "Hold"
                    }
                },
                {
                    "symbol": "GOOGL",
                    "insights": {
                        "valuation": "Undervalued", 
                        "momentum": "Neutral",
                        "action": "Buy on dips"
                    }
                }
            ],
            "market_outlook": {
                "current_trend": "Bullish",
                "key_risks": ["Interest rates", "Tech regulation"],
                "opportunities": ["International stocks", "REITs"]
            }
        }
    
    def safe_cache_save(
        self,
        cache_key: str,
        data: Dict[str, Any],
        model_name: str,
        compute_ms: int,
        llm_ms: int,
        mode: str
    ) -> None:
        """Безопасное сохранение в кэш с обработкой ошибок"""
        try:
            self.cache_service.set_cache_entry(
                cache_key, data, model_name, compute_ms, llm_ms, mode
            )
        except Exception as e:
            logger.error(f"Failed to save to cache: {e}")
            # Не падаем на ошибке кэша - это опциональная оптимизация


# === API Endpoints ===

unified_service = UnifiedInsightsService()


@router.get("/", response_model=UnifiedInsightsResponse)
async def get_unified_insights(
    user_id: UUID = Query(..., description="ID пользователя"),
    cache: str = Query(CacheMode.DEFAULT, description="Cache mode: default|bypass|refresh"),
    # Альтернативный способ через заголовок
    x_cache_mode: Optional[str] = Header(None, alias="X-Cache-Mode"),
    # ETag поддержка
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
    db: Session = Depends(get_db)
):
    """
    Получение AI инсайлов с унифицированным кэшированием
    
    Реализует контракт согласно спецификации:
    - Режимы default/bypass/refresh через query или header
    - Прозрачность через response fields и headers  
    - Метрики задержки LLM и E2E
    - Защита от штормов через single-flight
    
    Args:
        user_id: ID пользователя
        cache: Режим кэширования (приоритет параметру если есть)
        x_cache_mode: Альтернативный способ передачи режима через header
        db: Сессия базы данных
    
    Returns:
        Insights с метаданными кэша согласно спецификации
    """
    
    # Определяем режим кэширования (приоритет параметру)
    cache_mode = cache if cache in [CacheMode.DEFAULT, CacheMode.BYPASS, CacheMode.REFRESH] else \
                 x_cache_mode if x_cache_mode in [CacheMode.DEFAULT, CacheMode.BYPASS, CacheMode.REFRESH] else \
                 CacheMode.DEFAULT
    
    # Создаём модель запроса из query параметров
    request = UnifiedInsightsRequest(
        horizon_months=6,  # Дефолт, можно расширить для получения из query
        risk_profile="Balanced",
        model="llama3.1:8b",
        temperature=0.2,
        top_p=1.0,
        max_tokens=400,
        locale="en",
        include_signals=True
    )
    
    try:
        response_data, headers_data = await unified_service.get_insights(
            user_id, request, cache_mode, db, if_none_match
        )
        
        # Создаём Response с заголовками согласно спецификации
        response = JSONResponse(
            content=response_data,
            headers=headers_data
        )
        return response
        
    except Exception as e:
        logger.error(f"Unified insights error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insights computation failed: {str(e)}"
        )


@router.post("/", response_model=UnifiedInsightsResponse)  
async def post_unified_insights(
    request: UnifiedInsightsRequest,
    user_id: UUID = Query(..., description="ID пользователя"),
    cache: str = Query(CacheMode.DEFAULT, description="Cache mode: default|bypass|refresh"),
    db: Session = Depends(get_db)
) -> UnifiedInsightsResponse:
    """
    POST версия для передачи сложных параметров в body
    
    Аналогична GET, но позволяет передавать полные параметры в JSON body
    вместо ограниченных query параметров.
    """
    
    cache_mode = cache if cache in [CacheMode.DEFAULT, CacheMode.BYPASS, CacheMode.REFRESH] else CacheMode.DEFAULT
    
    try:
        response_data, headers_data = await unified_service.get_insights(
            user_id, request, cache_mode, db
        )
        
        return JSONResponse(
            content=response_data,
            headers=headers_data
        )
        
    except Exception as e:
        logger.error(f"POST unified insights error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insights computation failed: {str(e)}"
        )


@router.delete("/cache/invalidate")
async def invalidate_unified_cache(
    request: CacheInvalidateRequest
) -> Dict[str, Any]:
    """
    Инвалидация кэша согласно спецификации
    
    Args:
        request: Параметры инвалидации
    
    Returns:
        Статистика инвалидации
    """
    
    cache_service = UnifiedCacheService()
    
    if request.full_clear:
        # Полная очистка всех кэшей
        pattern = "insights:unified:*"
        keys = cache_service.redis_client.keys(pattern)
        
        if keys:
            deleted_count = cache_service.redis_client.delete(*keys)
            return {
                "invalidated_keys": deleted_count,
                "type": "full_invalidate",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "invalidated_keys": 0,
                "type": "no_entries_found",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    elif request.user_id:
        # Очистка кэша конкретного пользователя
        result = cache_service.invalidate_user_cache(request.user_id)
        return {
            **result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or full_clear=true required"
        )


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Получение статистики кэша согласно спецификации
    
    Returns:
        Статистика использования кэша
    """
    
    cache_service = UnifiedCacheService()
    return cache_service.get_cache_stats()


# === Optional: ETag support ===

@router.get("/etag", response_model=UnifiedInsightsResponse)
async def get_insights_with_etag(
    user_id: UUID = Query(..., description="ID пользователя"),
    cache: str = Query(CacheMode.DEFAULT),
    if_none_match: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Опциональная поддержка ETag для HTTP кэширования
    
    Если клиент передаёт If-None-Match заголовок с актуальным ETag,
    возвращаем 304 Not Modified без данных.
    """
    
    request = UnifiedInsightsRequest()  # дефолтные параметры
    cache_mode = cache if cache in [CacheMode.DEFAULT, CacheMode.BYPASS, CacheMode.REFRESH] else CacheMode.DEFAULT
    
    try:
        response_data, headers_data = await unified_service.get_insights(
            user_id, request, cache_mode, db
        )
        
        # Создаём ETag на основе cache_key и last_updated
        etag = f'"{response_data["cache_key"]}:{response_data["last_updated"]}"'
        
        # Проверяем If-None-Match
        if if_none_match and if_none_match == etag:
            return JSONResponse(
                content=None,
                status_code=304,
                headers={
                    "ETag": etag,
                    **headers_data
                }
            )
        
        response = JSONResponse(
            content=response_data,
            headers={
                "ETag": etag,
                **headers_data
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"ETag insights error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insights computation failed: {str(e)}"
        )
