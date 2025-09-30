// Утилиты для работы с X-Trace-Id
// Зачем: Обеспечиваем отслеживание запросов для отладки и мониторинга

/**
 * Получает или создает Trace ID для текущей сессии
 * Зачем: Стабильный идентификатор для отслеживания запросов в пределах вкладки браузера
 */
export function getOrCreateTraceId(): string {
  const stored = localStorage.getItem('trace_id');
  if (stored) {
    return stored;
  }
  
  // Генерируем новый Trace ID
  // Зачем: Уникальный идентификатор для отслеживания запросов
  const newTraceId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  localStorage.setItem('trace_id', newTraceId);
  return newTraceId;
}

/**
 * Создает заголовки с X-Trace-Id для fetch запросов
 * Зачем: Упрощает добавление Trace ID во все API запросы
 */
export function createTraceHeaders(): Record<string, string> {
  return {
    'X-Trace-Id': getOrCreateTraceId()
  };
}
