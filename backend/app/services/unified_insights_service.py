"""
Unified Insights Service - единый сервис для всех AI insights на странице Insights
Объединяет кэширование, генерацию LLM и SWR логику
"""

import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.ai.portfolio_assessor import build_snapshot, make_ai_inputs, result_json_schema
from app.ai.openai_client import get_client, default_model
from app.routers.llm_proxy import LLMChatRequest, generate_with_ollama
from app.services.unified_cache_service import (
    UnifiedCacheService, 
    CacheMode, 
    CacheMetadata
)

logger = logging.getLogger(__name__)


class UnifiedInsightsRequest:
    """Единый запрос для всех insights операций"""
    def __init__(self, **kwargs):
        self.horizon_months = kwargs.get('horizon_months', 6)
        self.risk_profile = kwargs.get('risk_profile', 'Balanced')
        self.model = kwargs.get('model', 'llama3.1:8b')
        self.temperature = kwargs.get('temperature', 0.2)
        self.language = kwargs.get('language', 'ru')
        self.cache_mode = kwargs.get('cache_mode', 'default')
        
    def to_dict(self):
        return {
            'horizon_months': self.horizon_months,
            'risk_profile': self.risk_profile,
            'model': self.model,
            'temperature': self.temperature,
            'language': self.language
        }


class UnifiedInsightsResponse:
    """Единый ответ со всеми метаданными"""
    def __init__(self, 
                 data: Dict[str, Any],
                 cached: bool = False,
                 cache_key: str = "",
                 model_name: str = "",
                 llm_ms: int = 0,
                 compute_ms: int = 0,
                 headers: Optional[Dict[str, str]] = None):
        self.data = data
        self.cached = cached
        self.cache_key = cache_key
        self.model_name = model_name
        self.llm_ms = llm_ms
        self.compute_ms = compute_ms
        self.headers = headers or {}
        
    def to_dict(self):
        return {
            "cached": self.cached,
            "cache_key": self.cache_key,
            "model_name": self.model_name,
            "last_updated": datetime.now().isoformat(),
            "compute_ms": self.compute_ms,
            "llm_ms": self.llm_ms,
            "data": self.data,
            "headers": self.headers
        }


