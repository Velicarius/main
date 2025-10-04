import React from 'react';
import { useStrategyStore } from '../../store/strategy';
import { StrategyKey } from '../../types/strategy';
import { fmtCurrency } from '../../lib/format';
import { TargetGoal } from '../dashboard/TargetGoal';
import { RiskProfile } from '../dashboard/RiskProfile';
import { TargetReturn } from '../dashboard/TargetReturn';
import { AssetAllocationChart } from '../dashboard/AssetAllocationChart';

interface StrategySelectorProps {
  currentValue?: number; // Portfolio current value for calculations
}

export function StrategySelector({ currentValue = 0 }: StrategySelectorProps) {
  const { current: strategy, setKey } = useStrategyStore();

  const strategyOptions: { key: StrategyKey; label: string }[] = [
    { key: 'conservative', label: 'Conservative' },
    { key: 'balanced', label: 'Balanced' },
    { key: 'aggressive', label: 'Aggressive' }
  ];

  const handleContributionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const numValue = value === '' ? 0 : Math.max(0, parseInt(value, 10) || 0);
    strategy.monthlyContribution = numValue;
  };

  const handleContributionBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const numValue = value === '' ? 0 : Math.max(0, parseInt(value, 10) || 0);
    strategy.monthlyContribution = numValue;
  };

  const [isExpanded, setIsExpanded] = React.useState(false);

  // Calculate years remaining
  const currentDate = new Date();
  const targetDateObj = strategy.targetDate ? new Date(strategy.targetDate) : new Date('2027-12-31');
  const yearsRemaining = Math.max((targetDateObj.getTime() - currentDate.getTime()) / (1000 * 60 * 60 * 24 * 365), 0);

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">View Strategy</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-slate-400 hover:text-white transition-colors"
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {/* Compact Strategy Summary */}
      {!isExpanded && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-slate-700/30 rounded-lg">
              <div className="text-lg font-bold text-blue-400">
                {strategy.targetGoalValue ? fmtCurrency(strategy.targetGoalValue, 'USD') : 'N/A'}
              </div>
              <div className="text-xs text-slate-400">Target Goal</div>
            </div>
            <div className="text-center p-3 bg-slate-700/30 rounded-lg">
              <div className="text-lg font-bold text-green-400 capitalize">
                {strategy.key}
              </div>
              <div className="text-xs text-slate-400">Risk Profile</div>
            </div>
          </div>
          
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Expected Return:</span>
            <span className="text-green-400">
              {(strategy.expectedReturnAnnual * 100).toFixed(1)}% annually
            </span>
          </div>
          
          {strategy.monthlyContribution > 0 && (
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Monthly Contribution:</span>
              <span className="text-blue-400">{fmtCurrency(strategy.monthlyContribution, 'USD')}</span>
            </div>
          )}
        </div>
      )}

      {/* Expanded Strategy Details */}
      {isExpanded && (
        <div className="space-y-6">
          {/* Strategy Selection */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Investment Strategy
            </label>
            <select
              value={strategy.key}
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

          {/* Goal */}
          {strategy.targetGoalValue && strategy.targetDate && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-3">🎯 Target Goal</h4>
              <TargetGoal
                targetValue={strategy.targetGoalValue}
                targetDate={strategy.targetDate}
                currentValue={currentValue}
              />
            </div>
          )}

          {/* Risk & Return */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-3">⚡ Risk & Return</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <RiskProfile
                riskLevel={strategy.key}
                maxDrawdown={strategy.maxDrawdown || 0}
                volatility={strategy.volatilityAnnual}
              />
              <TargetReturn
                expectedReturnAnnual={strategy.expectedReturnAnnual}
                currentValue={currentValue}
                monthlyContribution={strategy.monthlyContribution}
                yearsRemaining={yearsRemaining}
              />
            </div>
          </div>

          {/* Asset Allocation */}
          {strategy.assetAllocation && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-3">📊 Asset Allocation</h4>
              <AssetAllocationChart allocation={strategy.assetAllocation} />
            </div>
          )}

          {/* Contributions */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-3">💰 Contributions</h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Monthly Contribution
                </label>
                <input
                  type="number"
                  min="0"
                  step="50"
                  inputMode="numeric"
                  value={strategy.monthlyContribution || ''}
                  onChange={handleContributionChange}
                  onBlur={handleContributionBlur}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-right"
                  placeholder="0"
                />
              </div>
              <div className="text-xs text-slate-400">
                Monthly contribution is included in strategy forecasts and contributes to goal achievement.
              </div>
            </div>
          </div>

          {/* Rebalancing */}
          {strategy.rebalancingFrequency && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-3">🔄 Rebalancing</h4>
              <div className="bg-slate-700/30 rounded-lg p-3">
                <div className="flex justify-between">
                  <span className="text-sm text-slate-400">Frequency:</span>
                  <span className="text-white font-medium capitalize">{strategy.rebalancingFrequency}</span>
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Portfolio weights will be adjusted to maintain target allocation
                </div>
              </div>
            </div>
          )}

          {/* Constraints */}
          {strategy.constraints && Object.keys(strategy.constraints).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-3">🚧 Investment Rules</h4>
              <div className="bg-slate-700/30 rounded-lg p-3">
                <ul className="space-y-1">
                  {Object.entries(strategy.constraints).map(([key, value]) => (
                    <li key={key} className="flex items-start space-x-2 text-sm">
                      <span className="text-slate-400 mt-1">•</span>
                      <span className="text-slate-300">{key}: {value}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}