import { InsightsResponse, PortfolioSnapshot, IndustryGroup, GrowthBucket, RiskBucket, PositionAnalysis, AnalysisParams } from './types';

// Заглушка данных согласно требованиям
export const mockAnalysisParams: AnalysisParams = {
  model: 'llama3.1:8b',
  horizon_months: 6,
  risk_profile: 'Balanced'
};

export const mockSnapshot: PortfolioSnapshot = {
  total_equity_usd: 50369.05,
  free_usd: 20000.00,
  portfolio_value_usd: 30369.05,
  expected_return_pct: 8.5,
  volatility_annualized_pct: 18.2,
  risk_score_0_100: 62,
  as_of: '2025-10-02'
};

export const mockIndustryGroups: IndustryGroup[] = [
  {
    name: 'Technology',
    weight_pct: 42.3,
    avg_expected_return_pct: 12.1,
    avg_risk_score: 75,
    positions: ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
  },
  {
    name: 'Healthcare', 
    weight_pct: 28.7,
    avg_expected_return_pct: 9.8,
    avg_risk_score: 58,
    positions: ['JNJ', 'PFE', 'UNH']
  },
  {
    name: 'Finance',
    weight_pct: 19.5,
    avg_expected_return_pct: 7.2,
    avg_risk_score: 45,
    positions: ['JPM', 'BAC']
  },
  {
    name: 'Consumer Discretionary',
    weight_pct: 9.5,
    avg_expected_return_pct: 15.2,
    avg_risk_score: 68,
    positions: ['AMZN']
  }
];

export const mockGrowthBuckets: GrowthBucket[] = [
  {
    category: 'High growth',
    weight_pct: 28.4,
    avg_expected_return_pct: 18.7,
    positions: ['TSLA', 'AMZN', 'GOOGL']
  },
  {
    category: 'Mid growth',
    weight_pct: 45.6,
    avg_expected_return_pct: 10.2,
    positions: ['AAPL', 'MSFT', 'JNJ', 'UNH']
  },
  {
    category: 'Low/Value',
    weight_pct: 26.0,
    avg_expected_return_pct: 4.8,
    positions: ['PFE', 'JPM', 'BAC']
  }
];

export const mockRiskBuckets: RiskBucket[] = [
  {
    category: 'Low',
    weight_pct: 32.1,
    avg_risk_score: 25,
    avg_expected_return_pct: 6.4,
    positions: ['JPM', 'BAC', 'PFE']
  },
  {
    category: 'Moderate',
    weight_pct: 41.3,
    avg_risk_score: 55,
    avg_expected_return_pct: 9.8,
    positions: ['AAPL', 'MSFT', 'JNJ', 'UNH']
  },
  {
    category: 'High',
    weight_pct: 26.6,
    avg_risk_score: 82,
    avg_expected_return_pct: 15.9,
    positions: ['TSLA', 'AMZN', 'GOOGL']
  }
];

export const mockPositionAnalysis: PositionAnalysis[] = [
  {
    symbol: 'AAPL',
    thesis: 'Сильное фундаментальное положение с устойчивой денежной генерацией и расширяющимися сервисными доходами. Компания продолжает инновации в AR/VR и автогоме.',
    risks: [
      'Зависимость от iPhone продаж составляет 52% выручки',
      'Китайский рынок под давлением регуляторов'
    ],
    action: 'Hold',
    valuation: 'fair',
    momentum: 'up',
    quality: 'high',
    expected_return_pct: 11.2,
    risk_score: 58,
    volatility_pct: 22.1,
    weight_pct: 18.5
  },
  {
    symbol: 'TSLA',
    thesis: 'Пионер электромобилей с дальновидным тарифом в области искусственного интеллекта и робототехники. FSD и Robotaxi являются потенциальными каталистами роста.',
    risks: [
      'Высокая волатильность акций и зависимость от Илона Маска',
      'Ужесточение конкуренции в рынке электромобилей'
    ],
    action: 'Add',
    valuation: 'cheap',
    momentum: 'up',
    quality: 'medium',
    expected_return_pct: 25.3,
    risk_score: 85,
    volatility_pct: 45.2,
    weight_pct: 12.3
  },
  {
    symbol: 'GOOGL',
    thesis: 'Доминирование поиска с растущим потенциалом в облачных вычислениях и ИИ. YouTube и рекламный бизнес показывают устойчивый рост.',
    risks: [
      'Регуляторное давление на рекламный бизнес',
      'Конкуренция с Microsoft в области генеративного ИИ'
    ],
    action: 'Hold',
    valuation: 'cheap',
    momentum: 'flat',
    quality: 'high',
    expected_return_pct: 13.7,
    risk_score: 68,
    volatility_pct: 28.4,
    weight_pct: 15.8
  },
  {
    symbol: 'MSFT',
    thesis: 'Акселерация роста в облачной инфраструктуре Azure и продуктивности Office 365. GitHub и LinkedIn обеспечивают сильную экосистему.',
    risks: [
      'Потенциальные экономические ослабления могут снизить ИТ-расходы',
      'Конкуренция с Amazon AWS остается интенсивной'
    ],
    action: 'Hold',
    valuation: 'fair',
    momentum: 'up',
    quality: 'high',
    expected_return_pct: 9.8,
    risk_score: 52,
    volatility_pct: 24.1,
    weight_pct: 11.2
  }
];

export const mockInsightsResponse: InsightsResponse = {
  status: 'ok',
  model: 'llama3.1:8b',
  snapshot: mockSnapshot,
  groupings: {
    industries: mockIndustryGroups,
    growth_buckets: mockGrowthBuckets,
    risk_buckets: mockRiskBuckets
  },
  position_analysis: mockPositionAnalysis
};

// Функция для генерации случайных данных для тестирования
export function generateRandomInsights(params: AnalysisParams): InsightsResponse {
  const baseSnapshot: PortfolioSnapshot = {
    total_equity_usd: 45000 + Math.random() * 20000,
    free_usd: 15000 + Math.random() * 10000,
    portfolio_value_usd: 25000 + Math.random() * 15000,
    expected_return_pct: 5 + Math.random() * 15,
    volatility_annualized_pct: 15 + Math.random() * 20,
    risk_score_0_100: 40 + Math.random() * 40,
    as_of: new Date().toISOString().split('T')[0]
  };

  const symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META', 'NFLX'];
  const industries = ['Technology', 'Healthcare', 'Finance', 'Consumer Discretionary'];
  
  const industriesData: IndustryGroup[] = industries.map((industry, i) => ({
    name: industry,
    weight_pct: 15 + Math.random() * 25,
    avg_expected_return_pct: 5 + Math.random() * 15,
    avg_risk_score: 30 + Math.random() * 40,
    positions: symbols.slice(i * 2, (i + 1) * 2)
  }));

  // Нормализуем веса промышленности
  const totalIndustryWeight = industriesData.reduce((sum, ind) => sum + ind.weight_pct, 0);
  industriesData.forEach(ind => {
    ind.weight_pct = (ind.weight_pct / totalIndustryWeight) * 100;
  });

  return {
    status: 'ok',
    model: params.model,
    snapshot: baseSnapshot,
    groupings: {
      industries: industriesData,
      growth_buckets: mockGrowthBuckets,
      risk_buckets: mockRiskBuckets
    },
    position_analysis: mockPositionAnalysis
  };
}


