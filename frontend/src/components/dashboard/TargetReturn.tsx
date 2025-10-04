interface TargetReturnProps {
  expectedReturnAnnual: number;
  currentValue: number;
  monthlyContribution: number;
  yearsRemaining: number;
}

export function TargetReturn({ 
  expectedReturnAnnual, 
  currentValue, 
  monthlyContribution, 
  yearsRemaining 
}: TargetReturnProps) {
  const formatPercent = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }).format(value);
  };

  // Calculate CAGR
  const contributionGrowth = monthlyContribution * 12 * yearsRemaining;
  const futureValue = currentValue * Math.pow(1 + expectedReturnAnnual, yearsRemaining) + contributionGrowth;
  const cagr = Math.pow((futureValue / currentValue), 1 / yearsRemaining) - 1;

  // Estimate actual performance vs target (simplified)
  const actualPerformance = Math.random() * (expectedReturnAnnual + 0.05); // Simulated for now
  const performanceProgress = Math.min((actualPerformance / expectedReturnAnnual) * 100, 120);

  return (
    <div className="space-y-3">
      {/* Expected Return */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-slate-400">Expected Return</span>
        <span className="text-green-400 font-medium">
          {formatPercent(expectedReturnAnnual)} annually
        </span>
      </div>

      {/* CAGR */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-slate-400">Target CAGR</span>
        <span className="text-blue-400 font-medium">
          {formatPercent(cagr)}
        </span>
      </div>

      {/* Performance Progress */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-slate-400">Actual vs Target</span>
          <span className={`font-medium ${
            performanceProgress >= 100 ? 'text-green-400' : 
            performanceProgress >= 80 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {performanceProgress.toFixed(0)}%
          </span>
        </div>
        <div className="w-full bg-slate-600/50 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-500 ${
              performanceProgress >= 100 ? 'bg-green-500' : 
              performanceProgress >= 80 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${Math.min(performanceProgress, 100)}%` }}
          />
        </div>
      </div>

      {/* Status */}
      <div className="text-center">
        <div className={`text-xs px-2 py-1 rounded-full ${
          performanceProgress >= 100 ? 'bg-green-500/20 text-green-400' : 
          performanceProgress >= 80 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {performanceProgress >= 100 ? '🎯 Exceeding Target' : 
           performanceProgress >= 80 ? '📈 On Track' : '📉 Below Target'}
        </div>
      </div>
    </div>
  );
}
