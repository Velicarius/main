import React from 'react';
import { fmtCurrency } from '../../lib/format';

export interface StrategyBasicFieldsProps {
  targetGoalValue: number;
  targetDate: string;
  monthlyContribution: number;
  currentValue: number;
  onChange: (field: any, value: any) => void;
}

export const StrategyBasicFields: React.FC<StrategyBasicFieldsProps> = ({
  targetGoalValue,
  targetDate,
  monthlyContribution,
  currentValue,
  onChange
}) => {
  const formatNumber = (num: number) => {
    if (!num) return '';
    return num.toLocaleString('en-US');
  };

  // Calculate helpers
  const amountToGrow = targetGoalValue ? targetGoalValue - currentValue : 0;
  const growthPercentage = currentValue > 0 ? (amountToGrow / currentValue) * 100 : 0;

  const timeToGoal = targetDate
    ? Math.ceil((new Date(targetDate).getTime() - new Date().getTime()) / (30 * 24 * 60 * 60 * 1000))
    : 0;

  return (
    <div className="space-y-6">
      {/* Target Goal Section */}
      <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-white flex items-center">
          <span className="mr-2">🎯</span>
          Target Goal
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Target Value
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
              <input
                type="text"
                inputMode="numeric"
                value={targetGoalValue ? formatNumber(targetGoalValue) : ''}
                onChange={(e) => {
                  const value = e.target.value.replace(/[^0-9]/g, '');
                  onChange('targetGoalValue', Number(value));
                }}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 pl-8 py-2.5 text-white focus:border-blue-500 focus:outline-none text-right"
                placeholder="80,000"
              />
            </div>
            {targetGoalValue && targetGoalValue < currentValue && (
              <p className="text-xs text-yellow-400 mt-1">
                Target is less than current value
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Target Date
            </label>
            <input
              type="date"
              value={targetDate || ''}
              onChange={(e) => onChange('targetDate', e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white focus:border-blue-500 focus:outline-none"
            />
            {targetDate && new Date(targetDate) < new Date() && (
              <p className="text-xs text-red-400 mt-1">
                Target date must be in the future
              </p>
            )}
          </div>
        </div>

        {/* Progress indicator */}
        {targetGoalValue && amountToGrow > 0 && (
          <div className="mt-4 text-sm text-slate-400">
            Need to grow: <span className="text-green-400 font-semibold">{fmtCurrency(amountToGrow, 'USD')}</span>
            <span className="text-yellow-400"> ({growthPercentage.toFixed(1)}%)</span>
            {targetDate && (
              <span> by {new Date(targetDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</span>
            )}
          </div>
        )}
      </div>

      {/* Monthly Contribution Section */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
        <h3 className="text-base font-semibold mb-3 text-white flex items-center">
          <span className="mr-2">💰</span>
          Contributions
        </h3>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Monthly Contribution
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
            <input
              type="text"
              inputMode="numeric"
              value={monthlyContribution ? formatNumber(monthlyContribution) : ''}
              onChange={(e) => {
                const value = e.target.value.replace(/[^0-9]/g, '');
                onChange('monthlyContribution', Number(value));
              }}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 pl-8 py-2.5 text-white focus:border-blue-500 focus:outline-none text-right"
              placeholder="1,000"
            />
          </div>
          {monthlyContribution > 0 && timeToGoal > 0 && (
            <div className="text-sm text-slate-400 mt-2">
              ${monthlyContribution}/month × {timeToGoal} months = {fmtCurrency(monthlyContribution * timeToGoal, 'USD')} total contribution
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
