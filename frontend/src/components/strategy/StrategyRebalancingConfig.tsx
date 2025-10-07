import React from 'react';
import { RebalancingFrequency } from '../../types/strategy';

const REBALANCING_OPTIONS: { value: RebalancingFrequency; label: string }[] = [
  { value: 'none', label: 'No Rebalancing' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'semiannual', label: 'Semiannual' },
  { value: 'yearly', label: 'Yearly' }
];

export interface StrategyRebalancingConfigProps {
  frequency: RebalancingFrequency;
  onChange: (frequency: RebalancingFrequency) => void;
}

export const StrategyRebalancingConfig: React.FC<StrategyRebalancingConfigProps> = ({
  frequency,
  onChange
}) => {
  return (
    <div>
      <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center">
        <span className="mr-2">🔄</span>
        Rebalancing
      </h4>
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Frequency
          </label>
          <select
            value={frequency || 'quarterly'}
            onChange={(e) => onChange(e.target.value as RebalancingFrequency)}
            className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
          >
            {REBALANCING_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-slate-500 mt-1">
            Portfolio rebalancing frequency to maintain target allocation
          </p>
        </div>
      </div>
    </div>
  );
};
