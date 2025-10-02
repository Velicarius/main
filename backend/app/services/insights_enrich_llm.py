"""
Insights v2 - Component: insights_enrich_llm
Обогащение LLM: Llama-3.1-8B для генерации текстовых инсайтов
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import HTTPException

from app.schemas_insights_v2 import PreparedInsights, LLMInsightsResponse
from app.routers.llm_proxy import LLMChatRequest, generate_with_ollama

logger = logging.getLogger(__name__)


class LLMSchemaBuilder:
    """Билдер JSON схемы для Llama-3.1-8B"""
    
    @staticmethod
    def get_insights_schema(num_positions: int) -> Dict[str, Any]:
        """
        Создает строгую JSON схему для инсайтов
        Для Llama-3.1-8B с температурой 0.2
        """
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "schema_version": {
                    "type": "string",
                    "enum": ["insights.v2"],
                    "description": "Версия схемы ответа"
                },
                "as_of_copy": {
                    "type": ["string", "null"],
                    "description": "Эхо даты для трассировки"
                },
                "positions": {
                    "type": "array",
                    "minItems": num_positions,
                    "maxItems": num_positions,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Символ инструмента"
                            },
                            "insights": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "thesis": {
                                        "type": "string",
                                        "maxLength": 240,
                                        "description": "Краткий тезис позиции"
                                    },
                                    "risks": {
                                        "type": "array",
                                        "minItems": 1,
                                        "maxItems": 3,
                                        "items": {"type": "string"},
                                        "description": "Список рисков"
                                    },
                                    "action": {
                                        "type": "string",
                                        "enum": ["Add", "Hold", "Trim", "Hedge"],
                                        "description": "Рекомендуемое действие"
                                    },
                                    "signals": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "valuation": {
                                                "type": "string",
                                                "enum": ["cheap", "fair", "expensive"],
                                                "description": "Оценка дороговизны"
                                            },
                                            "momentum": {
                                                "type": "string", 
                                                "enum": ["up", "flat", "down", "neutral"],
                                                "description": "Моментум"
                                            },
                                            "quality": {
                                                "type": "string",
                                                "enum": ["high", "med", "low"],
                                                "description": "Качество компании"
                                            }
                                        },
                                        "required": ["valuation", "momentum", "quality"]
                                    }
                                },
                                "required": ["thesis", "risks", "action", "signals"]
                            }
                        },
                        "required": ["symbol", "insights"]
                    }
                }
            },
            "required": ["schema_version", "positions"]
        }


class LLMPromptBuilder:
    """Билдер промптов для Llama-3.1-8B"""
    
    @staticmethod
    def build_system_prompt() -> str:
        """Системный промпт настроен для Llama-3.1-8B"""
        return (
            "Ты — опытный портфельный аналитик с экспертизой в риск-менеджменте. "
            "Твоя задача — предоставить краткие, точные инсайты по каждой позиции портфеля. "
            "Анализируй только переданные данные, не делай предположений о неполной информации. "
            "Говори профессионально и кратко. "
            "Все числа уже рассчитаны — фокусируйся на качественном анализе и текстовых выводах. "
            "Твои рекомендации носят образовательный характер, окончательные решения принимает инвестор."
        )
    
    @staticmethod
    def build_user_prompt(prepared_data: PreparedInsights, params: Dict[str, Any]) -> str:
        """
        Основной промпт для анализа позиций
        Передаем только необходимые данные для текстовой генерации
        """
        positions_text = []
        for pos in prepared_data.positions:
            positions_text.append(
                f"• {pos.symbol} ({pos.name}): "
                f"Индустрия {pos.industry}, "
                f"Вес {pos.weight_pct}%, "
                f"Прогноз роста {pos.growth_forecast_pct or 'НД'}%, "
                f"Ожидаемая доходность {pos.expected_return_horizon_pct}%, "
                f"Риск {pos.risk_score_0_100 or 'НД'}/100, "
                f"Волатильность {pos.volatility_pct or 'НД'}%"
            )
        
        prompt = f"""
