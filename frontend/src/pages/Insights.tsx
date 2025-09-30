import { useState } from 'react';
import { useAuthStore } from '../store/auth';
import { apiFetch } from '../lib/api';

interface PortfolioAssessment {
  status: string;
  model: string;
  snapshot: {
    total_value: number;
    hhi: number;
    top_concentration_pct: number;
    missing_prices: string[];
  };
  ai: {
    rating: {
      score: number;
      label: string;
      risk_level: string;
    };
    overview: {
      headline: string;
      tags?: string[];
      key_strengths?: string[];
      key_concerns?: string[];
    };
    categories: Array<{
      name: string;
      score: number;
      note?: string;
      trend?: string;
    }>;
    insights: string[];
    risks: Array<{
      item: string;
      severity: string;
      mitigation?: string;
      impact?: string;
    }>;
    performance: {
      since_buy_pl_pct?: number;
      comment?: string;
      win_rate_pct?: number;
      avg_position_return?: number;
      volatility_assessment?: string;
    };
    diversification: {
      score: number;
      concentration_risk: string;
      sector_diversity?: string;
      recommendations?: string[];
    };
    actions: Array<{
      title: string;
      rationale: string;
      expected_impact?: string;
      priority: number;
      timeframe?: string;
    }>;
    summary_markdown: string;
  };
}

