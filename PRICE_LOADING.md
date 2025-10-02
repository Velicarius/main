# Автоматическая загрузка цен

## Обзор

Система автоматически загружает цены для новых позиций из Stooq API. При добавлении новой позиции система проверяет, есть ли уже данные о ценах для этого символа, и если нет - автоматически загружает их.

## Как это работает

1. **Добавление позиции**: При создании новой позиции через API (`POST /positions`)
2. **Проверка существующих данных**: Система проверяет, есть ли уже цены для символа в таблице `prices_eod`
3. **Автоматическая загрузка**: Если данных нет, система загружает их из Stooq API
4. **Сохранение в БД**: Загруженные данные сохраняются в таблицу `prices_eod`

## Поддерживаемые символы

- **Американские акции**: Автоматически добавляется суффикс `.US` (например, `AAPL` → `AAPL.US`)
- **Другие рынки**: Поддерживаются суффиксы `.PL`, `.DE`, `.JP`, `.UK`, `.FR`, `.CN`, `.HK`, `.IN`, `.CA`
- **USD**: Пропускается (всегда равен 1.0)

## Архитектура

### Основные компоненты

1. **`app.services.price_service.PriceService`** - Основной сервис для загрузки цен
2. **`app.marketdata.stooq_client`** - Клиент для работы с Stooq API
3. **`app.services.price_eod.PriceEODRepository`** - Репозиторий для работы с БД
4. **`app.services.auto_price_loader`** - DEPRECATED: используйте `price_service`

### Поток данных

```
Позиция → PriceService → StooqClient → Stooq API → DataFrame → PriceEODRepository → БД
```

## API Endpoints

### Создание позиции с автозагрузкой
```bash
curl -X POST "http://localhost:8001/positions" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "quantity": 10, "buy_price": 150.0}'
```

### Ручная загрузка цен
```bash
# Загрузить цену для конкретного символа
curl -X POST "http://localhost:8001/admin/eod/aapl/refresh-sync" \
  -H "X-Admin-Token: admin123"

# Загрузить цены для всех позиций
curl -X POST "http://localhost:8001/admin/eod/refresh-sync-all" \
  -H "X-Admin-Token: admin123"
```

### Проверка загруженных символов
```bash
curl "http://localhost:8001/prices-eod/symbols"
```

### Проверка конкретной цены
```bash
curl "http://localhost:8001/prices-eod/AAPL/latest"
```

### Health check для Stooq
```bash
curl "http://localhost:8001/health/stooq"
```

## Мониторинг и логирование

### Структурированные логи

Система использует структурированное логирование с ключевыми событиями:

- `price_service_start` - Начало загрузки цены
- `price_service_success` - Успешная загрузка
- `stooq_request` - Запрос к Stooq API
- `stooq_response` - Ответ от Stooq API
- `stooq_dataframe_parsed` - Успешный парсинг DataFrame
- `stooq_no_data` - Нет данных от Stooq
- `stooq_csv_parse_error` - Ошибка парсинга CSV

### Просмотр логов

```bash
# Просмотр логов API
docker-compose logs -f api | grep -i "price\|stooq"

# Просмотр логов воркера
docker-compose logs -f worker | grep -i "price\|stooq"
```

## Тестирование

### Автоматический тест
```bash
# Запуск теста в контейнере
docker-compose exec api python test_auto_price.py

# Запуск bash-скрипта тестирования
./test_api.sh
```

### Ручное тестирование
```bash
# 1. Создать позицию
curl -X POST "http://localhost:8001/positions" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "MSFT", "quantity": 5, "buy_price": 300.0}'

# 2. Проверить загруженные символы
curl "http://localhost:8001/prices-eod/symbols"

# 3. Проверить цену
curl "http://localhost:8001/prices-eod/MSFT/latest"
```

## Частые проблемы и решения

### 1. "No data" от Stooq
**Проблема**: Stooq возвращает "No data" для символа
**Решение**: 
- Проверьте правильность символа
- Убедитесь, что символ торгуется на поддерживаемых биржах
- Попробуйте альтернативные суффиксы

### 2. Ошибка парсинга CSV
**Проблема**: `stooq_csv_parse_error` в логах
**Решение**:
- Проверьте доступность Stooq API
- Убедитесь, что символ существует
- Проверьте логи для подробной информации

### 3. Автозагрузка не работает
**Проблема**: Цены не загружаются автоматически
**Решение**:
- Проверьте логи на ошибки
- Убедитесь, что используется новый `price_service`
- Проверьте health endpoint: `curl "http://localhost:8001/health/stooq"`

### 4. Символы сохраняются в нижнем регистре
**Проблема**: В БД символы сохраняются как "aapl" вместо "AAPL"
**Решение**: Исправлено в `PriceEODRepository._normalize_symbol()` - теперь сохраняет в верхнем регистре

## Конфигурация

### Переменные окружения
- `STOOQ_TIMEOUT` - Таймаут для запросов к Stooq (по умолчанию 10 секунд)
- `ADMIN_TOKEN` - Токен для админских endpoints (по умолчанию "admin123")

### Настройки логирования
Логирование настраивается через стандартные настройки Python logging.

## Разработка

### Добавление нового источника данных
1. Создайте новый клиент в `app.marketdata`
2. Обновите `PriceService` для поддержки нового источника
3. Добавьте тесты

### Отладка
1. Включите DEBUG логирование
2. Используйте структурированные логи для трассировки
3. Проверяйте health endpoints

## Миграция с старой системы

Старая система `app.quotes.stooq` помечена как DEPRECATED и автоматически перенаправляет на новый клиент `app.marketdata.stooq_client`. 

Для новых разработок используйте:
```python
from app.services.price_service import PriceService
from app.marketdata.stooq_client import fetch_latest_from_stooq
```

## Поддержка

При возникновении проблем:
1. Проверьте логи системы
2. Используйте health endpoints для диагностики
3. Запустите тесты для проверки функциональности
4. Обратитесь к разработчикам с подробными логами
