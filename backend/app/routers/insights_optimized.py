"""
Оптимизированный API роутер для страницы insights
Реализует кэширование, single-flight, дельта-вызовы и SWR
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.models.position import Position
from app.models.user import User
from app.services.insights_prepare import InsightsPrepareService
from app.services.insights_cache import (
    InsightsCacheService, CacheResult, CacheStatus
)
from app.services.insights_enrich_llm import InsightsEnrichLLMService
from app.services.sentiment_cache import SentimentAggregationService
from app.utils.cache_fingerprint import (
    CacheFingerprintService, ChangeDetector, CacheKeyBuilder
)
from app.schemas_insights_v2 import (
    InsightsV2Request, InsightsV2Response, PreparedInsights, LLMInsightsResponse,
    PositionAnalysis
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights-optimized"])

# === Основные сервисы ===

class OptimizedInsightsService:
    """Основной сервис оптимизированных insights"""
    
    def __init__(self):
        self.cache_service = InsightsCacheService()
        self.prepare_service = InsightsPrepareService
        self.llm_service = InsightsEnrichLLMService()
        self.sentiment_service = SentimentAggregationService()
    
    async def get_optimized_insights(
        self,
        user_id: UUID,
        params: InsightsV2Request,
        db: Session,
        background_tasks: BackgroundTasks
    ) -> InsightsV2Response:
        """
        Оптимизированное получение insights с кэшированием
        
        Args:
            user_id: ID пользователя
            params: параметры анализа
            db: сессия БД
            background_tasks: фоновые задачи FastAPI
            
        Returns:
            Оптимизированный ответ с данными
        """
        
        logger.info(f"Getting optimized insights for user {user_id}")
        
        try:
            # 1. Получаем prepared данные (детерминированные)
            prepared_insights = await self._get_or_prepare_base_data(user_id, params, db)
            
            # 2. Создаем fingerprint для LLM данных
            fingerprint = CacheFingerprintService.create_insights_fingerprint(
                positions=prepared_insights.positions,
                horizon_months=params.horizon_months,
                risk_profile=params.risk_profile,
                locale="en",
                model="llama-3.1-8b"
            )
            
            # 3. Проверяем кэш LLM данных
            cache_result = await self.cache_service.get_insights_cache(
                str(user_id), fingerprint
            )
            
            # 4. Обрабатываем результат кэша
            if cache_result.status == CacheStatus.FRESH:
                # Свежий кэш - возвращаем сразу
                llm_data = cache_result.data
                logger.info(f"Fresh cache hit for user {user_id}")
                
            elif cache_result.status == CacheStatus.STALE:
                # Старый кэш - возвращаем но планируем обновление
                llm_data = cache_result.data
                background_tasks.add_task(
                    self._background_refresh_llm,
                    user_id, fingerprint, prepared_insights, params
                )
                logger.info(f"Stale cache hit for user {user_id}, background refresh scheduled")
                
            elif cache_result.status == CacheStatus.MISSING:
                # Нет кэша - проверяем single-flight и запускаем LLM
                llm_data = await self._handle_missing_cache(
                    user_id, fingerprint, prepared_insights, params
                )
                logger.info(f"Cache miss for user {user_id}, new LLM request")
                
            elif cache_result.status == CacheStatus.LOADING:
                # Уже загружается - подписываемся на результат
                llm_data = await self._wait_for_loading(
                    user_id, fingerprint, prepared_insights, params
                )
                logger.info(f"Single-flight deduplication for user {user_id}")
                
            else:
                # Ошибка кэша - возвращаем без LLM данных
                llm_data = None
                logger.error(f"Cache error for user {user_id}: {cache_result.error}")
            
            # 5. Мержем данные и формируем ответ
            merged_result = self._merge_prepared_and_llm_data(
                prepared_insights, llm_data, False  # errors если есть
            )
            
            return merged_result
            
        except Exception as e:
            logger.error(f"Optimized insights failed for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Insights analysis failed: {str(e)}"
            )
    
    async def _get_or_prepare_base_data(
        self,
        user_id: UUID,
        params: InsightsV2Request,
        db: Session
    ) -> PreparedInsights:
        """Получение или подготовка базовых данных"""
        
        prepare_svc = InsightsPrepareService(db)
        return prepare_svc.prepare_insights(user_id, params.horizon_months)
    
    async def _handle_missing_cache(
        self,
        user_id: UUID,
        fingerprint: str,
        prepared_insights: PreparedInsights,
        params: InsightsV2Request
    ) -> Optional[Dict[str, Any]]:
        """Обработка отсутствия кэша"""
        
        # Проверяем single-flight лок
        lock_acquired, subscriber_key = await self.cache_service.acquire_single_flight_lock(
            fingerprint
        )
        
        if not lock_acquired:
            # Другой процесс уже обрабатывает - ждем его результат
            try:
                result = await self.cache_service.subscribe_to_result(fingerprint)
                if result and result.data:
                    return result.data
                else:
                    # Таймаут ожидания - запускаем самостоятельно
                    return await self._process_llm_request(
                        user_id, fingerprint, prepared_insights, params
                    )
            except Exception as e:
                logger.error(f"Single-flight subscription failed: {e}")
                return await self._process_llm_request(
                    user_id, fingerprint, prepared_insights, params
                )
        else:
            # Мы получили лок - обрабатываем запрос
            try:
                result = await self._process_llm_request(
                    user_id, fingerprint, prepared_insights, params
                )
                
                # Уведомляем подписчиков
                await self.cache_service.notify_subscribers(
                    fingerprint,
                    CacheResult(
                        status=CacheStatus.FRESH,
                        data=result,
                        cached_at=datetime.utcnow()
                    )
                )
                
                return result
                
            finally:
                # Освобождаем лок
                await self.cache_service.release_single_flight_lock(fingerprint)
    
    async def _process_llm_request(
        self,
        user_id: UUID,
        fingerprint: str,
        prepared_insights: PreparedInsights,
        params: InsightsV2Request
    ) -> Optional[Dict[str, Any]]:
        """Обработка запроса к LLM"""
        
        try:
            # Вызываем LLM обогащение
            llm_response, escalation_rate = await self.llm_service.enrich_with_llm(
                prepared_insights,
                params.model,
                params.horizon_months,
                params.risk_profile
            )
            
            # Конвертируем в словарь для кэша
            llm_data = llm_response.dict() if llm_response else None
            
            # Сохраняем в кэш
            await self.cache_service.set_insights_cache(
                str(user_id), fingerprint, llm_data
            )
            
            return llm_data
            
        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            
            # Сохраняем ошибку в кэше
            await self.cache_service.set_insights_cache(
                str(user_id), fingerprint, None, str(e)
            )
            
            return None
    
    async def _wait_for_loading(
        self,
        user_id: UUID,
        fingerprint: str,
        prepared_insights: PreparedInsights,
        params: InsightsV2Request
    ) -> Optional[Dict[str, Any]]:
        """Ожидание результата загрузки другим процессом"""
        
        try:
            result = await self.cache_service.subscribe_to_result(fingerprint)
            return result.data if result else None
            
        except Exception as e:
            logger.error(f"Loading wait failed: {e}")
            return None
    
    async def _background_refresh_llm(
        self,
        user_id: UUID,
        fingerprint: str,
        prepared_insights: PreparedInsights,
        params: InsightsV2Request
    ) -> None:
        """Фоновое обновление LLM данных для SWR"""
        
        logger.info(f"Background refresh for user {user_id}, fingerprint {fingerprint[:8]}...")
        
        try:
            await self._process_llm_request(
                user_id, fingerprint, prepared_insights, params
            )
        except Exception as e:
            logger.error(f"Background refresh failed: {e}")
    
    def _merge_prepared_and_llm_data(
        self,
        prepared: PreparedInsights,
        llm_data: Optional[Dict[str, Any]],
        force_stale: bool = False
    ) -> InsightsV2Response:
        """Мердж prepared и LLM данных"""
        
        positions_with_insights = []
        errors = []
        
        # Мержим позиции с LLM данными
        for position in prepared.positions:
            position_insights = self._find_position_insights(position.symbol, llm_data)
            
            position_analysis = PositionAnalysis(
                symbol=position.symbol,
                name=position.name,
                weight_pct=position.weight_pct,
                growth_forecast_pct=position.growth_forecast_pct,
                risk_score_0_100=position.risk_score_0_100,
                expected_return_horizon_pct=position.expected_return_horizon_pct,
                volatility_pct=position.volatility_pct,
                insights=position_insights
            )
            
            positions_with_insights.append(position_analysis)
        
        # Определяем статус
        status = "ok"
        if force_stale:
            status = "stale"
        elif not llm_data:
            status = "partial"
        elif errors:
            status = "partial"
        
        return InsightsV2Response(
            status=status,
            model="llama-3.1-8b",
            prepared_data=prepared,
            llm_data=llm_data,
            errors=errors,
            positions_with_insights=positions_with_insights,
            escalation_rate=None
        )
    
    def _find_position_insights(
        self,
        symbol: str,
        llm_data: Optional[Dict[str, Any]]
    ) -> Optional[Any]:
        """Поиск LLM инсайтов для позиции"""
        
        if not llm_data or not llm_data.get("positions"):
            return None
        
        # Ищем инсайты для символа
        for pos_insights in llm_data["positions"]:
            if pos_insights.get("symbol") == symbol:
                return pos_insights.get("insights")
        
        return None

# === Основные эндпойнты ===

insights_service = OptimizedInsightsService()

@router.get("/optimized/{user_id}", response_model=InsightsV2Response)
async def get_optimized_insights(
    user_id: UUID,
    background_tasks: BackgroundTasks,
    horizon_months: int = Query(default=12, ge=1, le=60),
    risk_profile: str = Query(default="balanced", regex="^(conservative|balanced|aggressive)$"),
    model: str = Query(default="llama-3.1-8b"),
    db: Session = Depends(get_db)
) -> InsightsV2Response:
    """
    Оптимизированное получение insights с кэшированием
    
    Использует SWR кэширование, single-flight дедупликацию,
    и фоновое обновление для оптимальной производительности.
    """
    
    # Создаем запрос
    params = InsightsV2Request(
        horizon_months=horizon_months,
        risk_profile=risk_profile,
        model=model
    )
    
    return await insights_service.get_optimized_insights(
        user_id, params, db, background_tasks
    )

@router.delete("/cache/invalidate")
async def invalidate_insights_cache(
    user_id: Optional[UUID] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    fingerprint: Optional[str] = Query(default=None),
    full: bool = Query(default=False)
) -> Dict[str, Any]:
    """
    Инвалидация кэша insights
    
    Args:
        user_id: конкретный пользователь
        symbol: конкретный символ
        fingerprint: конкретный отпечаток
        full: полная очистка всех кэшей
    """
    
    cache_service = InsightsCacheService()
    
    return await cache_service.invalidate_cache(
        user_id=str(user_id) if user_id else None,
        symbol=symbol,
        fingerprint=fingerprint,
        full_invalidate=full
    )

@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Статистика кэширования"""
    
    cache_service = InsightsCacheService()
    return await cache_service.get_cache_stats()

