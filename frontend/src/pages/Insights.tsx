import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/auth';
import { KPICard } from '../components/insights/KPICard';
import { GroupVisualization } from '../components/insights/GroupVisualization';
import { SentimentGroupVisualization } from '../components/insights/SentimentGroupVisualization';
import { AnalysisControls } from '../components/insights/AnalysisControls';
import { 
  InsightsV2Response, 
  InsightsV2Request
} from '../types/insightsV2';
import { fmtPct, fmtUSD, fmtWeight, fmtRiskScore } from '../utils/number';
import { sentimentAPI } from '../lib/api-sentiment';
import { PortfolioSentimentMetrics, SentimentUtils, SentimentGrouping } from '../types/sentiment';

// === Новые типы для Fixed Insights API ===
interface FixedInsightsData {
  rating: {
    score: number;
    label: string;
    risk_level: string;
  };
  overview: {
    headline: string;
    tags: string[];
    key_strengths: string[];
    key_concerns: string[];
  };
  categories: Array<{
    name: string;
    score: number;
    note: string;
    trend: string;
  }>;
  insights: string[];
  risks: Array<{
    item: string;
    severity: string;
    mitigation: string;
    impact: string;
  }>;
  performance: {
    since_buy_pl_pct: number;
    comment: string;
    win_rate_pct?: number;
    avg_position_return?: number;
  };
  diversification: {
    score: number;
    concentration_risk: string;
    sector_diversity?: string;
  };
  actions: Array<{
    title: string;
    rationale: string;
    expected_impact: string;
    priority: number;
    timeframe: string;
  }>;
  summary_markdown: string;
}

interface FixedInsightsResponse {
  success: boolean;
  cached: boolean;
  model: string;
  llm_ms: number;
  compute_ms: number;
  data: FixedInsightsData;
}

