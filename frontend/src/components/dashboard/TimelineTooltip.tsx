import React from 'react';

export interface TimelineTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
  formatCurrency: (value: number) => string;
  formatDate: (dateStr: string) => string;
  // Additional metrics for rich tooltip
  firstPointValue?: number;
  targetValue?: number;
  currentTotalValue?: number;
}

export const TimelineTooltip: React.FC<TimelineTooltipProps> = ({
  active,
  payload,
  label,
  formatCurrency,
  formatDate,
  firstPointValue,
  targetValue
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  // Get the actual portfolio value from the payload
  const actualEntry = payload.find((p: any) => p.dataKey === 'actual');
  const actualValue = actualEntry?.value;

  // Calculate P&L metrics if we have both values
  let periodPnL = 0;
  let periodPnLPercent = 0;
  if (actualValue && firstPointValue) {
    periodPnL = actualValue - firstPointValue;
    periodPnLPercent = firstPointValue > 0 ? (periodPnL / firstPointValue) * 100 : 0;
  }

  // Calculate delta to target
  const deltaToTarget = targetValue && actualValue ? targetValue - actualValue : null;

  return (
    <div className="bg-slate-800/95 border border-slate-600 rounded-lg p-4 shadow-xl backdrop-blur-sm min-w-[250px]">
      {/* Date */}
      <p className="text-white font-semibold mb-3 pb-2 border-b border-slate-600">
        {label ? formatDate(label) : ''}
      </p>

      {/* Portfolio Value */}
      {actualValue && (
        <div className="mb-2">
          <p className="text-xs text-slate-400 mb-0.5">Portfolio Value</p>
          <p className="text-lg font-bold text-blue-400">
            {formatCurrency(actualValue)}
          </p>
        </div>
      )}

      {/* Period P&L */}
      {firstPointValue && actualValue && (
        <div className="mb-2">
          <p className="text-xs text-slate-400 mb-0.5">Period P&L</p>
          <p className={`text-sm font-semibold ${periodPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {periodPnL >= 0 ? '+' : ''}{formatCurrency(periodPnL)}
            <span className="text-xs ml-1">
              ({periodPnL >= 0 ? '+' : ''}{periodPnLPercent.toFixed(2)}%)
            </span>
          </p>
        </div>
      )}

      {/* Target Value */}
      {targetValue && (
        <div className="mb-2">
          <p className="text-xs text-slate-400 mb-0.5">Target Value</p>
          <p className="text-sm font-medium text-emerald-400">
            {formatCurrency(targetValue)}
          </p>
        </div>
      )}

      {/* Delta to Target */}
      {deltaToTarget !== null && (
        <div>
          <p className="text-xs text-slate-400 mb-0.5">Delta to Target</p>
          <p className={`text-sm font-semibold ${deltaToTarget <= 0 ? 'text-green-400' : 'text-amber-400'}`}>
            {deltaToTarget > 0 ? '+' : ''}{formatCurrency(deltaToTarget)}
          </p>
        </div>
      )}
    </div>
  );
};