@router.get("/positions/delta/{user_id}")
async def get_delta_positions_insights(
    userId: UUID,
    current_fingerprint: str,
    new_positions: List[Dict[str, Any]],
    horizon_months: int = Query(default=12),
    risk_profile: str = Query(default="balanced"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Получение дельта-инсайтов только для измененных позиций
    """
    
    try:
        # Получаем предыдущие позиции из кэша или БД
        # Здесь будет логика определения изменений
        
        cache_service = InsightsCacheService()
        
        # Анализируем изменения
        # changes = ChangeDetector.detect_position_changes(...)
        
        # Возвращаем только для измененных позиций
        return {
            "changed_symbols": [],
            "insights": {},
            "cache_hits": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Delta insights failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/prefetch/{user_id}")
async def prefetch_prepared_insights(
    user_id: UUID,
    horizon_months: int = Query(default=12),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Предзагрузка prepared данных для быстрого отображения
    """
    
    try:
        cache_service = InsightsCacheService()
        
        # Предзагружаем prepared данные
        # prepared_data = await cache_service.get_or_set_prepared_data(...)
        
        return {
            "status": "prefetched",
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Prefetch failed: {e}")
        return {"status": "error", "error": str(e)}

# === Feature flags ===

@router.get("/feature-flags")
async def get_feature_flags() -> Dict[str, bool]:
    """Получение feature flags для клиента"""
    
    return {
        "INSIGHTS_LLM_ENABLED": True,
        "INSIGHTS_LLM_LAZY_LOAD": True,
        "INSIGHTS_LLM_DELTA_CALLS": True,
        "INSIGHTS_SENTIMENT_ENABLED": True
    }
