# AI Portfolio - Zero-Build Static UI

## Описание

Минималистичный статический UI для тестирования AI Portfolio backend без необходимости сборки или npm.

## Файлы

- `backend/app/web/ui/index.html` - Основная HTML страница
- `backend/app/web/ui/app.js` - JavaScript логика
- `backend/app/web/ui/styles.css` - Стили (поддержка темной/светлой темы)
- `backend/app/main.py` - Обновлен для обслуживания статических файлов

## Функциональность

- **Позиции**: Загрузка и отображение всех позиций из `/positions`
- **Цены**: Получение последних цен EOD из `/prices-eod/{symbol}/latest`
- **Расчеты**: Автоматический расчет Value (qty × last) и PnL ((last - buy_price) × qty)
- **Фильтрация**: Поиск по символу или аккаунту
- **EOD триггер**: Ручной запуск задачи получения данных через `/admin/tasks/fetch-eod`
- **Тоталы**: Общая стоимость портфеля и общий PnL

## Запуск

```bash
# Запуск backend как обычно
uvicorn app.main:app --reload --port 8001

# Открыть в браузере
http://localhost:8001/ui
```

## Особенности

- ✅ Zero-build: никаких npm, webpack, vite
- ✅ Работает за reverse proxy
- ✅ Поддержка темной/светлой темы
- ✅ Graceful error handling
- ✅ Обработка символов без цен (показывает —)
- ✅ Адаптивный дизайн
- ✅ Кнопки блокируются во время запросов

## API Endpoints

- `GET /positions` → массив позиций
- `GET /prices-eod/{symbol}/latest` → последняя цена (404 если нет данных)
- `POST /admin/tasks/fetch-eod` → запуск EOD задачи