Проанализируй каждую позицию портфеля и предоставь краткий пер-позиционный анализ:

ПАРАМЕТРЫ АНАЛИЗА:
- Горизонт анализа: {params.get('horizon_months', 6)} месяцев
- Профиль риска: {params.get('risk_profile', 'Balanced')}
- Дата анализа: {prepared_data.summary.as_of}

КЛАССИФИКАЦИОННЫЕ ПРАВИЛА:
- Риск по порогам: Low 0-33, Moderate 34-66, High 67-100
- Рост по горбам: High ≥15%, Mid 5-<15%, Low/<5%)

ПОЗИЦИИ ПОРТFEЛЯ:
{chr(10).join(positions_text)}

ТРЕБОВАНИЯ К АНАЛИЗУ:
1. Для каждой позиции дай краткий тезис (макс 240 символов)
2. Выдели 1-3 ключевых риска  
3. Определи рекомендуемое действие: Add/Hold/Trim/Hedge
4. Оцени сигналы: valuation (cheap/fair/expensive), momentum (up/flat/down/neutral), quality (high/med/low)
5. Основывай выводы на цифрах из контекста
6. Избегай общих фраз — будь конкретен

Верни строго валидный JSON согласно схеме.
"""
        
        return prompt.strip()


class LLMValidator:
    """Валидатор ответов LLM"""
    
    @staticmethod
    def validate_symbols_match(request_symbols: List[str], response_symbols: List[str]) -> bool:
        """Проверяем что символы в ответе совпадают с запросом"""
        request_set = set(request_symbols)
        response_set = set(response_symbols)
        return request_set == response_set
    
    @staticmethod
    def validate_enum_values(response_data: Dict[str, Any]) -> List[str]:
        """Валидирует допустимые значения enums"""
        errors = []
        
        validators = {
            'action': ['Add', 'Hold', 'Trim', 'Hedge'],
            'valuation': ['cheap', 'fair', 'expensive'], 
            'momentum': ['up', 'flat', 'down', 'neutral'],
            'quality': ['high', 'med', 'low']
        }
        
        for position in response_data.get('positions', []):
            insights = position.get('insights', {})
            symbol = position.get('symbol', 'UNKNOWN')
            
            # Проверяем action
            action = insights.get('action')
            if action and action not in validators['action']:
                errors.append(f"{symbol}: Invalid action '{action}'")
            
            # Проверяем signals
            signals = insights.get('signals', {})
            for signal_name, valid_values in [('valuation', validators['valuation']), 
                                             ('momentum', validators['momentum']),
                                             ('quality', validators['quality'])]:
                signal_value = signals.get(signal_name)
                if signal_value and signal_value not in valid_values:
                    errors.append(f"{symbol}: Invalid {signal_name} '{signal_value}'")
            
            # Проверяем длину тезиса
            thesis = insights.get('thesis', '')
            if len(thesis) > 240:
                errors.append(f"{symbol}: Thesis too long ({len(thesis)} chars)")
            
            # Проверяем количество рисков
            risks = insights.get('risks', [])
            if len(risks) < 1 or len(risks) > 3:
                errors.append(f"{symbol}: Invalid risks count ({len(risks)})")
        
        return errors
    
    @staticmethod
    def repair_response_basic(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Базовая починка ответа LLM"""
        repaired = response_data.copy()
        
        for position in repaired.get('positions', []):
            insights = position.get('insights', {})
            
            # Фиксим длину тезиса
            thesis = insights.get('thesis', '')
            if len(thesis) > 240:
                insights['thesis'] = thesis[:237] + "..."
            
            # Фиксим количество рисков
            risks = insights.get('risks', [])
            if len(risks) > 3:
                insights['risks'] = risks[:3]
            elif len(risks) < 1:
                insights['risks'] = ['Риск не оценен']
            
            # Фиксим недостающие сигналы
            signals = insights.get('signals', {})
            if 'valuation' not in signals:
                signals['valuation'] = 'fair'
            if 'momentum' not in signals:
                signals['momentum'] = 'neutral'
            if 'quality' not in signals:
                signals['quality'] = 'med'
            
            # Фиксим отсутствующее действие
            if 'action' not in insights:
                insights['action'] = 'Hold'
        
        return repaired


