"""
Сервис анализа сентимента финансовых новостей
Использует FinLlama как основную модель с fallback на FinBERT
"""

import logging
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import httpx
from fastapi import HTTPException, status

from app.schemas_sentiment import (
    SentimentRequest, SentimentScoreResponse, SentimentItem, SentimentResult,
    SentimentLabel, SentimentModel, SentimentConfig
)
from app.routers.llm_proxy import LLMChatRequest

logger = logging.getLogger(__name__)

class FinLlamaSentimentAnalyzer:
    """Основной анализатор на FinLlama"""
    
    def __init__(self):
        self.model_name = "finllama"
        self.categories = ["negative", "neutral", "positive"]
        
    async def analyze_batch(self, items: List[SentimentItem]) -> List[SentimentResult]:
        """Батч анализ новостей через FinLlama"""
        logger.info(f"Starting FinLlama batch analysis for {len(items)} items")
        
        results = []
        
        # Обрабатываем до 50 элементов за раз для оптимальности
        batch_size = 50
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await self._analyze_chunk(batch)
            results.extend(batch_results)
            
            # Небольшая пауза между батчами
            if i + batch_size < len(items):
                await asyncio.sleep(0.1)
        
        logger.info(f"FinLlama completed analysis: {len(results)} results")
        return results
    
    async def _analyze_chunk(self, items: List[SentimentItem]) -> List[SentimentResult]:
        """Анализ небольшой группы новостей"""
        
        # Строим промпт для FinLlama (классификация)
        prompt = self._build_classification_prompt(items)
        
        try:
            # Вызов через Ollama proxy (FinLlama)
            request = LLMChatRequest(
                model=self.model_name,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1  # Low temperature для консистентности
            )
            
            # Используем существующий proxy к Ollama
            response = await self._call_ollama_sentiment(request)
            
            # Парсим JSON ответ от FinLlama
            parsed_results = self._parse_sentiment_response(response, items)
            
            return parsed_results
            
        except Exception as e:
            logger.error(f"FinLlama analysis failed: {e}")
            # Возвращаем neutral результаты с низкой уверенностью
            return self._get_fallback_results(items, str(e))
    
    def _build_classification_prompt(self, items: List[SentimentItem]) -> str:
        """Строим структурированный промпт для FinLlama"""
        
        prompt = f"""You are a financial sentiment analysis specialist. 
Analyze the sentiment (negative, neutral, positive) and confidence for each financial news item.
Respond with a valid JSON array without any additional text.

News items to analyze:
"""
        
        for i, item in enumerate(items):
            prompt += f"{i+1}. Symbol: {item.symbol}\n"
            prompt += f"   Date: {item.published_at.isoformat()}\n"
            prompt += f"   Text: {item.text[:200]}...\n\n"
        
        prompt += """
Please analyze each item and respond with JSON in this exact format:
[
  {{"index": 1, "sentiment": "positive|neutral|negative", "confidence": 0.85, "strength": 0.9}},
  {{"index": 2, "sentiment": "neutral", "confidence": 0.6, "strength": 0.4}},
  ...
]

Guidelines:
- sentiment: "positive" for bullish/good news, "negative" for bearish/bad news, "neutral" for mixed/unclear
- confidence: probability that the sentiment is correct (0.0-1.0)
- strength: intensity of the sentiment (0.0-1.0)
- Pay attention to financial context, market impact, earnings, partnerships, regulation
"""
        
        return prompt
    
    async def _call_ollama_sentiment(self, request: LLMChatRequest) -> str:
        """Вызов Ollama для анализа сентимента"""
        
        # Используем внутренний API для избежания циклических импортов
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/llm/chat",
                json=request.dict(),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"FinLlama service unavailable: {response.status_code}"
                )
            
            return response.text
    
    def _parse_sentiment_response(self, response: str, items: List[SentimentItem]) -> List[SentimentResult]:
        """Парсинг ответа FinLlama с валидацией"""
        results = []
        
        try:
            # Извлекаем JSON из ответа
            clean_response = self._extract_json_from_response(response)
            parsed_data = json.loads(clean_response)
            
            if not isinstance(parsed_data, list):
                raise ValueError("Expected JSON array")
            
            # Сопоставляем результаты с исходными элементами
            for item_data in parsed_data:
                index = item_data.get("index", 0) - 1  # 1-based to 0-based
                
                if 0 <= index < len(items):
                    item = items[index]
                    
                    # Валидируем и нормализуем данные
                    sentiment_str = item_data.get("sentiment", "neutral").lower()
                    confidence = float(item_data.get("confidence", 0.0))
                    strength = float(item_data.get("strength", confidence))
                    
                    # Мапим на enum
                    sentiment = self._map_sentiment_label(sentiment_str)
                    
                    # Валидация confidence
                    confidence = max(0.0, min(1.0, confidence))
                    strength = max(0.0, min(1.0, strength))
                    
                    # Низкая уверенность → neutral
                    if confidence < 0.5:
                        sentiment = SentimentLabel.NEUTRAL
                        confidence = 0.0
                    
                    result = SentimentResult(
                        symbol=item.symbol,
                        sentiment=sentiment,
                        confidence=confidence,
                        strength=strength,
                        note="finllama" if confidence >= 0.5 else "low_confidence"
                    )
                    
                    results.append(result)
                else:
                    logger.warning(f"Invalid index {index} in FinLlama response")
            
            return results
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse FinLlama response: {e}")
            return self._get_fallback_results(items, f"parse_error: {e}")
    
    def _extract_json_from_response(self, response: str) -> str:
        """Извлекаем чистый JSON из ответа модели"""
        
        # Ищем JSON массив в ответе
        start_idx = response.find('[')
        end_idx = response.rfind(']') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            return response[start_idx:end_idx]
        
        # Альтернативный поиск
        lines = response.split('\n')
        for line in lines:
            if line.strip().startswith('[') and line.strip().endswith(']'):
                return line.strip()
        
        raise ValueError("No valid JSON array found in response")
    
    def _map_sentiment_label(self, sentiment_str: str) -> SentimentLabel:
        """Мапинг строки на enum sentiment"""
        
        sentiment_lower = sentiment_str.lower().strip()
        
        if sentiment_lower in ['positive', 'bullish', 'optimistic', 'good']:
            return SentimentLabel.POSITIVE
        elif sentiment_lower in ['negative', 'bearish', 'pessimistic', 'bad']:
            return SentimentLabel.NEGATIVE
        else:
            return SentimentLabel.NEUTRAL
    
    def _get_fallback_results(self, items: List[SentimentItem], error_reason: str) -> List[SentimentResult]:
        """Fallback результаты при ошибке"""
        return [
            SentimentResult(
                symbol=item.symbol,
                sentiment=SentimentLabel.NEUTRAL,
                confidence=0.0,
                strength=0.0,
                note=f"finllama_error: {error_reason}"
            )
            for item in items
        ]


