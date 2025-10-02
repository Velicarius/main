// Виджет топ-движущихся позиций
export type TopMover = {
  ticker: string;
  pnlPercent: number;
  currentValue: number;
};

export type TopMoversProps = {
  data?: TopMover[];
};

export function TopMovers({ data }: TopMoversProps) {
  // Мок-данные если нет реальных
  const mockData: TopMover[] = [
    { ticker: "AAPL", pnlPercent: 12.5, currentValue: 2500 },
    { ticker: "MSFT", pnlPercent: 8.3, currentValue: 1800 },
    { ticker: "GOOGL", pnlPercent: -5.2, currentValue: 1200 },
    { ticker: "TSLA", pnlPercent: 15.7, currentValue: 900 },
    { ticker: "NVDA", pnlPercent: 22.1, currentValue: 800 }
  ];

  const movers = data && data.length > 0 ? data : mockData;

  const formatValue = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getPnlColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-400';
    if (pnl < 0) return 'text-red-400';
    return 'text-slate-400';
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
      <h3 className="text-lg font-semibold text-white mb-4">Top Movers</h3>
      
      {movers.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-slate-400 text-2xl mb-2">📈</div>
          <p className="text-slate-400">No data yet</p>
          <p className="text-sm text-slate-500">Add positions to see movers</p>
        </div>
      ) : (
        <div className="space-y-3">
          {movers.map((mover, index) => (
            <div key={mover.ticker} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center text-sm font-medium text-slate-300">
                  {index + 1}
                </div>
                <div>
                  <div className="font-medium text-white">{mover.ticker}</div>
                  <div className="text-sm text-slate-400">{formatValue(mover.currentValue)}</div>
                </div>
              </div>
              <div className={`text-right font-medium ${getPnlColor(mover.pnlPercent)}`}>
                {mover.pnlPercent > 0 ? '+' : ''}{mover.pnlPercent.toFixed(1)}%
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