class InsightsEnrichLLMService:
    """Сервис обогащения данных LLM"""
    
    def __init__(self):
        self.schema_builder = LLMSchemaBuilder()
        self.prompt_builder = LLMPromptBuilder()
        self.validator = LLMValidator()
        
    async def enrich_insights(
        self, 
        prepared_data: PreparedInsights,
        params: Dict[str, Any]
    ) -> LLMInsightsResponse:
        """
        Шаг B: Обогащение LLM
        Передаем только данные необходимые для генерации текстов
        """
        
        # Подготавливаем запрос к LLM
        system_prompt = self.prompt_builder.build_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(prepared_data, params)
        
        # JSON схема для строгого формата
        num_positions = len(prepared_data.positions)
        json_schema = self.schema_builder.get_insights_schema(num_positions)
        
        # Создаем запрос к Llama-3.1-8B
        llm_request = LLMChatRequest(
            model=params.get('model', 'llama3.1:8b'),
            system=system_prompt,
            prompt=user_prompt,
            json_schema=json_schema,
            temperature=0.2,  # Низкая температура для стабильности
            max_tokens=400   # Ограниченный контекст для краткости
        )
        
        logger.info(f"Sending LLM request for {num_positions} positions")
        
        try:
            # Отправляем запрос к Ollama
            ollama_response = await generate_with_ollama(llm_request)
            response_text = ollama_response.get("response", "")
            
            # Парсим JSON ответ
            response_data = json.loads(response_text)
            
            # Первичная валидация
            if response_data.get('schema_version') != 'insights.v2':
                raise ValueError("Schema version mismatch")
            
            # Валидация символов
            response_symbols = [p['symbol'] for p in response_data.get('positions', [])]
            request_symbols = [p.symbol for p in prepared_data.positions]
            
            if not self.validator.validate_symbols_match(request_symbols, response_symbols):
                raise ValueError(f"Symbols mismatch: {request_symbols} vs {response_symbols}")
            
            # Валидация значений enum
            enum_errors = self.validator.validate_enum_values(response_data)
            if enum_errors:
                logger.warning(f"Enum validation errors: {enum_errors}")
                # Попробуем починить
                response_data = self.validator.repair_response_basic(response_data)
                
                # Повторная валидация после ремонта
                enum_errors_after = self.validator.validate_enum_values(response_data)
                if enum_errors_after:
                    raise ValueError(f"Cannot repair enum errors: {enum_errors_after}")
            
            # Формируем финальный ответ
            return LLMInsightsResponse(**response_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            # Repair-retry логика
            return await self._retry_with_repair(llm_request, e)
            
        except Exception as e:
            logger.error(f"LLM enrichment failed: {e}")
            raise
    
    async def _retry_with_repair(
        self, 
        original_request: LLMChatRequest, 
        original_error: Exception
    ) -> LLMInsightsResponse:
        """
        Repair-retry логика согласно техническому заданию
        """
        logger.info("Attempting repair-retry")
        
        # Создаем новый запрос с уточнением
        repair_request = original_request.model_copy()
        repair_request.prompt = (
            "ПРЕДЫДУЩИЙ ОТВЕТ БЫЛ НЕВАЛИДНЫМ JSON. "
            "Верни СТРОГО валидный JSON без лишних символов, markdown или текста. "
            "Следуй схеме точно.\n\n" + original_request.prompt
        )
        
        try:
            # Повторный запрос
            ollama_response = await generate_with_ollama(repair_request)
            response_text = ollama_response.get("response", "")
            
            # Попытка парсинга
            response_data = json.loads(response_text)
            return LLMInsightsResponse(**response_data)
            
        except Exception as retry_error:
            logger.error(f"Repair-retry also failed: {retry_error}")
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "llm_validation_failed",
                    "message": "Model failed to produce valid JSON after 2 attempts",
                    "original_error": str(original_error),
                    "retry_error": str(retry_error)
                }
            )
