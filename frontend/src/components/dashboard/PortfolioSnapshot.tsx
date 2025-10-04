
interface PortfolioSnapshotProps {
  totalValue: number;
  totalPnL: number;
  pnlPercentage: number;
}

export function PortfolioSnapshot({ totalValue, totalPnL, pnlPercentage }: PortfolioSnapshotProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercent = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
      signDisplay: 'always'
    }).format(value / 100);
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white mb-4">📊 Portfolio Snapshot</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Total Value */}
          <div className="space-y-2">
            <div className="text-sm text-slate-400">Total Portfolio Value</div>
            <div className="text-4xl font-bold text-blue-400">
              {formatCurrency(totalValue)}
            </div>
          </div>

          {/* Total P&L */}
          <div className="space-y-2">
            {totalPnL !== 0 ? (
              <>
                <div className="text-sm text-slate-400">Total P&L</div>
                <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrency(totalPnL)}
                </div>
                <div className={`text-lg ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercent(pnlPercentage)}
                </div>
              </>
            ) : (
              <>
                <div className="text-sm text-slate-400">Total P&L</div>
                <div className="text-2xl font-bold text-slate-400">
                  {formatCurrency(totalPnL)}
                </div>
                <div className="text-sm text-slate-500">
                  Calculate after position adds
                </div>
              </>
            )}
          </div>
        </div>

        {/* Status Indicator */}
        <div className="mt-4 flex items-center justify-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${totalPnL >= 0 ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
          <span className="text-sm text-slate-400">
            {totalPnL >= 0 ? 'Portfolio is up' : totalPnL === 0 ? 'Portfolio is neutral' : 'Portfolio is down'}
          </span>
        </div>
      </div>
    </div>
  );
}
