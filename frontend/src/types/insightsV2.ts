/**
 * Insights v2 Types для фронтенда
 * Соответствуют бэкенд схемам согласно техническому заданию
 */

// Переэкспорт функций форматирования из новых утилит для совместимости
import { formatPercentage as fmtPercentage, formatCurrency as fmtCurrency } from '../utils/number';

// Импорт sentiment типов
import { SentimentGrouping, PositionSentimentData } from './sentiment';

// Интеграция с sentiment данными
export interface SentimentKPI {
  portfolio_sentiment: number;
  portfolio_coverage: number;
  sentiment_badge: 'Bullish' | 'Neutral' | 'Bearish';
  has_sufficient_data: boolean;
}

export interface SentimentInsights {
  portfolio_metrics: SentimentKPI;
  sentiment_grouping?: SentimentGrouping;
  positions_sentiment?: PositionSentimentData[];
}

// === Шаг A: PreparedInsights (детерминированные данные) ===

export interface PositionPrepared {
  symbol: string;
  name: string;
  industry: string;
  weight_pct: number;
  growth_forecast_pct?: number;
  risk_score_0_100?: number;
  expected_return_horizon_pct: number;
  volatility_pct?: number;
}

export interface PortfolioSummary {
  total_equity_usd: number;
  free_usd: number;
  portfolio_value_usd: number;
  expected_return_horizon_pct: number;
  volatility_annualized_pct?: number;
  risk_score_0_100?: number;
  risk_class: 'Low' | 'Moderate' | 'High';
  as_of: string;
}

export interface GroupingData {
  name: string;
  weight_pct: number;
  avg_expected_return_pct?: number;
  avg_risk_score?: number;
  positions: string[];
}

export interface PreparedInsights {
  schema_version: 'insights.v2';
  summary: PortfolioSummary;
  grouping: {
    by_industry: GroupingData[];
    by_growth_bucket: GroupingData[];
    by_risk_bucket: GroupingData[];
  };
  positions: PositionPrepared[];
}

// === Шаг B: LLM данные (только тексты) ===

export interface LLMInsightSignals {
  valuation: 'cheap' | 'fair' | 'expensive';
  momentum: 'up' | 'flat' | 'down' | 'neutral';
  quality: 'high' | 'med' | 'low';
}

export interface LLMInsight {
  thesis: string; // ≤ 240 символов
  risks: string[]; // 1-3 пункта
  action: 'Add' | 'Hold' | 'Trim' | 'Hedge';
  signals: LLMInsightSignals;
}

export interface LLMInsightPosition {
  symbol: string;
  insights: LLMInsight;
}

export interface LLMInsightsResponse {
  schema_version: 'insights.v2';
  as_of_copy?: string;
  positions: LLMInsightPosition[];
}

// === Финальный объединенный тип для UI ===

export interface PositionAnalysis {
  symbol: string;
  name: string;
  industry: string;
  weight_pct: number;
  growth_forecast_pct?: number;
  risk_score_0_100?: number;
  expected_return_horizon_pct: number;
  volatility_pct?: number;
  insights?: LLMInsight; // Данные от LLM для этой позиции
}

// Computed свойства для UI
export type RiskCategory = 'Low' | 'Moderate' | 'High';
export type GrowthCategory = 'High' | 'Mid' | 'Low';

export function getRiskCategory(position: PositionAnalysis): RiskCategory {
  if (!position.risk_score_0_100) return 'Moderate';
  if (position.risk_score_0_100 <= 33) return 'Low';
  if (position.risk_score_0_100 <= 66) return 'Moderate';
  return 'High';
}

export function getGrowthCategory(position: PositionAnalysis): GrowthCategory {
  if (!position.growth_forecast_pct) return 'Low';
  if (position.growth_forecast_pct >= 15) return 'High';
  if (position.growth_forecast_pct >= 5) return 'Mid';
  return 'Low';
}

// === Запрос и ответ API ===

export interface InsightsV2Request {
  model: string;
  horizon_months: number; // 1-24
  risk_profile: 'Conservative' | 'Balanced' | 'Aggressive';
}

export interface InsightsV2Response {
  status: 'ok' | 'error' | 'partial';
  model: string;
  prepared_data: PreparedInsights;
  llm_data?: LLMInsightsResponse;
  errors: string[];
  positions_with_insights: PositionAnalysis[];
}

export interface AnalysisResult {
  model: string;
  success: boolean;
  escalation_rate?: number; // Частота repair-retry в %
  prepared_data?: PreparedInsights;
  llm_data?: LLMInsightsResponse;
  final_response?: InsightsV2Response;
  errors: string[];
}

// === Пороги для UI классификации (источник истины — бэкенд) ===
export const RISK_THRESHOLDS = {
  LOW: 33,
  MODERATE: 66,
  HIGH: 100
} as const;

export const GROWTH_THRESHOLDS = {
  HIGH_MIN: 15,
  MID_MIN: 5
} as const;

// === Валидация данных ===
export function validateInsightsResponse(response: any): boolean {
  if (!response || typeof response !== 'object') return false;
  
  // Проверяем обязательные поля
  if (!response.status || !response.model || !response.prepared_data) return false;
  
  // Проверяем структуру prepared_data
  const preparedData = response.prepared_data;
  if (!preparedData.summary || !preparedData.positions || !Array.isArray(preparedData.positions)) {
    return false;
  }
  
  // Проверяем группировки
  const grouping = preparedData.grouping;
  if (!grouping || !grouping.by_industry || !grouping.by_growth_bucket || !grouping.by_risk_bucket) {
    return false;
  }
  
  return true;
}

// === Утилиты для UI ===
export function calculateWeightNormalization(positions: PositionPrepared[]): boolean {
  const totalWeight = positions.reduce((sum, pos) => sum + pos.weight_pct, 0);
  return Math.abs(totalWeight - 100.0) <= 0.5; // Нормализованы локально если отклонение > 0.5%
}

export function formatPercentage(value: number | undefined): string {
  return fmtPercentage(value);
}

export function formatCurrency(value: number | undefined): string {
  return fmtCurrency(value);
}
