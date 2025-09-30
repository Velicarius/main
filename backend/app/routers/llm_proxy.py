"""
LLM Proxy Router для AI Portfolio Analyzer
Зачем: Проксирует запросы к локальным LLM через Ollama API

Этот роутер позволяет:
- Отправлять запросы к локальным LLM (Llama, Gemma, Qwen)
- Получать структурированные JSON ответы
- Валидировать ответы через Pydantic схемы
- Делать retry при ошибках
"""

import json
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

# Настройка логирования
# Зачем: Отслеживаем запросы к LLM для отладки
logger = logging.getLogger(__name__)

# Создаем роутер
# Зачем: Группируем все LLM endpoints в одном месте
router = APIRouter(prefix="/llm", tags=["LLM"])

# Импортируем конфигурацию Ollama
from app.config import get_ollama_config
# Импортируем схемы портфеля
from app.schemas_v1.portfolio_v1 import get_portfolio_schema_v1

# Получаем конфигурацию Ollama
# Зачем: Используем централизованную конфигурацию вместо хардкода
ollama_config = get_ollama_config()
OLLAMA_BASE_URL = ollama_config["url"]
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_ENDPOINT = f"{OLLAMA_BASE_URL}/api/tags"

# Таймауты для HTTP запросов
# Зачем: Предотвращаем зависание при медленных ответах LLM
REQUEST_TIMEOUT = 300  # 5 минут на генерацию
CONNECT_TIMEOUT = 10   # 10 секунд на подключение


class LLMChatRequest(BaseModel):
    """
    Схема запроса к LLM
    Зачем: Валидируем входные данные и документируем API
    """
    model: str = Field(
        ..., 
        description="Название модели Ollama (например: llama3.1:8b, gemma2:9b, qwen2.5-coder:7b)"
    )
    system: Optional[str] = Field(
        None, 
        description="Системный промпт для настройки поведения модели"
    )
    prompt: str = Field(
        ..., 
        description="Основной промпт для генерации ответа"
    )
    json_schema: Optional[Dict[str, Any]] = Field(
        None, 
        description="JSON Schema для принуждения модели к структурированному ответу"
    )
    max_tokens: Optional[int] = Field(
        1000, 
        description="Максимальное количество токенов в ответе"
    )
    temperature: Optional[float] = Field(
        0.7, 
        description="Температура генерации (0.0 - детерминированно, 1.0 - креативно)"
    )


class LLMChatResponse(BaseModel):
    """
    Схема ответа от LLM
    Зачем: Стандартизируем формат ответов для UI
    """
    success: bool = Field(description="Успешность запроса")
    model: str = Field(description="Использованная модель")
    response: str = Field(description="Текст ответа от LLM")
    raw_response: Optional[str] = Field(None, description="Сырой ответ от Ollama (для отладки)")
    error: Optional[str] = Field(None, description="Описание ошибки, если success=False")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов")


class LLMModelsResponse(BaseModel):
    """
    Схема ответа со списком доступных моделей
    Зачем: UI может показать пользователю доступные модели
    """
    success: bool
    models: list[dict]  # Список объектов с информацией о моделях
    error: Optional[str] = None


class AllowedModelsResponse(BaseModel):
    """
    Схема ответа со списком разрешенных моделей для скачивания
    Зачем: UI может показать пользователю, какие модели можно скачать
    """
    success: bool
    allowed: list[dict]  # Список объектов с тегом и меткой
    error: Optional[str] = None


class PullModelRequest(BaseModel):
    """
    Схема запроса для скачивания модели
    Зачем: Валидируем входные данные для скачивания
    """
    tag: str = Field(..., description="Тег модели для скачивания (например: llama3.1:8b)")


class PullModelResponse(BaseModel):
    """
    Схема ответа при скачивании модели
    Зачем: Информируем пользователя о результате скачивания
    """
    success: bool
    message: str
    error: Optional[str] = None


async def check_ollama_connection() -> bool:
    """
    Проверяет подключение к Ollama серверу
    Зачем: Валидируем, что Ollama запущен перед отправкой запросов
    
    Returns:
        bool: True если Ollama доступен, False иначе
    """
    # Логируем адрес Ollama для отладки
    logger.debug(f"Проверяем подключение к Ollama: {OLLAMA_BASE_URL}")
    
    try:
        async with httpx.AsyncClient(timeout=CONNECT_TIMEOUT) as client:
            response = await client.get(OLLAMA_TAGS_ENDPOINT)
            if response.status_code == 200:
                logger.info(f"Ollama доступен: {OLLAMA_BASE_URL}")
                return True
            else:
                logger.warning(f"Ollama недоступен: HTTP {response.status_code} для {OLLAMA_BASE_URL}")
                return False
    except Exception as e:
        logger.error(f"Ошибка подключения к Ollama {OLLAMA_BASE_URL}: {str(e)}")
        return False


