import { useEffect, useState } from 'react';
import { getPositions, healthCheck, getBaseUrl, getPortfolioHistory, PortfolioValuation, getUserRanking, UserRanking } from '../lib/api';
import { useAuthStore } from '../store/auth';
import { useStrategyStore } from '../store/strategy';
import { useStrategyInit } from '../hooks/useStrategyInit';
import { PortfolioSnapshot } from '../components/dashboard/PortfolioSnapshot';
import { SacredTimeline } from '../components/dashboard/SacredTimeline';
import { ManualStrategyEditor } from '../components/strategy/ManualStrategyEditor';
import { calculatePortfolioPnL } from '../utils/pnl';

export default function Dashboard() {
  const { loggedIn, user_id } = useAuthStore();
  const { current: strategy, loadStrategy } = useStrategyStore();
  const [positions, setPositions] = useState<any[]>([]);
  const [usdBalance, setUsdBalance] = useState<number>(0);
  const [portfolioHistory, setPortfolioHistory] = useState<PortfolioValuation[]>([]);
  const [, setUserRanking] = useState<UserRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize strategy from onboarding data
  useStrategyInit();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Check backend health
        await healthCheck();
        
        // Load strategy data
        await loadStrategy();
        
        // Fetch positions
        const pos = await getPositions();
        
        // Fetch current prices for each position (skip USD)
        const enrichedPositions = await Promise.all(
          pos.map(async (position) => {
            // Skip price fetching for USD
            if (position.symbol === 'USD') {
              return {
                ...position,
                last: 1.0  // USD always has price of 1.0
              };
            }
            
            try {
              const response = await fetch(`${getBaseUrl()}/prices-eod/${encodeURIComponent(position.symbol)}/latest`);
              let currentPrice = null;
              
              if (response.ok) {
                const priceData = await response.json();
                currentPrice = priceData.close;
              }
              
              return {
                ...position,
                last: currentPrice
              };
            } catch (error) {
              console.warn(`Failed to fetch price for ${position.symbol}:`, error);
              return {
                ...position,
                last: null
              };
            }
          })
        );
        
        // Разделяем позиции и USD баланс
        const nonUsdPositions = enrichedPositions.filter(p => p.symbol !== 'USD');
        const usdPosition = enrichedPositions.find(p => p.symbol === 'USD');
        
        setPositions(nonUsdPositions);
        setUsdBalance(usdPosition ? Number(usdPosition.quantity) : 0);

        // Fetch portfolio history if user is logged in
        if (user_id) {
          try {
            const history = await getPortfolioHistory(user_id, 30);
            setPortfolioHistory(history);
          } catch (err) {
            console.warn('Failed to fetch portfolio history:', err);
          }

          // Fetch user ranking
          try {
            const ranking = await getUserRanking();
            setUserRanking(ranking);
          } catch (err) {
            console.warn('Failed to fetch user ranking:', err);
          }
        }
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };

    if (loggedIn) {
      fetchData();
    }
  }, [loggedIn, user_id]);

  // Calculate portfolio metrics using shared logic
  const { totalMarketValue, totalPnL, pnlPercentage } = calculatePortfolioPnL(positions);

  // Total portfolio value including cash
  const totalPortfolioValue = totalMarketValue + usdBalance;

  // Подготовка данных для графика
  const actualSeries = portfolioHistory.map((point: any) => ({
    t: point.as_of,
    value: Number(point.total_value) || 0
  }));



  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
          <div className="text-slate-400">Loading portfolio data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gradient-to-r from-red-900/20 to-red-800/20 border border-red-500/30 rounded-xl p-6 backdrop-blur-sm">
        <div className="flex items-center space-x-3">
          <div className="w-6 h-6 bg-red-500/20 rounded-full flex items-center justify-center">
            <span className="text-red-400 text-sm">!</span>
          </div>
          <div className="text-red-400 font-medium">Error: {error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent mb-2">
          📊 Dashboard
        </h1>
        <p className="text-slate-400">Your investment portfolio at a glance</p>
      </div>

      {/* [Snapshot] -> Value, P&L */}
      <PortfolioSnapshot 
        totalValue={totalPortfolioValue}
        totalPnL={totalPnL}
        pnlPercentage={pnlPercentage}
      />

      {/* [Sacred Timeline] -> Graph (Expected vs Actual), % progress to goal */}
      <SacredTimeline 
        currency="USD"
        currentTotalValue={totalPortfolioValue}
        actualSeries={actualSeries.map((point: any) => ({
          date: point.t,
          value: point.value
        }))}
        strategy={strategy}
        loading={loading}
      />

      {/* [Strategy] -> Manual/Template Strategy Editor */}
      <ManualStrategyEditor 
        currentValue={totalPortfolioValue}
        onStrategyUpdate={() => {
          // Trigger strategy series recalculation for Sacred Timeline
          // This would update the strategy-based forecast
        }}
      />
    </div>
  );
}