#!/bin/bash

# Тест API для автоматической загрузки цен

echo "=== Тест API автоматической загрузки цен ==="

# Базовый URL API
API_URL="http://localhost:8001"

# Функция для проверки статуса
check_status() {
    if [ $1 -eq 0 ]; then
        echo "✅ $2"
    else
        echo "❌ $2"
    fi
}

# 1. Проверяем health endpoint
echo "1. Проверяем health endpoint..."
curl -s "$API_URL/health" > /dev/null
check_status $? "Health endpoint"

# 2. Проверяем Stooq health
echo "2. Проверяем Stooq health..."
curl -s "$API_URL/health/stooq" | jq .
check_status $? "Stooq health check"

# 3. Создаем новую позицию
echo "3. Создаем новую позицию AAPL..."
POSITION_RESPONSE=$(curl -s -X POST "$API_URL/positions" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "quantity": 10, "buy_price": 150.0}')

echo "Ответ создания позиции: $POSITION_RESPONSE"
check_status $? "Создание позиции"

# 4. Ждем 5 секунд
echo "4. Ждем 5 секунд для автозагрузки..."
sleep 5

# 5. Проверяем загруженные символы
echo "5. Проверяем загруженные символы..."
SYMBOLS_RESPONSE=$(curl -s "$API_URL/prices-eod/symbols")
echo "Символы в БД: $SYMBOLS_RESPONSE"

if echo "$SYMBOLS_RESPONSE" | grep -q "AAPL"; then
    echo "✅ AAPL найден в БД"
else
    echo "❌ AAPL не найден в БД"
    
    # 6. Пытаемся загрузить вручную через админский endpoint
    echo "6. Пытаемся загрузить вручную через админский endpoint..."
    ADMIN_RESPONSE=$(curl -s -X POST "$API_URL/admin/eod/aapl/refresh-sync" \
      -H "X-Admin-Token: admin123")
    echo "Ответ админского endpoint: $ADMIN_RESPONSE"
    check_status $? "Ручная загрузка через админ"
    
    # 7. Проверяем снова
    echo "7. Проверяем снова после ручной загрузки..."
    sleep 2
    SYMBOLS_RESPONSE=$(curl -s "$API_URL/prices-eod/symbols")
    echo "Символы в БД после ручной загрузки: $SYMBOLS_RESPONSE"
fi

# 8. Проверяем цену AAPL
echo "8. Проверяем цену AAPL..."
AAPL_PRICE=$(curl -s "$API_URL/prices-eod/AAPL/latest")
echo "Цена AAPL: $AAPL_PRICE"

if echo "$AAPL_PRICE" | grep -q "close"; then
    echo "✅ Цена AAPL загружена"
else
    echo "❌ Цена AAPL не загружена"
fi

echo "=== Тест завершен ==="
