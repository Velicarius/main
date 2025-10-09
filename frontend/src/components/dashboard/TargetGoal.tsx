interface TargetGoalProps {
  targetValue: number;
  targetDate: string;
  currentValue: number;
}

export function TargetGoal({ targetValue, targetDate, currentValue }: TargetGoalProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long',
      day: 'numeric'
    });
  };

  const progressPercentage = Math.min((currentValue / targetValue) * 100, 100);
  const remainingAmount = Math.max(targetValue - currentValue, 0);

  // Calculate years remaining
  const currentDate = new Date();
  const targetDateObj = new Date(targetDate);
  const yearsRemaining = Math.max((targetDateObj.getTime() - currentDate.getTime()) / (1000 * 60 * 60 * 24 * 365), 0);

  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="text-2xl font-bold text-blue-400 mb-1">
          {formatCurrency(targetValue)}
        </div>
        <div className="text-sm text-slate-400">
          Target by {formatDate(targetDate)}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-slate-400">Progress</span>
          <span className="text-white font-medium">{progressPercentage.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-slate-600/50 rounded-full h-3">
          <div 
            className="h-3 rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-slate-400">Current Value</div>
          <div className="text-white font-medium">{formatCurrency(currentValue)}</div>
        </div>
        <div>
          <div className="text-slate-400">Remaining</div>
          <div className="text-blue-300 font-medium">{formatCurrency(remainingAmount)}</div>
        </div>
      </div>

      {yearsRemaining > 0 && (
        <div className="text-center pt-2 border-t border-slate-600/50">
          <div className="text-xs text-slate-400">
            {yearsRemaining.toFixed(1)} years remaining
          </div>
        </div>
      )}
    </div>
  );
}






