/**
 * TypeScript типы для системы анализа сентимента новостей
 */

// === Базовые типы ===

export type SentimentType = 'negative' | 'neutral' | 'positive';

export type SentimentModel = 'finllama' | 'finbert';

export interface SentimentResult {
  symbol: string;
  sentiment: SentimentType;
  confidence: number;
  strength: number;
  note?: string;
}

export interface SentimentScoreResponse {
  model: SentimentModel;
  results: SentimentResult[];
  as_of: string;
  total_processed: number;
  successful: number;
  failed: number;
  avg_confidence: number;
}

// === Portfolio метрики ===

export interface PortfolioSentimentMetrics {
  portfolio_sentiment_7d: number;
  portfolio_sentiment_30d: number;
  portfolio_coverage_7d: number;
  portfolio_coverage_30d: number;
  portfolio_delta_7v30: number;
  bullish_count: number;
  neutral_count: number;
  bear_count: number;
  weighted_by_position: boolean;
  as_of: string;
}

// === Группировки ===

export interface SentimentBucket {
  bucket_name: 'Bullish' | 'Neutral' | 'Bearish';
  sentiment_range: [number, number];
  weight_pct: number;
  avg_sentiment_score: number;
  positions: string[];
  count: number;
}

export interface SentimentGrouping {
  timeframe: '7d' | '30d';
  buckets: SentimentBucket[];
  total_coverage: number;
  fallback_rate: number;
}

// === Данные позиций ===

export interface PositionNewsItem {
  headline: string;
  published_at: string;
  sentiment: SentimentType;
  confidence: number;
  source_weight: number;
}

export interface PositionSentimentData {
  symbol: string;
  sentiment_score_7d: number;
  sentiment_score_30d: number;
  confidence_7d: number;
  confidence_30d: number;
  delta_7v30: number;
  coverage_count_7d: number;
  coverage_count_30d: number;
  top_news: PositionNewsItem[];
  has_data_gap: boolean;
  model_used: SentimentModel;
  last_updated: string;
}

// === Конфигурация ===

export interface SentimentConfig {
  enabled: boolean;
  model_primary: SentimentModel;
  model_fallback: SentimentModel;
  default_window_days: number;
  decay_halflife_days: number;
  cache_ttl_hours: number;
  
  // Пороги для UI
  bullish_threshold: number;
  bearish_threshold: number;
  trend_threshold: number;
}

// === Утилиты и помощники ===

export class SentimentUtils {
  
  /**
   * Получение label для sentiment значения
   */
  static getSentimentLabel(sentiment: SentimentType): 'Bullish' | 'Neutral' | 'Bearish' {
    switch (sentiment) {
      case 'positive': return 'Bullish';
      case 'negative': return 'Bearish';
      default: return 'Neutral';
    }
  }
  
  /**
   * Получение бейджа для sentiment значения с учетом числовой шкалы
   */
  static getSentimentBadge(score: number): 'Bullish' | 'Neutral' | 'Bearish' {
    if (score >= 0.2) return 'Bullish';
    if (score <= -0.2) return 'Bearish';
    return 'Neutral';
  }
  
  /**
   * Получение цвета для sentiment значения
   */
  static getSentimentColor(sentiment: SentimentType): string {
    switch (sentiment) {
      case 'positive': return 'text-green-400 bg-green-500/20';
      case 'negative': return 'text-red-400 bg-red-500/20';
      default: return 'text-yellow-400 bg-yellow-500/20';
    }
  }
  
  /**
   * Получение цвета для числового sentiment score
   */
  static getSentimentScoreColor(score: number): string {
    if (score >= 0.2) return 'text-green-400 bg-green-500/20';
    if (score <= -0.2) return 'text-red-400 bg-red-500/20';
    return 'text-yellow-400 bg-yellow-500/20';
  }
  
  /**
   * Получение иконки тренда
   */
  static getTrendIcon(delta: number): string {
    if (delta >= 0.1) return '↗';  // Повышающийся тренд
    if (delta <= -0.1) return '↘'; // Понижающийся тренд
    return '→';                     // Без изменений
  }
  
  /**
   * Форматирование confidence как проценты
   */
  static formatConfidence(confidence: number): string {
    return `${Math.round(confidence * 100)}%`;
  }
  
  /**
   * Форматирование sentiment score для отображения
   */
  static formatSentimentScore(score: number): string {
    const sign = score >= 0 ? '+' : '';
    return `${sign}${score.toFixed(2)}`;
  }
  
  /**
   * Получение текстового описания sentiment
   */
  static getSentimentDescription(sentiment: SentimentType): string {
    switch (sentiment) {
      case 'positive': return 'Положительный';
      case 'negative': return 'Негативный';
      default: return 'Нейтральный';
    }
  }
  
  /**
   * Проверка достаточности данных для отображения
   */
  static hasEnoughData(coverage_count: number): boolean {
    return coverage_count >= 5; // Минимум 5 новостей для статистической значимости
  }
  
  /**
   * Получение статуса качества данных
   */
  static getDataQualityStatus(data: PositionSentimentData): 'good' | 'limited' | 'insufficient' {
    if (data.has_data_gap) return 'insufficient';
    if (data.coverage_count_30d < 5) return 'limited';
    return 'good';
  }
}

// === Константы ===

export const SENTIMENT_THRESHOLDS = {
  BULLISH: 0.2,
  BEARISH: -0.2,
  TREND: 0.1
} as const;

export const SENTIMENT_CONFIG: SentimentConfig = {
  enabled: true,
  model_primary: 'finllama',
  model_fallback: 'finbert',
  default_window_days: 30,
  decay_halflife_days: 14,
  cache_ttl_hours: 12,
  bullish_threshold: SENTIMENT_THRESHOLDS.BULLISH,
  bearish_threshold: SENTIMENT_THRESHOLDS.BEARISH,
  trend_threshold: SENTIMENT_THRESHOLDS.TREND
} as const;

// === API запросы ===

export interface SentimentApiClient {
  /**
   * Получение портфельных метрик сентимента
   */
  getPortfolioSentiment(userId: string, windowDays?: number): Promise<PortfolioSentimentMetrics>;
  
  /**
   * Получение группировки по сентименту
   */
  getSentimentGrouping(userId: string, timeframe?: '7d' | '30d'): Promise<SentimentGrouping>;
  
  /**
   * Получение сентимент данных для позиций
   */
  getPositionsSentiment(userId: string, topNewsCount?: number): Promise<PositionSentimentData[]>;
  
  /**
   * Инвалидация кэша (форс-рефреш)
   */
  invalidateCache(symbol?: string): Promise<{ message: string }>;
}
