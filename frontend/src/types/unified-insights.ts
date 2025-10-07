/**
 * TypeScript типы для Unified AI Insights согласно спецификации
 */

// === Request модели ===

export interface UnifiedInsightsRequest {
  /** Горизонт анализа в месяцах */
  horizon_months: number;
  
  /** Профиль риска */
  risk_profile: string;
  
  /** Модель LLM */
  model: string;
  
  /** Температура модели */
  temperature: number;
  
  /** Top-p параметр */
  top_p: number;
  
  /** Максимум токенов */
  max_tokens: number;
  
  /** Язык ответа */
  locale: string;
  
  /** Включать торговые сигналы */
  include_signals: boolean;
}

// === Response модели ===

export interface UnifiedInsightsResponse {
  /** Загружено из кэша? */
  cached: boolean;
  
  /** Ключ кэша */
  cache_key: string;
  
  /** Версия модели */
  model_version: string;
  
  /** Когда обновлено (ISO timestamp) */
  last_updated: string;
  
  /** Время вычисления на сервере (мс) */
  compute_ms: number;
  
  /** Чистое время LLM вызова (мс) */
  llm_ms: number;
  
  /** Основные данные инсайтов */
  data: UnifiedInsightsData;
}

// === Основные данные согласно спецификации ===

export interface UnifiedInsightsData {
  /** Сводка портфеля */
  portfolio_summary: PortfolioSummary;
  
  /** Анализ позиций */
  positions_analysis: PositionAnalysis[];
  
  /** Рыночный прогноз */
  market_outlook: MarketOutlook;
}

export interface PortfolioSummary {
  /** Оценка риска */
  risk_score: string;
  
  /** Диверсификация */
  diversification: string;
  
  /** Общая рекомендация */
  recommendation: string;
  
  /** Дополнительные метрики */
  metrics?: {
    total_value: number;
    number_positions: number;
    concentration_risk: number;
    volatility_score: number;
  };
}

export interface PositionAnalysis {
  /** Символ инструмента */
  symbol: string;
  
  /** AI инсайты по позиции */
  insights: {
    /** Оценка справедливой стоимости */
    valuation: string;
    
    /** Импульс */
    momentum: string;
    
    /** Действие */
    action: string;
    
    /** Дополнительные сигналы */
    signals?: {
      technical: string;
      fundamental: string;
      sentiment: string;
    };
  };
  
  /** Дополнительная информация */
  additional?: {
    current_price: number;
    target_price?: number;
    confidence: number; // 0-100
  };
}

export interface MarketOutlook {
  /** Текущий тренд */
  current_trend: string;
  
  /** Ключевые риски */
  key_risks: string[];
  
  /** Возможности */
  opportunities: string[];
  
  /** Дополнительный контекст */
  context?: {
    sector_rotation: string;
    macro_environment: string;
    volatility_forecast: string;
  };
}









