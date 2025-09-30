"""
Конфигурация для AI Portfolio Analyzer
Зачем: Централизованная настройка всех параметров приложения
"""

import os
from typing import Optional

# Конфигурация Ollama
# Зачем: Настраиваемый URL для подключения к Ollama
# Почему не localhost: В Docker контейнере localhost указывает на сам контейнер, а не на хост
# host.docker.internal: Специальный DNS-адрес Docker для доступа к хосту из контейнера
# Как переопределить: Установить переменную окружения OLLAMA_URL
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")

# Альтернативные варианты для разных окружений:
# - Локальная разработка: "http://localhost:11434"
# - Docker с проброшенным портом: "http://localhost:11434"
# - Kubernetes: "http://ollama-service:11434"

def get_ollama_url() -> str:
    """
    Получить URL для подключения к Ollama
    Зачем: Единая точка получения конфигурации Ollama
    """
    return OLLAMA_URL

def get_ollama_config() -> dict:
    """
    Получить полную конфигурацию Ollama
    Зачем: Расширяемость для будущих настроек (таймауты, retry, etc.)
    """
    return {
        "url": OLLAMA_URL,
        "timeout": 300,  # 5 минут на генерацию
        "connect_timeout": 10,  # 10 секунд на подключение
    }
