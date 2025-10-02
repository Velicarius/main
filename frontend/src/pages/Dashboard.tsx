import { useEffect, useState } from 'react';
import { getPositions, healthCheck, getBaseUrl, getPortfolioHistory, PortfolioValuation, getUserRanking, UserRanking } from '../lib/api';
import { useAuthStore } from '../store/auth';
import { useStrategyStore } from '../store/strategy';
import { useStrategyInit } from '../hooks/useStrategyInit';
import { fmtCurrency } from '../lib/format';
import { KpiTile } from '../components/dashboard/KpiTile';
import { PeriodSwitcher, Period } from '../components/dashboard/PeriodSwitcher';
import { AISnapshot } from '../components/dashboard/AISnapshot';
import { QuickActions } from '../components/dashboard/QuickActions';
import { TopMovers } from '../components/dashboard/TopMovers';
import { AlertsWidget } from '../components/dashboard/AlertsWidget';
import { StrategySelector } from '../components/strategy/StrategySelector';
import { SacredTimeline } from '../components/dashboard/SacredTimeline';

export default function Dashboard() {
  const { loggedIn, user_id } = useAuthStore();
  const { current: strategy } = useStrategyStore();
  const [positions, setPositions] = useState<any[]>([]);
  const [usdBalance, setUsdBalance] = useState<number>(0);
  const [portfolioHistory, setPortfolioHistory] = useState<PortfolioValuation[]>([]);
  const [, setUserRanking] = useState<UserRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<Period>("1m");

  // Initialize strategy from onboarding data
  useStrategyInit();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Check backend health
        await healthCheck();
        
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

    fetchData();
  }, [loggedIn, user_id]);

  // Calculate portfolio metrics
  const totalInvested = positions.reduce((sum, pos) => {
    // Use current market price if buy_price is null (for onboarding positions)
    const effectiveBuyPrice = pos.buy_price || pos.last || 0;
    return sum + (pos.quantity * effectiveBuyPrice);
  }, 0);
  const totalMarketValue = positions.reduce((sum, pos) => sum + (pos.quantity * (pos.last || pos.buy_price || 0)), 0);
  const totalPnL = totalMarketValue - totalInvested;
  const pnlPercentage = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;
  
  // Total portfolio value including cash
  const totalPortfolioValue = totalMarketValue + usdBalance;

  // Форматирование чисел

  const formatPercent = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    }).format(value / 100);
  };

  // Подготовка данных для графика
  const actualSeries = portfolioHistory.map(point => ({
    t: point.as_of,
    value: Number(point.total_value) || 0
  }));

  // Generate strategy series
  const generateStrategySeries = () => {
    const months = 12; // 1 year forecast
    const data = [];
    const now = new Date();
    
    for (let i = 0; i <= months; i++) {
      const date = new Date(now);
      date.setMonth(date.getMonth() + i);
      
      // Simple compound growth with monthly contributions
      const monthsElapsed = i;
      const monthlyReturn = strategy.expectedReturnAnnual / 12;
      const compoundGrowth = Math.pow(1 + monthlyReturn, monthsElapsed);
      const contributionGrowth = strategy.monthlyContribution * monthsElapsed;
      
      const forecastValue = (totalPortfolioValue * compoundGrowth) + contributionGrowth;
      
      data.push({
        t: date.toISOString().split('T')[0], // YYYY-MM-DD format
        value: Math.round(forecastValue)
      });
    }
    
    return data;
  };

  const strategySeries = generateStrategySeries();
  const todayISO = new Date().toISOString().split('T')[0];

  // Подготовка данных для TopMovers
  const topMoversData = positions
    .map(pos => {
      const quantity = pos.quantity || 0;
      const buyPrice = pos.buy_price || 0;
      const currentPrice = pos.last || 0;
      const value = quantity * currentPrice;
      const pnl = value - (quantity * buyPrice);
      const pnlPercent = buyPrice > 0 ? (pnl / (quantity * buyPrice)) * 100 : 0;
      
      return {
        ticker: pos.symbol,
        pnlPercent,
        currentValue: value
      };
    })
    .filter(mover => mover.pnlPercent !== 0)
    .sort((a, b) => Math.abs(b.pnlPercent) - Math.abs(a.pnlPercent))
    .slice(0, 5);

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
      {/* Above the fold - без вертикального скролла страницы */}
      <div className="space-y-6">
        {/* Верхняя полоса */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              📊 Portfolio Overview
            </h1>
            <p className="text-slate-400 mt-2">Your investment portfolio at a glance</p>
          </div>
          <div className="flex items-center space-x-4">
            <PeriodSwitcher value={selectedPeriod} onChange={setSelectedPeriod} />
            <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-400">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span>Live data</span>
            </div>
          </div>
        </div>

        {/* Ряд KPI */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <KpiTile
            label="Total Value"
            value={fmtCurrency(totalPortfolioValue, 'USD')}
            icon="💼"
            variant="primary"
          />
          <KpiTile
            label="Free Cash"
            value={fmtCurrency(usdBalance, 'USD')}
            icon="💰"
            variant="success"
          />
          <KpiTile
            label="Total Positions"
            value={positions.length.toString()}
            icon="📊"
            variant="neutral"
          />
          <KpiTile
            label="Total Invested"
            value={fmtCurrency(totalInvested, 'USD')}
            icon="💎"
            variant="neutral"
          />
          <KpiTile
            label="Market Value"
            value={fmtCurrency(totalMarketValue, 'USD')}
            icon="📈"
            variant="neutral"
          />
          <KpiTile
            label="Total P&L"
            value={`${totalPnL >= 0 ? '+' : ''}${fmtCurrency(totalPnL, 'USD')}`}
            sub={`${totalPnL >= 0 ? '+' : ''}${formatPercent(pnlPercentage)}`}
            icon={totalPnL >= 0 ? "📊" : "📉"}
            variant={totalPnL >= 0 ? "success" : "warning"}
          />
        </div>

        {/* AI Snapshot */}
        <AISnapshot />
      </div>

      {/* Ниже - с вертикальным скроллом */}
      <div className="space-y-6">
        {/* Strategy Selector */}
        <StrategySelector />

        {/* Sacred Timeline */}
        <SacredTimeline 
          currency="USD"
          todayISO={todayISO}
          registrationDateISO="2024-01-01" // TODO: Get from user profile
          horizonYears={1}
          currentTotalValue={totalPortfolioValue}
          actualSeries={actualSeries}
          strategySeries={strategySeries}
        />


        {/* Быстрые действия */}
        <QuickActions />

        {/* Две колонки: TopMovers и AlertsWidget */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TopMovers data={topMoversData} />
          <AlertsWidget />
        </div>
      </div>
    </div>
  );
}