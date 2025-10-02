import React from 'react';
import { IndustryGroup, GrowthBucket, RiskBucket } from './types';
import { fmtNum, fmtPct, fmtRiskScore } from '../../utils/number';

interface GroupVisualizationProps<T = IndustryGroup | GrowthBucket | RiskBucket> {
  title: string;
  type: 'industry' | 'growth' | 'risk';
  data: T[];
  totalWeight: number;
}

export const GroupVisualization: React.FC<GroupVisualizationProps> = ({
  title,
  data,
  totalWeight
}) => {
  const normalizeWeight = (weight: number) => {
    if (totalWeight === 0) return 0;
    return Math.round((weight / totalWeight) * 100 * 100) / 100;
  };

  const getBarColor = (category: string) => {
    switch (category.toLowerCase()) {
      case 'high growth':
      case 'high':
        return 'bg-gradient-to-r from-emerald-500 to-green-600';
      case 'mid growth':
      case 'moderate':
        return 'bg-gradient-to-r from-yellow-500 to-orange-500';
      case 'low/value':
      case 'low':
        return 'bg-gradient-to-r from-blue-500 to-purple-500';
      default:
        return 'bg-gradient-to-r from-slate-500 to-slate-600';
    }
  };

  // Сортируем данные по весу
  const sortedData = [...data].sort((a, b) => b.weight_pct - a.weight_pct);

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <h3 className="text-lg font-semibold text-white mb-6">{title}</h3>
      
      {data.length === 0 ? (
        <div className="text-center text-slate-400 py-8">
          <div className="text-2xl mb-2">📊</div>
          <p>Недостаточно данных для группировки</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Список групп */}
          <div className="space-y-3">
            {sortedData.map((item, index) => {
              const normalizedWeight = normalizeWeight(item.weight_pct);
              const topPositions = 'positions' in item ? item.positions.slice(0, 3) : [];
              const displayName = 'name' in item ? item.name : (item as any).category;
              
              return (
                <div key={index} className="group">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-white">
                      {displayName}
                    </span>
                    <span className="text-sm text-slate-300 font-mono">
                      {normalizedWeight}%
                    </span>
                  </div>
                  
                  {/* Прогресс бар */}
                  <div className="relative h-8 bg-slate-700/50 rounded-lg overflow-hidden">
                    <div 
                      className={`absolute top-0 left-0 h-full ${getBarColor(displayName)} transition-all duration-1000 ease-out`}
                      style={{ width: `${normalizedWeight}%` }}
                    />
                    <div className="absolute inset-0 flex items-center px-3">
                      <span className="text-xs text-white font-medium">
                        {fmtPct(normalizedWeight)}
                      </span>
                    </div>
                  </div>

                  {/* Детали при наведении */}
                  <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <div className="text-xs text-slate-400 space-y-1">
                      {'avg_expected_return_pct' in item && item.avg_expected_return_pct !== undefined && (
                        <div>Ожидаемая доходность: {fmtPct(item.avg_expected_return_pct)}</div>
                      )}
                      {'avg_risk_score' in item && item.avg_risk_score !== undefined && (
                        <div>Риск: {fmtRiskScore(item.avg_risk_score)}/100</div>
                      )}
                      {topPositions.length > 0 && (
                        <div>Топ позиции: {topPositions.join(', ')}</div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Общая информация */}
          <div className="mt-6 p-4 bg-slate-700/30 rounded-lg">
            <div className="text-sm text-slate-300">
              <div className="flex justify-between items-center mb-2">
                <span>Общий вес:</span>
                <span className="font-mono">{fmtPct(totalWeight)}</span>
              </div>
              {totalWeight < 98 || totalWeight > 102 ? (
                <div className="text-xs text-yellow-400">
                  ⚠️ Веса отклоняются от 100% (ошибка {fmtNum(totalWeight - 100, 1)}%)
                </div>
              ) : (
                <div className="text-xs text-emerald-400">
                  ✅ Веса в пределах нормы
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