export default function Insights() {
  const { user_id } = useAuthStore();
  const [assessment, setAssessment] = useState<PortfolioAssessment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
  const [language, setLanguage] = useState('ru');

  const runAssessment = async () => {
    if (!user_id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiFetch(`/ai/portfolio/assess?user_id=${user_id}&model=${selectedModel}&language=${language}`, {
        method: 'POST'
      });
      const data = await response.json();
      setAssessment(data);
    } catch (err: any) {
      setError(err.message || 'Ошибка при анализе портфеля');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high': return 'text-red-500';
      case 'medium': return 'text-yellow-500';
      case 'low': return 'text-green-500';
      default: return 'text-gray-500';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-green-500';
    if (score >= 5) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel.toLowerCase()) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTimeframeColor = (timeframe?: string) => {
    switch (timeframe) {
      case 'immediate': return 'bg-red-100 text-red-800';
      case 'short_term': return 'bg-orange-100 text-orange-800';
      case 'medium_term': return 'bg-blue-100 text-blue-800';
      case 'long_term': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
            🤖 AI Анализ Портфеля
          </h1>
          <p className="text-slate-400 mt-2">Профессиональный анализ рисков, диверсификации и производительности</p>
        </div>
        <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-400">
          <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
          <span>AI Powered</span>
        </div>
      </div>
      
      {/* Controls */}
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <div className="flex flex-wrap gap-6 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-slate-300 mb-2">Модель AI</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
            >
              <option value="gpt-4o-mini">GPT-4o Mini</option>
              <option value="gpt-4o">GPT-4o</option>
            </select>
          </div>
          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium text-slate-300 mb-2">Язык</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
            >
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </div>
          <button
            onClick={runAssessment}
            disabled={loading || !user_id}
            className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-purple-500/25 font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {loading ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Анализирую...</span>
              </div>
            ) : (
              'Запустить анализ'
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 p-4 bg-gradient-to-r from-red-900/20 to-red-800/20 border border-red-500/30 rounded-lg backdrop-blur-sm">
            <div className="flex items-center space-x-3">
              <div className="w-6 h-6 bg-red-500/20 rounded-full flex items-center justify-center">
                <span className="text-red-400 text-sm">!</span>
              </div>
              <p className="text-red-400 font-medium">{error}</p>
            </div>
          </div>
        )}
      </div>

      {assessment && (
        <div className="space-y-8">
          {/* Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Общая оценка</h3>
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-sm font-bold">AI</span>
                </div>
              </div>
              <div className="text-center">
                <div className={`text-4xl font-bold mb-2 ${getScoreColor(assessment.ai.rating.score)}`}>
                  {assessment.ai.rating.score.toFixed(1)}/10
                </div>
                <div className="text-sm text-slate-400 mb-3">{assessment.ai.rating.label}</div>
                <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${getRiskLevelColor(assessment.ai.rating.risk_level)}`}>
                  Риск: {assessment.ai.rating.risk_level}
                </span>
              </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Производительность</h3>
                <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-green-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-sm">📈</span>
                </div>
              </div>
              <div className="text-center">
                <div className={`text-3xl font-bold mb-2 ${assessment.ai.performance.since_buy_pl_pct && assessment.ai.performance.since_buy_pl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {assessment.ai.performance.since_buy_pl_pct ? `${assessment.ai.performance.since_buy_pl_pct.toFixed(1)}%` : '—'}
                </div>
                <div className="text-sm text-slate-400 mb-2">
                  {assessment.ai.performance.comment || 'Нет данных о производительности'}
                </div>
                {assessment.ai.performance.win_rate_pct && (
                  <div className="text-xs text-slate-500">
                    Win Rate: {assessment.ai.performance.win_rate_pct.toFixed(1)}%
                  </div>
                )}
              </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Диверсификация</h3>
                <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-sm">⚖️</span>
                </div>
              </div>
              <div className="text-center">
                <div className={`text-3xl font-bold mb-2 ${getScoreColor(assessment.ai.diversification.score)}`}>
                  {assessment.ai.diversification.score.toFixed(1)}/10
                </div>
                <div className="text-sm text-slate-400 mb-2">
                  Концентрация: {assessment.ai.diversification.concentration_risk}
                </div>
                {assessment.ai.diversification.sector_diversity && (
                  <div className="text-xs text-slate-500">
                    Секторы: {assessment.ai.diversification.sector_diversity}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Headline and Tags */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <h2 className="text-xl font-semibold text-white mb-6">{assessment.ai.overview.headline}</h2>
            {assessment.ai.overview.tags && (
              <div className="flex flex-wrap gap-3 mb-6">
                {assessment.ai.overview.tags.map((tag, index) => (
                  <span key={index} className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-blue-100 rounded-full text-sm font-medium shadow-lg">
                    {tag}
                  </span>
                ))}
              </div>
            )}
            {assessment.ai.overview.key_strengths && (
              <div className="mb-6">
                <h4 className="font-medium text-green-400 mb-3 flex items-center">
                  <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                  Сильные стороны:
                </h4>
                <ul className="space-y-2">
                  {assessment.ai.overview.key_strengths.map((strength, index) => (
                    <li key={index} className="text-sm text-slate-300 flex items-start">
                      <span className="text-green-400 mr-2">✓</span>
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {assessment.ai.overview.key_concerns && (
              <div>
                <h4 className="font-medium text-red-400 mb-3 flex items-center">
                  <span className="w-2 h-2 bg-red-400 rounded-full mr-2"></span>
                  Области для улучшения:
                </h4>
                <ul className="space-y-2">
                  {assessment.ai.overview.key_concerns.map((concern, index) => (
                    <li key={index} className="text-sm text-slate-300 flex items-start">
                      <span className="text-red-400 mr-2">⚠</span>
                      {concern}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Categories and Risks */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
              <h3 className="text-lg font-semibold text-white mb-6">Категории оценки</h3>
              <div className="space-y-4">
                {assessment.ai.categories.map((category, index) => (
                  <div key={index} className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium text-white">{category.name}</span>
                      <span className={`text-lg font-bold ${getScoreColor(category.score)}`}>
                        {category.score.toFixed(1)}/10
                      </span>
                    </div>
                    {category.note && (
                      <p className="text-sm text-slate-400 mb-2">{category.note}</p>
                    )}
                    {category.trend && (
                      <span className="text-xs text-slate-500 bg-slate-600/50 px-2 py-1 rounded">
                        Тренд: {category.trend}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
              <h3 className="text-lg font-semibold text-white mb-6">Анализ рисков</h3>
              <div className="space-y-4">
                {assessment.ai.risks.map((risk, index) => (
                  <div key={index} className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`font-medium ${getSeverityColor(risk.severity)}`}>
                        ● {risk.severity.toUpperCase()}
                      </span>
                      {risk.impact && (
                        <span className="text-xs text-slate-500 bg-slate-600/50 px-2 py-1 rounded">
                          Impact: {risk.impact}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-white mb-2">{risk.item}</p>
                    {risk.mitigation && (
                      <p className="text-xs text-slate-400 bg-slate-600/30 p-2 rounded">
                        💡 {risk.mitigation}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Insights */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <h3 className="text-lg font-semibold text-white mb-6">Ключевые инсайты</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {assessment.ai.insights.map((insight, index) => (
                <div key={index} className="p-4 bg-gradient-to-r from-blue-900/20 to-purple-900/20 rounded-lg border border-blue-500/30 hover:border-blue-400/50 transition-all duration-200">
                  <p className="text-sm text-slate-300 leading-relaxed">{insight}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Action Plan */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <h3 className="text-lg font-semibold text-white mb-6">План действий</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-700/50">
                <thead className="bg-slate-700/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">#</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Действие</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Обоснование</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Приоритет</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase tracking-wider">Срок</th>
                  </tr>
                </thead>
                <tbody className="bg-slate-800/30 divide-y divide-slate-700/30">
                  {assessment.ai.actions.map((action, index) => (
                    <tr key={index} className="hover:bg-slate-700/20 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                        {index + 1}
                      </td>
                      <td className="px-6 py-4 text-sm text-white font-medium">{action.title}</td>
                      <td className="px-6 py-4 text-sm text-slate-400">{action.rationale}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                          action.priority >= 4 ? 'bg-red-900/50 text-red-300 border border-red-500/30' :
                          action.priority >= 3 ? 'bg-yellow-900/50 text-yellow-300 border border-yellow-500/30' :
                          'bg-green-900/50 text-green-300 border border-green-500/30'
                        }`}>
                          {action.priority}/5
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {action.timeframe && (
                          <span className={`px-3 py-1 text-xs font-medium rounded-full ${getTimeframeColor(action.timeframe)}`}>
                            {action.timeframe}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Summary */}
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            <h3 className="text-lg font-semibold text-white mb-6">Резюме</h3>
            <div className="prose max-w-none">
              <p className="text-slate-300 whitespace-pre-line leading-relaxed">{assessment.ai.summary_markdown}</p>
            </div>
          </div>

          {/* Technical Info */}
          <div className="bg-slate-700/50 backdrop-blur-xl rounded-xl p-6 border border-slate-600/50 shadow-lg">
            <h4 className="text-sm font-medium text-slate-300 mb-4">Техническая информация</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-slate-400">
              <div>
                <p><span className="text-slate-300">Модель:</span> {assessment.model}</p>
                <p><span className="text-slate-300">Общая стоимость:</span> ${assessment.snapshot.total_value.toLocaleString()}</p>
              </div>
              <div>
                <p><span className="text-slate-300">Индекс концентрации (HHI):</span> {assessment.snapshot.hhi.toFixed(3)}</p>
                <p><span className="text-slate-300">Топ-3 позиции:</span> {assessment.snapshot.top_concentration_pct.toFixed(1)}%</p>
              </div>
              {assessment.snapshot.missing_prices.length > 0 && (
                <div className="md:col-span-2">
                  <p><span className="text-slate-300">Отсутствующие цены:</span> {assessment.snapshot.missing_prices.join(', ')}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