class UnifiedInsightsService:
    """Единый сервис для всех AI insights операций"""
    
    def __init__(self):
        self.cache_service = UnifiedCacheService()
        
    def _determine_provider(self, model: str) -> Tuple[str, str]:
        """Определяем провайдера по модели"""
        if model and model.startswith(('llama', 'gemma', 'qwen', 'mistral', 'codellama')):
            return model, "ollama"
        else:
            return model or default_model(), "openai"
    
    async def get_insights(
        self,
        user_id: UUID,
        request: UnifiedInsightsRequest,
        db: Session
    ) -> UnifiedInsightsResponse:
        """
        Основной метод получения insights с полным кэшированием
        """
        start_time = time.time()
        request_data = request.to_dict()
        
        logger.info(f"🔄 Unified insights request for user {user_id}, mode={request.cache_mode}")
        
        # Проверяем SWR кэш
        if request.cache_mode == CacheMode.DEFAULT:
            cache_metadata, cached_data, needs_background_refresh = self.cache_service.get_insights_with_swr(
                str(user_id), request_data
            )
            
            # Возвращаем кэшированные данные если найдены
            if cache_metadata and cached_data:
                computation_ms = int((time.time() - start_time) * 1000)
                
                headers = {
                    "ETag": cache_metadata.etag,
                    "X-Cache": "STALE" if cache_metadata.is_stale else "HIT",
                    "X-Cache-Age": str(cache_metadata.cache_age),
                    "X-Generated-At": cache_metadata.last_updated.isoformat(),
                    "X-LLM-Model": cache_metadata.model_name,
                    "X-Features-Version": "v3",
                    "X-Cache-Key": cache_metadata.cache_key[:16] + "...",
                    "X-LLM-Latency-MS": str(cache_metadata.llm_latency_ms),
                }
                
                # Планируем фоновое обновление для STALE данных
                if needs_background_refresh:
                    logger.info(f"🚀 Scheduling background refresh for stale cache")
                    self._schedule_background_refresh(user_id, request, db)
                
                return UnifiedInsightsResponse(
                    data=cached_data,
                    cached=True,
                    cache_key=cache_metadata.cache_key,
                    model_name=cache_metadata.model_name,
                    llm_ms=cache_metadata.llm_latency_ms,
                    compute_ms=computation_ms,
                    headers=headers
                )
        
        # Генерируем свежие данные если кэш miss или bypass
        logger.info(f"🔥 Generating fresh insights for user {user_id}")
        
        # Готовим данные портфеля и LLM запрос
        snapshot = build_snapshot(db, user_id)
        inputs = make_ai_inputs(snapshot, request.language)
        schema = result_json_schema()
        
        # Определяем провайдера и модель
        model, provider = self._determine_provider(request.model)
        
        # Генерируем через соответствующий провайдер
        llm_start = time.time()
        
        try:
            if provider == "ollama":
                response = await self._generate_via_ollama(inputs, schema, model, request.temperature)
            else:
                response = await self._generate_via_openai(inputs, schema, model, request.temperature)
            
            llm_ms = int((time.time() - llm_start) * 1000)
            
            # Парсим и валидируем ответ
            insights_data = self._parse_llm_response(response)
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Возвращаем fallback данные
            insights_data = self._get_fallback_insights(snapshot)
            llm_ms = 0
        
        compute_ms = int((time.time() - start_time) * 1000)
        
        # Сохраняем в кэш
        cache_key, etag = self.cache_service.save_insights_with_swr(
            str(user_id), request_data, insights_data, compute_ms, llm_ms
        )
        
        # Формируем ответ
        headers = {
            "ETag": etag,
            "X-Cache": "MISS",
            "X-Cache-Age": "0",
            "X-Cache-KEY": cache_key[:16] + "...",
            "X-LLM-Model": model,
            "X-LLM-Latency-MS": str(llm_ms),
            "X-Generated-At": datetime.now().isoformat(),
            "X-Features-Version": "v3"
        }
        
        return UnifiedInsightsResponse(
            data=insights_data,
            cached=False,
            cache_key=cache_key,
            model_name=model,
            llm_ms=llm_ms,
            compute_ms=compute_ms,
            headers=headers
        )
    
    async def _generate_via_ollama(
        self,
        inputs: Dict[str, Any],
        schema: Dict[str, Any],
        model: str,
        temperature: float
    ) -> str:
        """Генерация через Ollama"""
        request = LLMChatRequest(
            model=model,
            prompt=inputs["user"],
            system=inputs["system"],
            json_schema=schema["schema"],
            temperature=temperature,
            max_tokens=4000
        )
        
        response = await generate_with_ollama(request)
        return response["response"]
    
    async def _generate_via_openai(
        self,
        inputs: Dict[str, Any],
        schema: Dict[str, Any],
        model: str,
        temperature: float
    ) -> str:
        """Генерация через OpenAI"""
        try:
            client = get_client()
        except RuntimeError as e:
            raise ValueError(f"OpenAI client unavailable: {e}")
        
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": inputs["system"]},
                {"role": "user", "content": inputs["system"]},
                {"role": "developer", "content": json.dumps(inputs["context"])},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema["name"],
                    "schema": schema["schema"],
                    "strict": schema["strict"],
                }
            }
        )
        
        return resp.output_text
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Парсинг и валидация ответа LLM"""
        try:
            data = json.loads(response)
            # Базовая валидация структуры
            required_fields = ["rating", "overview", "insights"]
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Missing required field: {field}")
                    data[field] = self._get_default_field(field)
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._get_fallback_insights()
    
    def _get_fallback_insights(self, snapshot=None) -> Dict[str, Any]:
        """Fallback данные при ошибке LLM"""
        return {
            "rating": {
                "score": 5.0,
                "label": "unknown",
                "risk_level": "medium"
            },
            "overview": {
                "headline": "Portfolio analysis unavailable",
                "tags": ["Data gap", "System error"],
                "key_strengths": [],
                "key_concerns": []
            },
            "insights": ["Portfolio analysis temporarily unavailable"],
            "risks": [],
            "performance": {
                "since_buy_pl_pct": None,
                "comment": "Analysis unavailable"
            },
            "diversification": {
                "score": 5.0,
                "concentration_risk": "medium"
            },
            "actions": [],
            "summary_markdown": "Portfolio analysis is currently unavailable. Please try again later."
        }
    
    def _get_default_field(self, field: str) -> Any:
        """Дефолтные значения для отсутствующих полей"""
        defaults = {
            "rating": {"score": 5.0, "label": "unknown", "risk_level": "medium"},
            "overview": {"headline": "Analysis incomplete"},
            "insights": ["Analysis incomplete"],
            "risks": [],
            "actions": []
        }
        return defaults.get(field, {})
    
    def _schedule_background_refresh(
        self,
        user_id: UUID,
        request: UnifiedInsightsRequest,
        db: Session
    ):
        """Планирование фонового обновления кэша"""
        # В реальной реализации здесь была бы фоновая задача
        logger.info(f"Scheduling background refresh for user {user_id}")
        # TODO: Implement background task scheduling
    
    async def refresh_insights(
        self,
        user_id: UUID,
        request: UnifiedInsightsRequest,
        db: Session
    ) -> UnifiedInsightsResponse:
        """Принудительное обновление insights"""
        request.cache_mode = CacheMode.BYPASS
        return await self.get_insights(user_id, request, db)





