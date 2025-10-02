/**
 * Универсальные утилиты для безопасного форматирования чисел
 * Защищает от падений при null/undefined/NaN значениях
 */

// =============================================================================
// Основные функции форматирования
// =============================================================================

/**
 * Безопасное форматирование числа с заданным количеством знаков после запятой
 * @param value - значение для форматирования (может быть null/undefined/NaN)
 * @param digits - количество знаков после запятой (по умолчанию 2)
 * @param fallback - возвращаемое значение при невалидном числе (по умолчанию '—')
 * @returns отформатированное число в виде строки или fallback
 */
export function fmtNum(
  value: any, 
  digits: number = 2, 
  fallback: string = '—'
): string {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  
  const num = Number(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return fallback;
  }
  
  return num.toFixed(digits);
}

/**
 * Безопасное форматирование числа с процентами
 * @param value - значение для форматирования (может быть null/undefined/NaN)
 * @param digits - количество знаков после запятой (по умолчанию 1)
 * @param fallback - возвращаемое значение при невалидном числе (по умолчанию '—')
 * @returns строка с символом % или fallback
 */
export function fmtPct(
  value: any, 
  digits: number = 1, 
  fallback: string = '—'
): string {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  
  const num = Number(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return fallback;
  }
  
  return `${num.toFixed(digits)}%`;
}

/**
 * Безопасное форматирование числа как денежной суммы в USD
 * @param value - значение для форматирования (может быть null/undefined/NaN)
 * @param digits - количество знаков после запятой (по умолчанию 2)
 * @param fallback - возвращаемое значение при невалидном числе (по умолчанию '—')
 * @returns строка с символом $ или fallback
 */
export function fmtUSD(
  value: any, 
  digits: number = 2, 
  fallback: string = '—'
): string {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  
  const num = Number(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return fallback;
  }
  
  const formatted = num.toFixed(digits);
  // Добавляем разделители тысяч для больших чисел
  const parts = formatted.split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  
  return `$${parts.join('.')}`;
}

// =============================================================================
// Вспомогательные функции валидации
// =============================================================================

/**
 * Проверяет, является ли значение валидным числом
 * @param value - значение для проверки
 * @returns true если значение валидно как число
 */
export function isValidNumber(value: any): boolean {
  if (value === null || value === undefined || value === '') {
    return false;
  }
  
  const num = Number(value);
  return !Number.isNaN(num) && Number.isFinite(num);
}

/**
 * Безопасное получение числового значения с fallback
 * @param value - значение для конвертации
 * @param fallback - возвращаемое значение при невалидном числе (по умолчанию 0)
 * @returns число или fallback
 */
export function safeNumber(value: any, fallback: number = 0): number {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  
  const num = Number(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return fallback;
  }
  
  return num;
}

// =============================================================================
// Специализированные форматтеры для финансовых данных
// =============================================================================

/**
 * Форматирование веса позиции в портфеле (в процентах)
 * @param value - значение веса (может быть null/undefined/NaN)
 * @returns строка с весом в процентах или '—'
 */
export function fmtWeight(value: any): string {
  return fmtPct(value, 1);
}

/**
 * Форматирование рискового скора (число от 0 до 100)
 * @param value - значение скора (может быть null/undefined/NaN)
 * @returns строка с числом или '—'
 */
export function fmtRiskScore(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—';
  }
  
  const num = Number(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return '—';
  }
  
  // Проверяем что значение в разумных пределах для рискового скора
  if (num < 0 || num > 1000) {
    return '—';
  }
  
  return Math.round(num).toString();
}

/**
 * Форматирование валюты с разделителями тысяч
 * @param value - значение (может être null/undefined/NaN)
 * @returns строка с символом $ или '—'
 */
export function fmtCurrency(value: any): string {
  return fmtUSD(value, 2);
}

// =============================================================================
// Совместимость со старыми функциями из types/insightsV2.ts
// =============================================================================

/**
 * Совместимая функция форматирования процентов (как в insightsV2.ts)
 * @deprecated Используйте fmtPct для новых компонентов
 */
export function formatPercentage(value: any): string {
  return fmtPct(value);
}

/**
 * Совместимая функция форматирования валюты (как в insightsV2.ts)
 * @deprecated Используйте fmtUSD или fmtCurrency для новых компонентов
 */
export function formatCurrency(value: any): string {
  return fmtUSD(value);
}