@retry(
    stop=stop_after_attempt(3),  # Максимум 3 попытки
    wait=wait_exponential(multiplier=1, min=1, max=10),  # Экспоненциальная задержка
    reraise=True
)
async def generate_with_ollama(request: LLMChatRequest) -> Dict[str, Any]:
    """
    Отправляет запрос к Ollama API с retry логикой
    Зачем: Обрабатываем временные сбои сети и перегрузку Ollama
    
    Args:
        request: Запрос к LLM
        
    Returns:
        Dict с ответом от Ollama
        
    Raises:
        HTTPException: При критических ошибках
    """
    # Формируем промпт с JSON Schema если нужно
    # Зачем: Принуждаем модель к структурированному ответу
    full_prompt = request.prompt
    needs_json = bool(request.json_schema)
    
    if needs_json:
        schema_txt = json.dumps(request.json_schema, ensure_ascii=False)
        json_rules = (
            "You MUST return ONLY valid JSON that STRICTLY follows the JSON Schema below. "
            "No prose. No markdown. No code fences. Unknown fields → null. "
            "If a required field cannot be inferred, set it to null and add a short note in 'assumptions' if such field exists.\n\n"
            "=== JSON SCHEMA START ===\n"
            f"{schema_txt}\n"
            "=== JSON SCHEMA END ===\n\n"
        )
        full_prompt = json_rules + request.prompt

    # Подготавливаем данные для Ollama API
    # Зачем: Ollama ожидает определенный формат запроса
    ollama_payload = {
        "model": request.model,
        "prompt": full_prompt,
        "stream": False,  # Не стримим, получаем полный ответ
        "options": {
            "temperature": request.temperature,
            "num_predict": request.max_tokens,
        }
    }
    
    # Включаем JSON режим и понижаем температуру для структурированных ответов
    if needs_json:
        ollama_payload["format"] = "json"  # просим строго JSON на уровне Ollama
        ollama_payload["options"]["temperature"] = 0.2
    
    # Добавляем системный промпт если есть
    # Зачем: Системный промпт настраивает поведение модели
    if request.system:
        ollama_payload["system"] = request.system

    logger.info(f"Отправляем запрос к Ollama: {request.model}")
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                OLLAMA_GENERATE_ENDPOINT,
                json=ollama_payload
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.TimeoutException:
        logger.error(f"Таймаут запроса к Ollama: {request.model}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Ollama не ответил в течение {REQUEST_TIMEOUT} секунд"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP ошибка от Ollama: {e.response.status_code}")
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Модель '{request.model}' не найдена. Проверьте: ollama list"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ошибка Ollama: {e.response.status_code}"
            )
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к Ollama: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка: {str(e)}"
        )


def _json_recover(s: str) -> dict | None:
    """
    Мягкое восстановление JSON из текста
    Зачем: Пытаемся извлечь валидный JSON даже если модель добавила мусор
    """
    try:
        return json.loads(s)
    except Exception:
        # попробуем вырезать от первого '{' до последней '}'
        i, j = s.find("{"), s.rfind("}")
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(s[i:j+1])
            except Exception:
                return None
        return None


def validate_json_response(response_text: str, json_schema: Optional[Dict] = None) -> str:
    """
    Валидирует и исправляет JSON ответ от LLM
    Зачем: LLM иногда возвращают невалидный JSON, пытаемся исправить
    
    Args:
        response_text: Текст ответа от LLM
        json_schema: Ожидаемая схема (пока не используется)
        
    Returns:
        str: Валидный JSON или исходный текст
    """
    # Пытаемся найти JSON в ответе
    # Зачем: LLM могут добавлять пояснения до/после JSON
    import re
    
    # Ищем JSON блоки в тексте
    json_pattern = r'\{.*\}'
    json_matches = re.findall(json_pattern, response_text, re.DOTALL)
    
    if json_matches:
        # Берем самый длинный JSON блок (вероятно основной)
        json_candidate = max(json_matches, key=len)
        
        # Используем мягкое восстановление
        parsed = _json_recover(json_candidate)
        if parsed is not None:
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        else:
            # Если не получилось, возвращаем исходный текст
            logger.warning("Не удалось распарсить JSON от LLM")
            return response_text
    
    return response_text