class FinBERTSentimentAnalyzer:
    """Fallback анализатор на FinBERT"""
    
    def __init__(self):
        self.model_name = "FinBERT"
        self.base_url = "http://localhost:8001/finbert"  # Предполагаемый endpoint
    
    async def analyze_batch(self, items: List[SentimentItem]) -> List[SentimentResult]:
        """Батч анализ через FinBERT"""
        logger.info(f"Starting FinBERT fallback analysis for {len(items)} items")
        
        try:
            # Простой HTTP вызов к FinBERT сервису
            request_data = {
                "texts": [item.text for item in items],
                "symbols": [item.symbol for item in items]
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/predict",
                    json=request_data
                )
                
                if response.status_code == 200:
                    parsed_results = self._parse_finbert_response(response.json(), items)
                    logger.info("FinBERT analysis completed successfully")
                    return parsed_results
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"FinBERT service error: {response.status_code}"
                    )
                    
        except Exception as e:
            logger.error(f"FinBERT analysis failed: {e}")
            return self._get_fallback_results(items, str(e))
    
    def _parse_finbert_response(self, response_data: Dict[str, Any], items: List[SentimentItem]) -> List[SentimentResult]:
        """Парсинг ответа FinBERT"""
        results = []
        
        predictions = response_data.get("predictions", [])
        confidences = response_data.get("confidences", [])
        
        for i, item in enumerate(items):
            if i < len(predictions):
                # FinBERT возвращает индексы классов: 0=negative, 1=neutral, 2=positive
                class_idx = predictions[i]
                confidence = confidences[i] if i < len(confidences) else 0.5
                
                # Мапим индексы на лейблы
                sentiment_labels = [
                    SentimentLabel.NEGATIVE,
                    SentimentLabel.NEUTRAL, 
                    SentimentLabel.POSITIVE
                ]
                
                sentiment = sentiment_labels[class_idx] if 0 <= class_idx <= 2 else SentimentLabel.NEUTRAL
                
                results.append(SentimentResult(
                    symbol=item.symbol,
                    sentiment=sentiment,
                    confidence=max(0.0, min(1.0, confidence)),
                    strength=max(0.0, min(1.0, confidence * 0.9)),  # FinBERT обычно менее уверен в strength
                    note="finbert_fallback"
                ))
            else:
                results.append(results[-1] if results else self._get_fallback_results([item], "parse_error")[0])
        
        return results
    
    def _get_fallback_results(self, items: List[SentimentItem], error_reason: str) -> List[SentimentResult]:
        """Минимальный fallback"""
        return [
            SentimentResult(
                symbol=item.symbol,
                sentiment=SentimentLabel.NEUTRAL,
                confidence=0.0,
                strength=0.0,
                note=f"finbert_error: {error_reason}"
            )
            for item in items
        ]


