import { useStrategyStore } from '../../store/strategy';

interface StrategyGoalProps {
  currentValue: number;
}

export function StrategyGoal({ currentValue }: StrategyGoalProps) {
  const { current: strategy } = useStrategyStore();

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Calculate 1-year target based on strategy
  const monthsElapsed = 12; // Assume 1 year elapsed
  const monthlyReturn = strategy.expectedReturnAnnual / 12;
  const compoundGrowth = Math.pow(1 + monthlyReturn, monthsElapsed);
  const contributionGrowth = strategy.monthlyContribution * monthsElapsed;
  const targetValue = (currentValue * compoundGrowth) + contributionGrowth;

  const progressToGoal = currentValue / targetValue;
  const isAheadOfPlan = currentValue > targetValue;

  return (
    <div className="bg-slate-700/30 rounded-lg p-4">
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm text-slate-300">Goal Progress</span>
          <span className={`text-sm font-medium ${isAheadOfPlan ? 'text-green-400' : 'text-yellow-400'}`}>
            {isAheadOfPlan ? '🚀 Ahead of Plan' : '📊 On Track'}
          </span>
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-slate-600/50 rounded-full h-3">
          <div 
            className={`h-3 rounded-full ${isAheadOfPlan ? 'bg-green-500' : 'bg-blue-500'} transition-all duration-500`}
            style={{ width: `${Math.min(progressToGoal * 100, 100)}%` }}
          ></div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-slate-400">Current</div>
            <div className="text-white font-medium">{formatCurrency(currentValue)}</div>
          </div>
          <div>
            <div className="text-slate-400">1-Year Target</div>
            <div className="text-blue-300 font-medium">{formatCurrency(targetValue)}</div>
          </div>
        </div>

        {strategy.monthlyContribution > 0 && (
          <div className="pt-2 border-t border-slate-600/50">
            <div className="flex justify-between text-xs text-slate-400">
              <span>Monthly Contribution:</span>
              <span className="text-blue-400">{formatCurrency(strategy.monthlyContribution)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