@router.post("/chat", response_model=LLMChatResponse)
async def chat_with_llm(request: LLMChatRequest) -> LLMChatResponse:
    """
    Основной endpoint для общения с LLM
    Зачем: Единая точка входа для всех запросов к локальным LLM
    
    Args:
        request: Запрос с промптом и настройками
        
    Returns:
        LLMChatResponse: Структурированный ответ от LLM
    """
    logger.info(f"Получен запрос к LLM: {request.model}")
    
    # Проверяем подключение к Ollama
    # Зачем: Быстро сообщаем пользователю, если Ollama не запущен
    if not await check_ollama_connection():
        return LLMChatResponse(
            success=False,
            model=request.model,
            response="",
            error="Ollama сервер недоступен. Запустите: ollama serve",
            raw_response=None
        )
    
    try:
        # Отправляем запрос к Ollama
        ollama_response = await generate_with_ollama(request)
        
        # Извлекаем ответ из формата Ollama
        # Зачем: Ollama возвращает ответ в поле 'response'
        response_text = ollama_response.get("response", "")
        
        # Валидируем JSON если нужен структурированный ответ
        if request.json_schema:
            # Пытаемся распарсить JSON
            parsed = _json_recover(response_text)
            
            if parsed is None:
                # Первая попытка не удалась, делаем retry с уточнением
                logger.warning("Первая попытка не дала валидный JSON, делаем retry")
                
                # Создаем новый запрос с уточнением
                retry_request = request.model_copy()
                retry_request.prompt = (
                    "Your previous output was NOT valid JSON. "
                    "Return ONLY valid JSON with no extra characters. "
                    "Follow the schema exactly.\n\n"
                ) + request.prompt
                
                # Повторный запрос
                ollama_response = await generate_with_ollama(retry_request)
                response_text = ollama_response.get("response", "")
                
                # Проверяем еще раз
                parsed = _json_recover(response_text)
                
                if parsed is None:
                    # Окончательный фейл
                    raise HTTPException(
                        status_code=422, 
                        detail={
                            "code": "invalid_json",
                            "message": "Model failed to produce valid JSON after 2 attempts.",
                            "raw_text": response_text[:4000]  # на всякий случай ограничим
                        }
                    )
            
            # Успешно распарсили, форматируем
            response_text = json.dumps(parsed, ensure_ascii=False, indent=2)
        
        # Подсчитываем токены (приблизительно)
        # Зачем: Показываем пользователю, сколько токенов использовано
        tokens_used = ollama_response.get("eval_count", 0)
        
        return LLMChatResponse(
            success=True,
            model=request.model,
            response=response_text,
            raw_response=json.dumps(ollama_response, ensure_ascii=False, indent=2),
            tokens_used=tokens_used
        )
        
    except HTTPException:
        # Перебрасываем HTTP исключения как есть
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка в chat_with_llm: {e}")
        return LLMChatResponse(
            success=False,
            model=request.model,
            response="",
            error=f"Внутренняя ошибка: {str(e)}"
        )


@router.get("/models", response_model=LLMModelsResponse)
async def get_available_models() -> LLMModelsResponse:
    """
    Возвращает список доступных моделей Ollama
    Зачем: UI может показать пользователю, какие модели доступны
    
    Returns:
        LLMModelsResponse: Список моделей или ошибка
    """
    try:
        # Проверяем подключение к Ollama
        if not await check_ollama_connection():
            return LLMModelsResponse(
                success=False,
                models=[],
                error="Ollama сервер недоступен. Запустите: ollama serve"
            )
        
        # Запрашиваем список моделей
        async with httpx.AsyncClient(timeout=CONNECT_TIMEOUT) as client:
            response = await client.get(OLLAMA_TAGS_ENDPOINT)
            response.raise_for_status()
            data = response.json()
            
            # Возвращаем полную информацию о моделях
            # Зачем: UI может показать размер, семейство и другие детали
            models = data.get("models", [])
            
            return LLMModelsResponse(
                success=True,
                models=models
            )
            
    except Exception as e:
        logger.error(f"Ошибка при получении списка моделей: {e}")
        return LLMModelsResponse(
            success=False,
            models=[],
            error=f"Ошибка: {str(e)}"
        )