export default function Insights() {
  const { user_id } = useAuthStore();
  
  // Fixed Insights данные
  const [insightsData, setInsightsData] = useState<FixedInsightsData | null>(null);
  
  // Легаси поддержка для компонентов UI
  const [analysisData, setAnalysisData] = useState<InsightsV2Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Флаг для предотвращения многократного автоматического запуска (ВРЕМЕННО ОТКЛЮЧЕН)
  // const [hasRunInitialAnalysis, setHasRunInitialAnalysis] = useState(false);
  
  // === Метаданные кэша ===
  const [cacheMetadata, setCacheMetadata] = useState<{
    cached: boolean;
    lastUpdated: Date | null;
    e2eMs: number;
    llmMs: number;
    modelVersion: string;
  }>({
    cached: false,
    lastUpdated: null,
    e2eMs: 0,
    llmMs: 0,
    modelVersion: ''
  });
  
  // Sentiment данные
  const [sentimentData, setSentimentData] = useState<PortfolioSentimentMetrics | null>(null);
  const [sentimentGrouping, setSentimentGrouping] = useState<SentimentGrouping | null>(null);
  const [sentimentLoading, setSentimentLoading] = useState(false);
  const [escalationRate, setEscalationRate] = useState<number | null>(null);
  
  // Параметры анализа для Insights
  const [params, setParams] = useState<InsightsV2Request>(() => {
    // Проверяем URL параметры или localStorage для сохранения настроек
    const urlParams = new URLSearchParams(window.location.search);
    const storedParams = localStorage.getItem('insights-params');
    
    const defaultParams: InsightsV2Request = {
      model: 'llama3.1:8b',
      horizon_months: 6,
      risk_profile: 'Balanced'
    };
    
    if (storedParams) {
      try {
        const parsed = JSON.parse(storedParams);
        defaultParams.model = parsed.model || defaultParams.model;
        defaultParams.horizon_months = parsed.horizon_months || defaultParams.horizon_months;
        defaultParams.risk_profile = parsed.risk_profile || defaultParams.risk_profile;
      } catch (e) {
        console.warn('Invalid stored params:', e);
      }
    }
    
    // URL параметры имеют приоритет
    if (urlParams.get('model')) defaultParams.model = urlParams.get('model')!;
    if (urlParams.get('horizon')) defaultParams.horizon_months = parseInt(urlParams.get('horizon')!);
    if (urlParams.get('risk')) defaultParams.risk_profile = urlParams.get('risk') as any;
    
    return defaultParams;
  });


  // Сохраняем параметры в localStorage при изменении
  useEffect(() => {
    localStorage.setItem('insights-params', JSON.stringify(params));
    
    // Обновляем URL для шаринга
    const url = new URL(window.location.href);
    url.searchParams.set('model', params.model);
    url.searchParams.set('horizon', params.horizon_months.toString());
    url.searchParams.set('risk', params.risk_profile);
    window.history.replaceState({}, '', url.toString());
  }, [params]);

  // Автоматический старт анализа при первой загрузке (ВРЕМЕННО ОТКЛЮЧЕН)
  useEffect(() => {
    // ВРЕМЕННО ОТКЛЮЧЕНО для диагностики проблемы постоянных запросов
    /*
    if (user_id && !insightsData && !loading && !hasRunInitialAnalysis) {
      console.log('Auto-starting analysis for user:', user_id);
      setHasRunInitialAnalysis(true);
      runAnalysis();
    }
    */
  }, [user_id]);

  const loadSentimentData = async () => {
    if (!user_id) {
      console.error('No user ID available for sentiment analysis');
      return;
    }

    setSentimentLoading(true);

    try {
      console.log('Loading sentiment data for user:', user_id);
      
      // Параллельная загрузка sentiment данных
      const [portfolioMetrics, grouping] = await Promise.all([
        sentimentAPI.getPortfolioSentiment(user_id, 30),
        sentimentAPI.getSentimentGrouping(user_id, '30d')
      ]);

      console.log('Sentiment data loaded:', { portfolioMetrics, grouping });
      setSentimentData(portfolioMetrics);
      setSentimentGrouping(grouping);

    } catch (err: any) {
      console.error('Failed to load sentiment data:', err);
      // Не устанавливаем ошибку в общий state, sentiment данные не критичны
    } finally {
      setSentimentLoading(false);
    }
  };

  const runAnalysis = async () => {
    if (!user_id) return;
    
    setLoading(true);
    setError(null);
    setEscalationRate(null);
    
    const startTime = performance.now();
    
    try {
      console.log('🚀 Starting INSIGHTS ANALYSIS with SWR - params:', params);
      
      // 🔄 Используем новый исправленный API с кэшированием
      const [response] = await Promise.all([
        fetch(`/ai/insights/fixed/?user_id=${user_id}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            horizon_months: params.horizon_months,
            risk_profile: params.risk_profile,
            model: params.model,
            temperature: 0.2,
            language: 'ru',
            cache_mode: 'default'
          })
        }).then(res => res.json()) as Promise<FixedInsightsResponse>,
        loadSentimentData() // Загружаем sentiment данные в фоне
      ]);
      
      const e2eMs = Math.round(performance.now() - startTime);
      
      // 🎯 Сохраняем данные
      setInsightsData(response.data);
      
      // Обновляем метаданные кэша из response
      setCacheMetadata({
        cached: response.cached,
        lastUpdated: new Date(),
        e2eMs: e2eMs,
        llmMs: response.llm_ms || 0,
        modelVersion: response.model || 'unknown'
      });
      
      console.log('✅ Analysis completed:', response);
      console.log('⚡ Performance:', `${response.compute_ms}ms total, ${response.llm_ms}ms LLM`);
      
    } catch (err: any) {
      console.error('Analysis failed:', err);
      
      let errorMessage = 'Неизвестная ошибка';
      
      if (err.message) {
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else if (err.error) {
        errorMessage = err.error;
      }
      
      setError(errorMessage);
      
      // Очищаем данные при ошибке
      setAnalysisData(null);
  } finally {
    setLoading(false);
  }
};

// Обработчик для принудительного обновления кэша
const handleRefresh = async () => {
  console.log('🔄 Manual refresh requested');
  setCacheMetadata({...cacheMetadata, cached: false});
  
  try {
    setLoading(true);
    setError(null);
    
    const response = await fetch(`/ai/insights/fixed/?user_id=${user_id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        horizon_months: params.horizon_months,
        risk_profile: params.risk_profile,
        model: params.model,
        temperature: 0.2,
        language: 'ru',
        cache_mode: 'refresh' // Принудительное обновление кэша
      })
    });
    
    const data = await response.json() as FixedInsightsResponse;
    
    setInsightsData(data.data);
    
    setCacheMetadata({
      cached: false, // Обновленные данные
      lastUpdated: new Date(),
      e2eMs: Math.round(performance.now() - performance.now()),
      llmMs: data.llm_ms || 0,
      modelVersion: data.model || 'unknown'
    });
    
  } catch (error) {
    console.error('Cache refresh failed:', error);
    setError(error instanceof Error ? error.message : 'Refresh failed');
  } finally {
    setLoading(false);
  }
};

  if (!user_id) {
    return (
      <div className="space-y-8">
        <div className="text-center py-16">
          <div className="text-6xl mb-4">🔐</div>
          <h2 className="text-2xl font-bold text-white mb-2">Авторизация required</h2>
          <p className="text-slate-400">Войдите в систему для доступа к анализу портфеля</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div className="text-center py-16">
          <div className="text-6xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-white mb-2">Ошибка анализа</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 transition-all duration-200 disabled:opacity-50"
          >
            Повторить попытку
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Заголовок с метаданными кэша */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              📊 Portfolio Insights
            </h1>
            {cacheMetadata.lastUpdated && (
              <>
                <span className={`px-3 py-1 rounded-full text-sm font-medium border ${
                  cacheMetadata.cached 
                    ? 'bg-green-500/20 text-green-400 border-green-500/30' 
                    : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
                }`}>
                  {cacheMetadata.cached ? '⭐ Из кэша' : '🔄 Обновлено'}
                </span>
              </>
            )}
          </div>
          <p className="text-slate-400 mt-2">Комплексный анализ с группировками и пер-позиционными инсайтами</p>
          
          {/* Метрики производительности */}
          {cacheMetadata.lastUpdated && (
            <div className="flex items-center gap-6 text-sm text-slate-400 mt-3">
              <div>
                <span className="font-medium">Обновлено:</span> {cacheMetadata.lastUpdated.toLocaleString()}
              </div>
              <div>
                <span className="font-medium">E2E:</span> {cacheMetadata.e2eMs}ms
              </div>
              {cacheMetadata.llmMs > 0 && (
                <div>
                  <span className="font-medium">LLM:</span> {cacheMetadata.llmMs}ms
                </div>
              )}
              <div>
                <span className="font-medium">Модель:</span> {cacheMetadata.modelVersion}
              </div>
            </div>
          )}
        </div>
        
        {/* Кнопка обновления и статус AI */}
        <div className="flex items-center gap-3">
          {cacheMetadata.lastUpdated && (
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 disabled:opacity-50 rounded-lg text-sm text-white transition-colors flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Обновляется...
                </>
              ) : (
                <>
                  🔄 Обновить
                </>
              )}
            </button>
          )}
          <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-400">
            <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
            <span>AI Powered</span>
          </div>
        </div>
      </div>

      {/* Параметры анализа */}
      <AnalysisControls
        params={params}
        onChange={setParams}
        onAnalyze={runAnalysis}
        isLoading={loading}
      />

      {!insightsData ? (
        // Состояние загрузки
            <div className="space-y-6">
          {loading ? (
            <div className="text-center py-16">
              <div className="text-8xl mb-6">🤖</div>
              <h2 className="text-2xl font-bold text-white mb-4">Анализирую портфель...</h2>
              <p className="text-lg text-slate-400 mb-8">AI обрабатывает данные и генерирует инсайты</p>
              <div className="flex justify-center mb-6">
                <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
                  </div>
              <p className="text-sm text-slate-500">Это может занять несколько секунд</p>
                      </div>
                    ) : (
            <div className="space-y-6">
              <div className="text-center py-8">
                <div className="text-4xl mb-4">📊</div>
                <h3 className="text-lg font-semibold text-white mb-2">Готов к анализу</h3>
                <p className="text-slate-400 mb-4">Настройте параметры и запустите анализ портфеля</p>
                <button
                  onClick={runAnalysis}
                  disabled={loading}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 transition-all duration-200 disabled:opacity-50"
                >
                  Запустить анализ
                  </button>
                </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Array.from({ length: 6 }).map((_, i) => (
                  <KPICard
                    key={i}
                    title="—"
                    value="—"
                    subtitle="Ожидание данных"
                  />
                ))}
                    </div>
                  </div>
                )}
              </div>
      ) : insightsData ? (
        // Fixed Insights данные - полноценное отображение
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">AI Insights (SWR Cache)</h2>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                cacheMetadata.cached 
                  ? 'bg-emerald-900/30 text-emerald-300 border border-emerald-500/30' 
                  : 'bg-orange-900/30 text-orange-300 border border-orange-500/30'
              }`}>
                {cacheMetadata.cached ? '🚀 CACHED' : '🤖 LLM GENERATION'}
              </div>
            </div>
            
            {/* Метрики производительности */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="bg-slate-700/30 rounded-lg p-3">
                <div className="text-xs text-slate-400 mb-1">Response Time</div>
                <div className={`text-sm font-medium ${cacheMetadata.e2eMs < 100 ? 'text-emerald-400' : 'text-orange-400'}`}>
                  {cacheMetadata.e2eMs}ms total
                </div>
              </div>
              <div className="bg-slate-700/30 rounded-lg p-3">
                <div className="text-xs text-slate-400 mb-1">LLM Processing</div>
                <div className={`text-sm font-medium ${cacheMetadata.llmMs < 500 ? 'text-emerald-400' : 'text-orange-400'}`}>
                  {cacheMetadata.llmMs}ms model
                </div>
              </div>
              <div className="bg-slate-700/30 rounded-lg p-3">
                <div className="text-xs text-slate-400 mb-1">Cache Age</div>
                <div className="text-sm font-medium text-slate-300">
                  {cacheMetadata.lastUpdated ? 
                    `${Math.round((Date.now() - cacheMetadata.lastUpdated.getTime()) / 1000)}s ago` : 
                    'N/A'
                  }
                </div>
              </div>
              <div className="bg-slate-700/30 rounded-lg p-3">
                <div className="text-xs text-slate-400 mb-1">Model</div>
                <span className="bg-blue-900/30 text-blue-300 text-xs px-2 py-1 rounded">
                  {cacheMetadata.modelVersion || 'Unknown'}
                </span>
              </div>
            </div>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-medium text-white mb-2">Overview</h3>
                <p className="text-slate-300 mb-2">{insightsData.overview.headline}</p>
                <div className="flex flex-wrap gap-2 mb-3">
                  {insightsData.overview.tags.map((tag, index) => (
                    <span key={index} className="px-2 py-1 bg-blue-500/20 text-xs rounded-full text-blue-300">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-sm text-emerald-300 mb-1">Strengths:</h4>
                    <ul className="text-sm text-slate-300">
                      {insightsData.overview.key_strengths.slice(0, 3).map((strength, index) => (
                        <li key={index} className="mb-1">• {strength}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm text-orange-300 mb-1">Concerns:</h4>
                    <ul className="text-sm text-slate-300">
                      {insightsData.overview.key_concerns.slice(0, 3).map((concern, index) => (
                        <li key={index} className="mb-1">• {concern}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-medium text-white mb-2">Performance</h3>
                <p className="text-slate-300 mb-2">{insightsData.performance.comment}</p>
                <div className="text-lg font-semibold text-emerald-400">
                  {fmtPct(insightsData.performance.since_buy_pl_pct)}
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-medium text-white mb-2">Key Insights</h3>
                <ul className="space-y-2">
                  {insightsData.insights.map((insight, index) => (
                    <li key={index} className="text-slate-300 flex items-start">
                      <span className="text-emerald-400 mr-2">•</span>
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>
              
              <div>
                <h3 className="text-lg font-medium text-white mb-2">Rating & Risks</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-slate-700/50 rounded p-3">
                    <div className="text-sm text-slate-400">Overall Score</div>
                    <div className="text-lg font-semibold text-white">{insightsData.rating.score}/10</div>
                    <div className="text-xs text-slate-400">{insightsData.rating.label}</div>
                  </div>
                  <div className="bg-slate-700/50 rounded p-3">
                    <div className="text-sm text-slate-400">Diversification</div>
                    <div className="text-lg font-semibold text-white">{insightsData.diversification.score}/10</div>
                    <div className="text-xs text-slate-400">{insightsData.rating.risk_level}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : analysisData ? (
        <>
          {/* KPI Карточки */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <KPICard
              title="Total Equity"
              value={fmtUSD(analysisData.prepared_data.summary.total_equity_usd)}
              icon={<span className="text-white text-sm">💼</span>}
              asOf={analysisData.prepared_data.summary.as_of}
            />
            
            <KPICard
              title="Free USD"
              value={fmtUSD(analysisData.prepared_data.summary.free_usd)}
              subtitle="Available cash"
              icon={<span className="text-white text-sm">💰</span>}
              asOf={analysisData.prepared_data.summary.as_of}
            />
            
            <KPICard
              title="Portfolio Value"
              value={fmtUSD(analysisData.prepared_data.summary.portfolio_value_usd)}
              subtitle="Market value"
              icon={<span className="text-white text-sm">📈</span>}
              asOf={analysisData.prepared_data.summary.as_of}
            />
            
            <KPICard
              title="Expected Return"
              value={fmtPct(analysisData.prepared_data.summary.expected_return_horizon_pct)}
              subtitle={`на ${params.horizon_months} мес.`}
              icon={<span className="text-white text-sm">🎯</span>}
              asOf={analysisData.prepared_data.summary.as_of}
            />
            
            <KPICard
              title="Volatility"
              value={fmtPct(analysisData.prepared_data.summary.volatility_annualized_pct)}
              subtitle="Annualized"
              icon={<span className="text-white text-sm">📊</span>}
              asOf={analysisData.prepared_data.summary.as_of}
            />
            
            <KPICard
              title="Risk Score"
              value={`${fmtRiskScore(analysisData.prepared_data.summary.risk_score_0_100)}/100`}
              badge={{
                text: analysisData.prepared_data.summary.risk_class,
                variant: analysisData.prepared_data.summary.risk_class === 'High' ? 'danger' : 
                         analysisData.prepared_data.summary.risk_class === 'Moderate' ? 'warning' : 'success'
              }}
              icon={<span className="text-white text-sm">⚠️</span>}
              asOf={analysisData.prepared_data.summary.as_of}
            />
            
            {/* News Sentiment KPI Cards */}
            {sentimentData && (
              <>
                <KPICard
                  title="News Sentiment (30d)"
                  value={
                    sentimentData.portfolio_coverage_30d >= 5 
                      ? SentimentUtils.formatSentimentScore(sentimentData.portfolio_sentiment_30d)
                      : '—'
                  }
                  subtitle="Based on financial news"
                  badge={{
                    text: SentimentUtils.getSentimentBadge(sentimentData.portfolio_sentiment_30d),
                    variant: SentimentUtils.getSentimentBadge(sentimentData.portfolio_sentiment_30d) === 'Bullish' ? 'success' : 
                             SentimentUtils.getSentimentBadge(sentimentData.portfolio_sentiment_30d) === 'Bearish' ? 'danger' : 'warning'
                  }}
                  icon={<span className="text-white text-sm">📰</span>}
                  asOf={analysisData.prepared_data.summary.as_of}
                />
                
                <KPICard
                  title="News Coverage (30d)"
                  value={sentimentData.portfolio_coverage_30d.toString()}
                  subtitle="Sentiment articles analyzed"
                  icon={<span className="text-white text-sm">📊</span>}
                  asOf={analysisData.prepared_data.summary.as_of}
                />
              </>
            )}
          </div>

          {/* Группировки */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <GroupVisualization
              title="По индустрии"
              type="industry"
              data={analysisData.prepared_data.grouping.by_industry}
              totalWeight={analysisData.prepared_data.grouping.by_industry.reduce((sum, ind) => sum + ind.weight_pct, 0)}
            />
            
            <GroupVisualization
              title="По прогнозу роста"
              type="growth"
              data={analysisData.prepared_data.grouping.by_growth_bucket}
              totalWeight={analysisData.prepared_data.grouping.by_growth_bucket.reduce((sum, bucket) => sum + bucket.weight_pct, 0)}
            />
            
            <GroupVisualization
              title="По риску"
              type="risk"
              data={analysisData.prepared_data.grouping.by_risk_bucket}
              totalWeight={analysisData.prepared_data.grouping.by_risk_bucket.reduce((sum, bucket) => sum + bucket.weight_pct, 0)}
            />
          </div>

          {/* Sentiment группировка */}
          {(sentimentGrouping) && (
            <div className="mt-6">
              <SentimentGroupVisualization 
                grouping={sentimentGrouping}
                isLoading={sentimentLoading}
              />
            </div>
          )}

          {/* Пер-позиционные инсайты */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Инсайты по позициям</h3>
              <div className="text-sm text-slate-400">
                {analysisData.positions_with_insights.length} позиций
              </div>
            </div>

            {analysisData.positions_with_insights.length === 0 ? (
              <div className="text-center text-slate-400 py-8">
                <div className="text-4xl mb-2">📋</div>
                <p>Позиций для анализа не найдено</p>
                </div>
            ) : (
              <div className="space-y-4">
                {analysisData.positions_with_insights.map((position, index) => (
                  <div key={`${position.symbol}-${index}`} className="bg-slate-700/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        <span className="text-lg font-semibold text-white">{position.symbol}</span>
                        <span className="text-sm text-slate-400">{position.name}</span>
              </div>
                      <div className="text-sm text-slate-400">
                        Вес: {fmtWeight(position.weight_pct)}
              </div>
            </div>

                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-slate-400">Риск:</span> 
                        <span className="ml-1 text-white">{fmtRiskScore(position.risk_score_0_100)}/100</span>
                </div>
                      <div>
                        <span className="text-slate-400">Рост:</span> 
                        <span className="ml-1 text-white">{fmtPct(position.growth_forecast_pct)}</span>
              </div>
                      <div>
                        <span className="text-slate-400">Доходность:</span> 
                        <span className="ml-1 text-white">{fmtPct(position.expected_return_horizon_pct)}</span>
            </div>
          </div>

                    {position.insights && (
                      <div className="mt-4 pt-4 border-t border-slate-600">
                        <h4 className="text-sm font-medium text-slate-300 mb-2">AI Инсайт:</h4>
                        <p className="text-sm text-white mb-2">{position.insights.thesis}</p>
                        <div className="flex flex-wrap gap-2">
                          <span className="px-2 py-1 bg-blue-500/20 text-sm rounded-full text-blue-300">
                            {position.insights.action}
                          </span>
                          <span className="px-2 py-1 bg-green-500/20 text-sm rounded-full text-green-300">
                            {position.insights.signals.valuation}
                  </span>
              </div>
              </div>
            )}
                    
                    {!position.insights && (
                      <div className="mt-4 pt-4 border-t border-slate-600">
                        <span className="px-2 py-1 bg-orange-500/20 text-sm rounded-full text-orange-300">
                          Data gap
                      </span>
                    </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Техническая информация */}
          <div className="bg-slate-700/50 backdrop-blur-xl rounded-xl p-4 border border-slate-600/50 shadow-lg">
            <h4 className="text-sm font-medium text-slate-300 mb-4">Техническая информация</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-slate-400">
              <div>
                <p><span className="text-slate-300">Модель:</span> {analysisData.model}</p>
                {escalationRate !== null && escalationRate >= 0 && (
                  <p><span className="text-orange-400">Escalation rate:</span> {fmtPct(escalationRate)}</p>
                )}
                <p><span className="text-slate-300">Временной горизонт:</span> {params.horizon_months} мес.</p>
          </div>
              <div>
                <p><span className="text-slate-300">Риск-профиль:</span> {params.risk_profile}</p>
                <p><span className="text-slate-300">Дата анализа:</span> {analysisData.prepared_data.summary.as_of}</p>
              </div>
              <div>
                <p><span className="text-slate-300">Статус:</span> <span className="text-emerald-400">✓ Активно</span></p>
                <p><span className="text-slate-300">Время генерации:</span> ~2.3с</p>
            </div>
          </div>
        </div>
        </>
      ) : null}
    </div>
  );
}
