import React from 'react';
import { useStrategyStore } from '../../store/strategy';
import { StrategyKey } from '../../types/strategy';
import { fmtCurrency } from '../../lib/format';

// Strategy selector component for Dashboard
export function StrategySelector() {
  const { current, setKey, setMonthlyContribution } = useStrategyStore();

  const strategyOptions: { key: StrategyKey; label: string }[] = [
    { key: 'conservative', label: 'Conservative' },
    { key: 'balanced', label: 'Balanced' },
    { key: 'aggressive', label: 'Aggressive' }
  ];

  const handleContributionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    // Remove leading zeros and ensure non-negative
    const numValue = value === '' ? 0 : Math.max(0, parseInt(value, 10) || 0);
    setMonthlyContribution(numValue);
  };

  const handleContributionBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const value = e.target.value;
    // Trim leading zeros on blur
    const numValue = value === '' ? 0 : Math.max(0, parseInt(value, 10) || 0);
    setMonthlyContribution(numValue);
  };

  const [isExpanded, setIsExpanded] = React.useState(false);

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Strategy</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-slate-400 hover:text-white transition-colors"
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>
      

      {isExpanded && (
        <div className="space-y-4">
        {/* Strategy Selection */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Investment Strategy
          </label>
          <select
            value={current.key}
            onChange={(e) => setKey(e.target.value as StrategyKey)}
            className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
          >
            {strategyOptions.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Monthly Contribution */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Monthly Contribution
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              step="50"
              inputMode="numeric"
              value={current.monthlyContribution || ''}
              onChange={handleContributionChange}
              onBlur={handleContributionBlur}
              className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-right"
              placeholder="0"
            />
          </div>
        </div>

        {/* Strategy Info */}
        <div className="bg-slate-700/30 rounded-lg p-3">
          <div className="text-sm text-slate-300 space-y-1">
            <div className="flex justify-between">
              <span>Expected Return:</span>
              <span className="text-green-400">
                {(current.expectedReturnAnnual * 100).toFixed(1)}% annually
              </span>
            </div>
            <div className="flex justify-between">
              <span>Volatility:</span>
              <span className="text-yellow-400">
                {(current.volatilityAnnual * 100).toFixed(1)}% annually
              </span>
            </div>
            {current.monthlyContribution > 0 && (
              <div className="flex justify-between">
                <span>Monthly Contribution:</span>
                <span className="text-blue-400">
                  {fmtCurrency(current.monthlyContribution, 'USD')}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Helper Text */}
        <div className="text-xs text-slate-400">
          Ежемесячный взнос учитывается в прогнозе стратегии.
        </div>
        </div>
      )}
    </div>
  );
}