@router.get("/allowed_models", response_model=AllowedModelsResponse)
async def get_allowed_models() -> AllowedModelsResponse:
    """
    Возвращает список разрешенных моделей для скачивания
    Зачем: UI может показать пользователю, какие модели можно скачать
    
    Returns:
        AllowedModelsResponse: Список разрешенных моделей
    """
    try:
        # Whitelist разрешенных моделей
        # Зачем: Ограничиваем скачивание только проверенными моделями
        allowed_models = [
            {"tag": "llama3.1:8b", "label": "Llama 3.1 8B (4.1GB) - Общий анализ"},
            {"tag": "llama3.1:70b", "label": "Llama 3.1 70B (40GB) - Продвинутый анализ"},
            {"tag": "gemma2:9b", "label": "Gemma 2 9B (5.4GB) - Быстрые ответы"},
            {"tag": "gemma2:27b", "label": "Gemma 2 27B (16GB) - Качественные ответы"},
            {"tag": "qwen2.5-coder:7b", "label": "Qwen2.5-Coder 7B (4.4GB) - Код-генерация"},
            {"tag": "qwen2.5:7b", "label": "Qwen2.5 7B (4.4GB) - Универсальная модель"},
            {"tag": "qwen2.5:14b", "label": "Qwen2.5 14B (8.1GB) - Улучшенная модель"},
            {"tag": "mistral:7b", "label": "Mistral 7B (4.1GB) - Эффективная модель"},
            {"tag": "codellama:7b", "label": "CodeLlama 7B (3.8GB) - Специализация на коде"},
        ]
        
        return AllowedModelsResponse(
            success=True,
            allowed=allowed_models
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка разрешенных моделей: {e}")
        return AllowedModelsResponse(
            success=False,
            allowed=[],
            error=f"Ошибка: {str(e)}"
        )


@router.post("/pull", response_model=PullModelResponse)
async def pull_model(request: PullModelRequest) -> PullModelResponse:
    """
    Скачивает модель через Ollama
    Зачем: Позволяет пользователю скачивать новые модели
    
    Args:
        request: Запрос с тегом модели
        
    Returns:
        PullModelResponse: Результат скачивания
    """
    try:
        # Проверяем подключение к Ollama
        if not await check_ollama_connection():
            return PullModelResponse(
                success=False,
                message="Ollama сервер недоступен",
                error="Запустите: ollama serve"
            )
        
        # Проверяем, что модель в whitelist
        # Зачем: Безопасность - скачиваем только разрешенные модели
        allowed_response = await get_allowed_models()
        if not allowed_response.success:
            return PullModelResponse(
                success=False,
                message="Не удалось получить список разрешенных моделей",
                error=allowed_response.error
            )
        
        allowed_tags = [model["tag"] for model in allowed_response.allowed]
        if request.tag not in allowed_tags:
            return PullModelResponse(
                success=False,
                message=f"Модель {request.tag} не разрешена для скачивания",
                error="Модель не в whitelist"
            )
        
        # Отправляем запрос на скачивание в Ollama
        # Зачем: Используем Ollama API для скачивания модели
        pull_payload = {
            "name": request.tag
        }
        
        async with httpx.AsyncClient(timeout=1800) as client:  # 30 минут на скачивание
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/pull",
                json=pull_payload
            )
            response.raise_for_status()
            
            # Ollama возвращает stream, но мы ждем завершения
            # Зачем: Убеждаемся, что модель полностью скачана
            logger.info(f"Модель {request.tag} успешно скачана")
            
            return PullModelResponse(
                success=True,
                message=f"Модель {request.tag} успешно скачана и установлена"
            )
            
    except httpx.TimeoutException:
        logger.error(f"Таймаут при скачивании модели {request.tag}")
        return PullModelResponse(
            success=False,
            message=f"Таймаут при скачивании модели {request.tag}",
            error="Скачивание заняло слишком много времени"
        )
    except Exception as e:
        logger.error(f"Ошибка при скачивании модели {request.tag}: {e}")
        return PullModelResponse(
            success=False,
            message=f"Ошибка при скачивании модели {request.tag}",
            error=str(e)
        )


@router.get("/schemas/portfolio_v1")
async def get_portfolio_schema_v1_endpoint() -> Dict[str, Any]:
    """
    Возвращает JSON Schema для анализа портфеля v1
    Зачем: Централизуем схему для UI
    
    Returns:
        Dict[str, Any]: JSON Schema для валидации ответа LLM
    """
    return get_portfolio_schema_v1()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Проверка здоровья LLM сервиса
    Зачем: Мониторинг и отладка состояния Ollama
    
    Returns:
        Dict с информацией о состоянии сервиса
    """
    ollama_available = await check_ollama_connection()
    
    return {
        "status": "healthy" if ollama_available else "unhealthy",
        "ollama_available": ollama_available,
        "ollama_url": OLLAMA_BASE_URL,
        "message": "LLM сервис работает" if ollama_available else "Ollama недоступен"
    }

