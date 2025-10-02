import React, { useState } from 'react';
import { PositionAnalysis, getRiskCategory, getGrowthCategory } from './types';
import { fmtPct, fmtWeight, fmtRiskScore } from '../../utils/number';

interface PositionInsightCardProps {
  analysis: PositionAnalysis;
  isMobile?: boolean;
}

export const PositionInsightCard: React.FC<PositionInsightCardProps> = ({
  analysis,
  isMobile = false
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getActionColor = (action: string) => {
    switch (action) {
      case 'Buy':
      case 'Add':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'Hold':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'Trim':
      case 'Sell':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'Hedge':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getValuationIcon = (valuation: string) => {
    switch (valuation) {
      case 'cheap':
        return '📉';
      case 'fair':
        return '➡️';
      case 'expensive':
        return '📈';
      default:
        return '❓';
    }
  };

  const getMomentumIcon = (momentum: string) => {
    switch (momentum) {
      case 'up':
        return '🚀';
      case 'flat':
        return '➡️';
      case 'down':
        return '📉';
      default:
        return '❓';
    }
  };

  const getQualityIcon = (quality: string) => {
    switch (quality) {
      case 'high':
        return '⭐';
      case 'medium':
        return '🔹';
      case 'low':
        return '🔸';
      default:
        return '❓';
    }
  };

  const riskCategory = getRiskCategory(analysis.risk_score);
  const growthCategory = getGrowthCategory(analysis.expected_return_pct);

  const BadgeBadge = ({ label, variant, icon }: { label: string; variant: string; icon?: string }) => (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${variant}`}>
      {icon && <span className="mr-1">{icon}</span>}
      {label}
    </span>
  );

  if (isMobile) {
    // Мобильная версия - dropdown
    return (
      <details className="group">
        <summary className="cursor-pointer flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors">
          <span className="font-medium text-white">{analysis.symbol}</span>
          <div className="flex items-center space-x-2">
            <BadgeBadge 
              label={riskCategory} 
              variant={riskCategory === 'High' ? 'bg-red-500/20 text-red-400 border-red-500/30' : 
                      riskCategory === 'Moderate' ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' : 
                      'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'} 
            />
            <svg className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" 
                 fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </summary>
        
        <div className="mt-3 p-4 bg-slate-700/50 rounded-lg space-y-4">
          {/* Thesis */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-2">Идея</h4>
            <p className="text-sm text-slate-400 leading-relaxed">{analysis.thesis}</p>
          </div>

          {/* Signals */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-2">Сигналы</h4>
            <div className="flex flex-wrap gap-2">
              <BadgeBadge 
                label={analysis.valuation} 
                variant="bg-blue-500/20 text-blue-400 border-blue-500/30"
                icon={getValuationIcon(analysis.valuation)}
              />
              <BadgeBadge 
                label={analysis.momentum} 
                variant="bg-purple-500/20 text-purple-400 border-purple-500/30"
                icon={getMomentumIcon(analysis.momentum)}
              />
              <BadgeBadge 
                label={analysis.quality} 
                variant="bg-amber-500/20 text-amber-400 border-amber-500/30"
                icon={getQualityIcon(analysis.quality)}
              />
            </div>
          </div>

          {/* Risks */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-2">Риски</h4>
            <ul className="space-y-1">
              {analysis.risks.map((risk, index) => (
                <li key={index} className="text-sm text-slate-400 flex items-start">
                  <span className="text-red-400 mr-2">⚠</span>
                  {risk}
                </li>
              ))}
            </ul>
          </div>

          {/* Action */}
          <div className="flex justify-between items-center pt-3 border-t border-slate-600/50">
            <div>
              <div className="text-sm text-slate-300">Рекомендация</div>
              <span className={`inline-flex px-3 py-1 rounded-full text-sm font-medium border ${getActionColor(analysis.action)}`}>
                {analysis.action}
              </span>
            </div>
            <div className="text-right text-xs text-slate-400">
              <div>Вес: {fmtWeight(analysis.weight_pct)}</div>
              {analysis.expected_return_pct !== undefined && (
                <div>Доходность: {fmtPct(analysis.expected_return_pct)}</div>
              )}
            </div>
          </div>
        </div>
      </details>
    );
  }

  // Десктопная версия - expandable row
  return (
    <div className="border border-slate-700/50 rounded-lg overflow-hidden">
      {/* Header row */}
      <div 
        className="p-4 cursor-pointer bg-slate-700/30 hover:bg-slate-700/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="font-medium text-white">{analysis.symbol}</span>
            <div className="flex items-center space-x-2">
              <BadgeBadge 
                label={riskCategory} 
                variant={riskCategory === 'High' ? 'bg-red-500/20 text-red-400 border-red-500/30' : 
                        riskCategory === 'Moderate' ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' : 
                        'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'} 
              />
              <BadgeBadge 
                label={growthCategory} 
                variant={growthCategory.includes('High') ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 
                        growthCategory.includes('Mid') ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' : 
                        'bg-blue-500/20 text-blue-400 border-blue-500/30'} 
              />
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-right text-sm">
              <div className="text-slate-300">
{fmtPct(analysis.expected_return_pct)}
              </div>
              <div className="text-xs text-slate-400">
{fmtWeight(analysis.weight_pct)} вес
              </div>
            </div>
            <svg className={`w-5 h-5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
                 fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-4 bg-slate-700/20 border-t border-slate-600/50 animate-in slide-in-from-top-2 duration-200">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left column */}
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-slate-300 mb-2">Инвестиционная идея</h4>
                <p className="text-sm text-slate-400 leading-relaxed">{analysis.thesis}</p>
              </div>

              <div>
                <h4 className="text-sm font-medium text-slate-300 mb-2">Рисковые факторы</h4>
                <ul className="space-y-2">
                  {analysis.risks.map((risk, index) => (
                    <li key={index} className="text-sm text-slate-400 flex items-start">
                      <span className="text-red-400 mr-2 mt-0.5">⚠</span>
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Right column */}
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-slate-300 mb-3">Сигналы</h4>
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-lg">{getValuationIcon(analysis.valuation)}</span>
                    <div>
                      <div className="text-sm text-slate-400">Оценка</div>
                      <div className="text-sm font-medium text-white">{analysis.valuation}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-lg">{getMomentumIcon(analysis.momentum)}</span>
                    <div>
                      <div className="text-sm text-slate-400">Момент</div>
                      <div className="text-sm font-medium text-white">{analysis.momentum}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-lg">{getQualityIcon(analysis.quality)}</span>
                    <div>
                      <div className="text-sm text-slate-400">Качество</div>
                      <div className="text-sm font-medium text-white">{analysis.quality}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center pt-3 border-t border-slate-600/50">
                <div>
                  <div className="text-sm text-slate-300 mb-2">Рекомендация</div>
                  <span className={`inline-flex px-3 py-1 rounded-full text-sm font-medium border ${getActionColor(analysis.action)}`}>
                    {analysis.action}
                  </span>
                </div>
                <div className="text-right text-xs text-slate-400">
                  {analysis.risk_score !== undefined && (
                    <div>Риск: {fmtRiskScore(analysis.risk_score)}/100</div>
                  )}
                  {analysis.volatility_pct !== undefined && (
                    <div>Волат.: {fmtPct(analysis.volatility_pct)}</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
