interface RiskProfileProps {
  riskLevel: string;
  maxDrawdown: number;
  volatility: number;
}

export function RiskProfile({ riskLevel, maxDrawdown, volatility }: RiskProfileProps) {
  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'conservative': return 'text-green-400 bg-green-500/20';
      case 'balanced': return 'text-yellow-400 bg-yellow-500/20';
      case 'aggrogressive': return 'text-red-400 bg-red-500/20';
      default: return 'text-blue-400 bg-blue-500/20';
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case 'conservative': return '🛡️';
      case 'balanced': return '⚖️';
      case 'aggrogressive': return '🚀';
      default: return '📊';
    }
  };

  return (
    <div className="space-y-3">
      {/* Risk Level */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{getRiskIcon(riskLevel)}</span>
          <span className="text-sm text-slate-400">Risk Level</span>
        </div>
        <div className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${getRiskColor(riskLevel)}`}>
          {riskLevel}
        </div>
      </div>

      {/* Risk Metrics */}
      <div className="grid grid-cols-1 gap-3">
        <div className="flex justify-between">
          <span className="text-sm text-slate-400">Max Drawdown</span>
          <span className="text-red-400 font-medium">{maxDrawdown}%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-slate-400">Volatility</span>
          <span className="text-yellow-400 font-medium">{(volatility * 100).toFixed(1)}%</span>
        </div>
      </div>

      {/* Drawdown Warning */}
      <div className="bg-slate-700/30 rounded-lg p-2">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-red-400 rounded-full"></div>
          <span className="text-xs text-slate-300">
            Expected maximum loss: {Math.abs(maxDrawdown)}%
          </span>
        </div>
      </div>
    </div>
  );
}