class SentimentAnalysisService:
    """Основной сервис анализа сентимента с автоматическим fallback"""
    
    def __init__(self):
        self.finllama = FinLlamaSentimentAnalyzer()
        self.finbert = FinBERTSentimentAnalyzer()
        self.config = SentimentConfig()
        
    async def analyze_sentiment_batch(self, request: SentimentRequest) -> SentimentScoreResponse:
        """Основной метод анализа с автоматическим fallback"""
        
        logger.info(f"Starting sentiment analysis: {request.model} for {len(request.items)} items")
        
        start_time = datetime.utcnow()
        
        try:
            # Пытаемся использовать основную модель
            if request.model == SentimentModel.FINLLAMA:
                results = await self.finllama.analyze_batch(request.items)
                model_used = SentimentModel.FINLLAMA
            else:
                results = await self.finbert.analyze_batch(request.items)
                model_used = SentimentModel.FINBERT
            
            # Проверяем качество результатов
            avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0
            failed_count = sum(1 for r in results if r.confidence < self.config.confidence_threshold)
            
            # Fallback если слишком много неуверенных результатов
            if avg_confidence < 0.4 and request.model == SentimentModel.FINLLAMA:
                logger.warning(f"FinLlama low confidence ({avg_confidence:.2f}), switching to FinBERT")
                results = await self.finbert.analyze_batch(request.items)
                model_used = SentimentModel.FINBERT
        
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            
            # Автоматический fallback на FinBERT
            try:
                results = await self.finbert.analyze_batch(request.items)
                model_used = SentimentModel.FINBERT
            except Exception as fallback_error:
                logger.error(f"FinBERT fallback also failed: {fallback_error}")
                # Последний fallback - нейтральные результаты
                model_used = SentimentModel.FINLLAMA  # Для логирования
                results = [
                    SentimentResult(
                        symbol=item.symbol,
                        sentiment=SentimentLabel.NEUTRAL,
                        confidence=0.0,
                        strength=0.0,
                        note="duplicate_fallback"
                    )
                    for item in request.items
                ]
        
        # Подсчитываем статистику
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        successful = sum(1 for r in results if r.confidence >= self.config.confidence_threshold)
        failed = len(results) - successful
        final_avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0
        
        logger.info(f"Sentiment analysis completed: {model_used}, {elapsed_ms}ms, {successful}/{len(results)} successful")
        
        return SentimentScoreResponse(
            model=model_used,
            results=results,
            as_of=datetime.utcnow(),
            total_processed=len(results),
            successful=successful,
            failed=failed,
            avg_confidence=final_avg_confidence
        )
