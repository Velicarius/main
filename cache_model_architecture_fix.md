# Исправление архитектуры кэша и моделей на странице Insights

## Проблемы

### 1. Дублирующие API endpoints
- `/ai/insights-swr` - SWR API  
- `/ai/insights` - Unified API
- `/insights/optimized` - Optimized API
- `/insights/v2` - Legacy V2 API

### 2. Несогласованные кэш-сервисы
- `InsightsCacheService` базовый Redis кэш
- `UnifiedCacheService` с SWR и fingerprinting

### 3. Фронтенд смешивает API
```typescript
// В Insights.tsx использует:
swrInsightsAPI.getInsights()

// В UnifiedInsights.tsx использует:  
optimizedInsightsAPI.getOptimizedInsights()
```

### 4. LLM обращения разбросаны по сервисам
- `ai_portfolio.py` - базовые запросы
- `insights_enrich_llm.py` - обогащение 
- `ai_insights_unified.py` - SWR генерация

## Архитектурное решение

### Унификация API
```
Единый endpoint: POST /ai/insights/unified

Параметры:
- cache_mode: 'default' | 'bypass' | 'refresh'
- horizon_months, risk_profile, model, etc.

Ответ:
{
  "cached": boolean,
  "cache_key": string,
  "model_name": string,
  "llm_ms": number,
  "data": InsightsData,
  "headers": {
    "ETag": string,
    "X-Cache": "HIT|MISS|STALE",
    "X-Cache-Age": number
  }
}
```

### Унифицированный сервис
```python
class UnifiedInsightsService:
    async def get_insights(
        self,
        user_id: UUID,
        request: UnifiedInsightsRequest,
        cache_mode: str = "default"
    ) -> UnifiedInsightsResponse:
        # 1. Check SWR cache
        # 2. Generate if miss/stale  
        # 3. Schedule background refresh
        # 4. Return with full metadata
```

### Единый фронтенд API
```typescript
class InsightsAPI {
  async getInsights(params: InsightsRequest): Promise<InsightsResponse> {
    // Single API call for everything
  }
  
  async refreshInsights(params: InsightsRequest): Promise<InsightsResponse> {
    // Force refresh endpoint
  }
}
```

### Оптимизированная страница
```typescript
// Единая логика без дублирования
const useInsights = (params: InsightsRequest) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cacheInfo, setCacheInfo] = useState(null);
  
  const fetchInsights = async () => {
    const response = await insightsAPI.getInsights(params);
    setData(response.data);
    setCacheInfo(response.headers);
  };
  
  const refreshInsights = async () => {
    const response = await insightsAPI.refreshInsights(params);
    setData(response.data);
    setCacheInfo(response.headers);
  };
  
  return { data, loading, cacheInfo, fetchInsights, refreshInsights };
};
```

## План реализации

### Шаг 1: Унификация бэкенда
1. Создать единый `UnifiedInsightsService`
2. Собрать все LLM логики в один сервис
3. Реализовать единый кэш с SWR

### Шаг 2: Очистка фронтенда  
1. Создать единый `InsightsAPI` клиент
2. Упростить логику в `Insights.tsx`
3. Убрать дублирование в компонентах

### Шаг 3: Мониторинг и оптимизация
1. Добавить метрики кэша
2. Реализовать background refresh
3. Тестирование производительности

## Результат

✅ Один API endpoint вместо 4
✅ Единый кэш-сервис с SWR  
✅ Простая логика во фронтенде
✅ Прозрачные метрики производительности
✅ Надежное кэширование LLM ответов







