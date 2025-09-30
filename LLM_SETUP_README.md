# 🚀 Быстрый старт: Локальные LLM для AI Portfolio Analyzer

## Что мы создали

Полная интеграция локальных LLM (Llama, Gemma, Qwen) через Ollama для тестирования в AI Portfolio Analyzer.

### 📁 Структура файлов

```
infra/ollama/
├── README.md          # Подробная документация по Ollama
├── install.ps1        # Автоматическая установка Ollama
└── pull_models.ps1    # Скачивание моделей LLM

backend/app/routers/
└── llm_proxy.py       # FastAPI роутер для Ollama API

backend/app/web/ui/
└── llm_test.html      # Веб-интерфейс для тестирования LLM

backend/app/main.py    # Обновлен с новым роутером
backend/requirements.txt # Добавлена зависимость tenacity
```

## 🎯 Быстрый запуск

### 1. Установите Ollama
```powershell
cd infra/ollama
.\install.ps1
```

### 2. Скачайте модели LLM
```powershell
.\pull_models.ps1
```

### 3. Запустите Ollama сервер
```bash
ollama serve
```

### 4. Запустите FastAPI
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Откройте тестовый интерфейс
```
http://localhost:8000/ui/llm_test.html
```

## 🔧 API Endpoints

### POST `/llm/chat`
Отправка запроса к LLM:
```json
{
  "model": "llama3.1:8b",
  "system": "Ты эксперт по анализу портфелей",
  "prompt": "Проанализируй мой портфель: 60% акции, 30% облигации",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### GET `/llm/models`
Получить список доступных моделей

### GET `/llm/health`
Проверка состояния Ollama

## 🧪 Тестирование

1. **Откройте** `http://localhost:8000/ui/llm_test.html`
2. **Выберите модель** (llama3.1:8b, gemma2:9b, qwen2.5-coder:7b)
3. **Введите промпт** для анализа портфеля
4. **Нажмите "Отправить запрос"**
5. **Получите JSON ответ** от LLM

## 💡 Примеры промптов

### Анализ портфеля
```
Проанализируй мой портфель: 60% акции (AAPL, MSFT, GOOGL), 30% облигации (BND), 10% золото (GLD). 
Какие риски и возможности? Дай рекомендации по оптимизации.
```

### Генерация SQL
```
Сгенерируй SQL запрос для расчета доходности портфеля за последние 30 дней. 
Таблица: portfolio_valuations_eod с полями date, portfolio_id, total_value.
```

### Анализ рисков
```
Оцени риски моего портфеля: 70% акции технологических компаний, 20% криптовалюты, 10% наличные.
Какие сценарии могут привести к потере 20%+ стоимости?
```

## 🐛 Troubleshooting

### Ollama не запускается
```bash
# Проверьте порт 11434
netstat -an | findstr 11434

# Перезапустите Ollama
ollama serve
```

### Модель не отвечает
```bash
# Проверьте список моделей
ollama list

# Перескачайте модель
ollama pull llama3.1:8b
```

### Медленные ответы
- Используйте квантованные модели (q4_0)
- Закройте другие приложения
- Рассмотрите vLLM для продакшена

## 📊 Сравнение моделей

| Модель | Размер | Скорость | Качество | Назначение |
|--------|--------|----------|----------|------------|
| llama3.1:8b | 4.1GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | Общий анализ |
| gemma2:9b | 5.4GB | ⭐⭐⭐⭐ | ⭐⭐⭐ | Быстрые ответы |
| qwen2.5-coder:7b | 4.4GB | ⭐⭐⭐ | ⭐⭐⭐⭐ | Код-генерация |

## 🔄 Следующие шаги

1. **Интеграция с портфелем**: Подключить LLM к реальным данным портфеля
2. **Кэширование**: Сохранять ответы LLM для повторных запросов
3. **Векторный поиск**: Использовать embeddings для контекстного поиска
4. **vLLM**: Переход на vLLM для продакшена с высокой нагрузкой

## 📚 Дополнительные ресурсы

- [Ollama Documentation](https://ollama.ai/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Tenacity Retry Library](https://tenacity.readthedocs.io/)

