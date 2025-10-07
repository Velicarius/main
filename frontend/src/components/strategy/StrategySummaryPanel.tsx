import React from 'react';
import { fmtCurrency } from '../../lib/format';
import { StrategyParams } from '../../types/strategy';

export interface StrategySummaryPanelProps {
  currentValue: number;
  strategy: StrategyParams;
  isExpanded: boolean;
  progressToGoal?: number;
}

export const StrategySummaryPanel: React.FC<StrategySummaryPanelProps> = ({
  currentValue,
  strategy,
  isExpanded,
  progressToGoal
}) => {
  // Calculate time to goal
  const timeToGoal = strategy.targetDate
    ? Math.ceil((new Date(strategy.targetDate).getTime() - new Date().getTime()) / (30 * 24 * 60 * 60 * 1000))
    : 0;

  // Calculate amount needed to grow
  const amountToGrow = strategy.targetGoalValue ? strategy.targetGoalValue - currentValue : 0;
  const growthPercentage = currentValue > 0 ? (amountToGrow / currentValue) * 100 : 0;

  return (
    <>
      {/* Main Summary Card */}
      <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-xl p-6 mb-6">
        <div className="grid grid-cols-3 gap-6 text-center">
          <div>
            <div className="text-sm text-slate-400 mb-1">Current Value</div>
            <div className="text-2xl font-bold text-white">{fmtCurrency(currentValue, 'USD')}</div>
          </div>
          <div>
            <div className="text-sm text-slate-400 mb-1">Target Value</div>
            <div className="text-2xl font-bold text-blue-400">
              {strategy.targetGoalValue ? fmtCurrency(strategy.targetGoalValue, 'USD') : 'Not Set'}
            </div>
          </div>
          <div>
            <div className="text-sm text-slate-400 mb-1">Time to Goal</div>
            <div className="text-2xl font-bold text-purple-400">
              {timeToGoal > 0 ? `${timeToGoal} months` : 'Not Set'}
            </div>
          </div>
        </div>

        {/* Growth Summary */}
        {strategy.targetGoalValue && amountToGrow > 0 && (
          <div className="mt-4 text-center">
            <div className="text-sm text-slate-400">
              Need to grow: <span className="text-green-400 font-semibold">{fmtCurrency(amountToGrow, 'USD')}</span>
              <span className="text-yellow-400"> ({growthPercentage.toFixed(1)}%)</span>
              {strategy.targetDate && (
                <span> by {new Date(strategy.targetDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Compact Summary (when collapsed) */}
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
                {strategy.riskLevel || 'Manual'}
              </div>
              <div className="text-xs text-slate-400">Risk Level</div>
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

          {/* Progress Indicator */}
          {progressToGoal !== undefined && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Goal Progress</span>
                <span className="text-blue-400">{progressToGoal.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-600/50 rounded-full h-1">
                <div
                  className="h-1 rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
                  style={{ width: `${Math.min(progressToGoal, 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
};
