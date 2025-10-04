// Новые типы для Insights v2 согласно требованиям

// Основные интерфейсы портфеля
export interface PositionInsight {
  symbol: string;
  name: string;
  sector?: string;
  industry?: string;
  value_usd: number;
  weight_pct: number;
  growth_forecast_pct?: number;
  risk_score_0_100?: number;
  expected_return_pct?: number;
  volatility_pct?: number;
}

export interface PortfolioSnapshot {
  total_equity_usd: number;
  free_usd?: number;
  portfolio_value_usd: number;
  expected_return_pct?: number;
  volatility_annualized_pct?: number;
  risk_score_0_100?: number;
  as_of: string;
}

// Текущие группировки
export interface IndustryGroup {
  name: string;
  weight_pct: number;
  avg_expected_return_pct?: number;
  avg_risk_score?: number;
  positions: string[]; // символы позиций
}

export interface GrowthBucket {
  category: 'High growth' | 'Mid growth' | 'Low/Value';
  weight_pct: number;
  avg_expected_return_pct?: number;
  positions: string[];
}

export interface RiskBucket {
  category: 'Low' | 'Moderate' | 'High';
  weight_pct: number;
  avg_risk_score?: number;
  avg_expected_return_pct?: number;
  positions: string[];
}

// Пер-позиционные инсайты
export interface PositionAnalysis {
  symbol: string;
  thesis: string; // до 240 символов
  risks: string[]; // 2-3 рисковых фактора
  action: 'Hold' | 'Trim' | 'Add' | 'Hedge';
  valuation: 'fair' | 'expensive' | 'cheap';
  momentum: 'up' | 'flat' | 'down';
  quality: 'high' | 'medium' | 'low';
  expected_return_pct?: number;
  risk_score?: number;
  volatility_pct?: number;
  weight_pct: number;
}

// Параметры анализа
export interface AnalysisParams {
  model: string;
  horizon_months: number;
  risk_profile: 'Conservative' | 'Balanced' | 'Aggressive';
}

// Полный ответ API
export interface InsightsResponse {
  status: 'ok' | 'error';
  model: string;
  snapshot: PortfolioSnapshot;
  groupings: {
    industries: IndustryGroup[];
    growth_buckets: GrowthBucket[];
    risk_buckets: RiskBucket[];
  };
  position_analysis: PositionAnalysis[];
  errors?: string[];
}

// Утилиты для группировки
export function categorizeGrowthPositions(positions: PositionInsight[]): {
  [key: string]: PositionInsight[];
} {
  const buckets = {
    'High growth': [] as PositionInsight[],
    'Mid growth': [] as PositionInsight[],
    'Low/Value': [] as PositionInsight[]
  };

  positions.forEach(pos => {
    const growth = pos.growth_forecast_pct;
    if (growth === null || growth === undefined || growth < 5) {
      buckets['Low/Value'].push(pos);
    } else if (growth < 15) {
      buckets['Mid growth'].push(pos);
    } else {
      buckets['High growth'].push(pos);
    }
  });

  return buckets;
}

export function categorizeRiskPositions(positions: PositionInsight[]): {
  [key: string]: PositionInsight[];
} {
  const buckets = {
    'Low': [] as PositionInsight[],
    'Moderate': [] as PositionInsight[],
    'High': [] as PositionInsight[]
  };

  positions.forEach(pos => {
    const risk = pos.risk_score_0_100;
    if (risk === null || risk === undefined) {
      buckets['Moderate'].push(pos);
    } else if (risk <= 33) {
      buckets['Low'].push(pos);
    } else if (risk <= 66) {
      buckets['Moderate'].push(pos);
    } else {
      buckets['High'].push(pos);
    }
  });

  return buckets;
}

export function calculateWeightedAverage(positions: PositionInsight[], field: keyof PositionInsight): number | null {
  const relevantPositions = positions.filter(pos => 
    pos[field] !== null && pos[field] !== undefined && pos.weight_pct > 0
  );

  if (relevantPositions.length === 0) return null;

  const totalWeight = positions.reduce((sum, pos) => sum + pos.weight_pct, 0);
  if (totalWeight === 0) return null;

  const weightedSum = relevantPositions.reduce((sum, pos) => {
    return sum + ((pos[field] as number) * pos.weight_pct);
  }, 0);

  return weightedSum / totalWeight;
}

// Пороги для классификации риска
export const RISK_THRESHOLDS = {
  LOW: 33,
  MODERATE: 66,
  HIGH: 100
} as const;

export type RiskCategory = 'Low' | 'Moderate' | 'High';
export type GrowthCategory = 'High growth' | 'Mid growth' | 'Low/Value';

export function getRiskCategory(score?: number): RiskCategory {
  if (!score && score !== 0) return 'Moderate';
  if (score <= RISK_THRESHOLDS.LOW) return 'Low';
  if (score <= RISK_THRESHOLDS.MODERATE) return 'Moderate';
  return 'High';
}

export function getGrowthCategory(growth?: number): GrowthCategory {
  if (!growth && growth !== 0) return 'Low/Value';
  if (growth < 5) return 'Low/Value';
  if (growth < 15) return 'Mid growth';
  return 'High growth';
}







