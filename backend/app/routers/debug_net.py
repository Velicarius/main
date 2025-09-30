"""
Диагностический роутер для сетевых подключений
Зачем: Отладка проблем с подключением к Ollama из Docker контейнера

ВНИМАНИЕ: Этот роутер предназначен только для разработки и отладки.
В продакшене его следует отключить или защитить аутентификацией.
"""

import socket
import logging
from typing import Dict, Any
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter
from app.config import get_ollama_config

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер
# Зачем: Группируем диагностические endpoints
router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/connect")
async def debug_connect() -> Dict[str, Any]:
    """
    Диагностика подключения к Ollama
    Зачем: Пошаговая проверка DNS, TCP и HTTP подключений
    
    Returns:
        JSON с результатами диагностики:
        - ollama_url: URL для подключения
        - dns: результат DNS резолва
        - tcp_ok: успешность TCP подключения
        - http_ok: успешность HTTP запроса
        - error: последняя ошибка
    """
    # Получаем конфигурацию Ollama
    ollama_config = get_ollama_config()
    ollama_url = ollama_config["url"]
    
    result = {
        "ollama_url": ollama_url,
        "dns": {"host": "", "ip": ""},
        "tcp_ok": False,
        "http_ok": False,
        "error": None
    }
    
    try:
        # Парсим URL для получения хоста и порта
        parsed_url = urlparse(ollama_url)
        host = parsed_url.hostname
        port = parsed_url.port or 11434  # По умолчанию порт Ollama
        
        result["dns"]["host"] = host
        
        # 1. DNS резолв
        try:
            ip = socket.gethostbyname(host)
            result["dns"]["ip"] = ip
            logger.info(f"DNS резолв успешен: {host} -> {ip}")
        except socket.gaierror as e:
            result["error"] = f"DNS резолв не удался: {str(e)}"
            logger.error(f"DNS резолв не удался для {host}: {str(e)}")
            return result
        
        # 2. TCP подключение
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # Таймаут 3 секунды
            result_tcp = sock.connect_ex((ip, port))
            sock.close()
            
            if result_tcp == 0:
                result["tcp_ok"] = True
                logger.info(f"TCP подключение успешно: {ip}:{port}")
            else:
                result["error"] = f"TCP подключение не удалось: код {result_tcp}"
                logger.error(f"TCP подключение не удалось к {ip}:{port}, код: {result_tcp}")
                return result
                
        except Exception as e:
            result["error"] = f"Ошибка TCP подключения: {str(e)}"
            logger.error(f"Ошибка TCP подключения к {ip}:{port}: {str(e)}")
            return result
        
        # 3. HTTP запрос
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{ollama_url}/api/version")
                if response.status_code == 200:
                    result["http_ok"] = True
                    logger.info(f"HTTP запрос успешен: {ollama_url}/api/version")
                else:
                    result["error"] = f"HTTP запрос не удался: статус {response.status_code}"
                    logger.error(f"HTTP запрос не удался: {ollama_url}/api/version, статус: {response.status_code}")
        except Exception as e:
            result["error"] = f"Ошибка HTTP запроса: {str(e)}"
            logger.error(f"Ошибка HTTP запроса к {ollama_url}/api/version: {str(e)}")
    
    except Exception as e:
        result["error"] = f"Общая ошибка диагностики: {str(e)}"
        logger.error(f"Общая ошибка диагностики: {str(e)}")
    
    return result


@router.get("/ping")
async def debug_ping() -> Dict[str, str]:
    """
    Простая проверка доступности роутера
    Зачем: Быстрая проверка, что диагностический роутер работает
    """
    return {"status": "ok", "message": "Debug router доступен"}
