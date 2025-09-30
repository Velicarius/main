import { useEffect, useState } from 'react';
import { getPositions, healthCheck, getBaseUrl, getPortfolioHistory, PortfolioValuation, getUserRanking, UserRanking } from '../lib/api';
import { useAuthStore } from '../store/auth';

export default function Dashboard() {
  const { loggedIn, user_id } = useAuthStore();
  const [positions, setPositions] = useState<any[]>([]);
  const [usdBalance, setUsdBalance] = useState<number>(0);
  const [portfolioHistory, setPortfolioHistory] = useState<PortfolioValuation[]>([]);
  const [userRanking, setUserRanking] = useState<UserRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Refresh data when auth state changes
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Check backend health
        await healthCheck();
        
        // Fetch positions
        const pos = await getPositions();
        
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
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [loggedIn, user_id]);

  // Calculate portfolio metrics
  const totalPositions = positions.length;
  const totalInvested = positions.reduce((sum, pos) => sum + (pos.quantity * (pos.buy_price || 0)), 0);
  const totalMarketValue = positions.reduce((sum, pos) => sum + (pos.quantity * (pos.last || pos.buy_price || 0)), 0);
  const totalPnL = totalMarketValue - totalInvested;
  const pnlPercentage = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;
  
  // Total portfolio value including cash
  const totalPortfolioValue = totalMarketValue + usdBalance;

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
            📊 Portfolio Overview
          </h1>
          <p className="text-slate-400 mt-2">Your investment portfolio at a glance</p>
        </div>
        <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-400">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span>Live data</span>
        </div>
      </div>
      
      {/* Portfolio History Chart */}
      {portfolioHistory.length > 0 && (
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-xl">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">Portfolio Value History</h3>
            <span className="text-sm text-slate-400">Last 30 days</span>
          </div>
          <div className="h-64 flex items-center justify-center">
            <div className="w-full h-full relative">
              <svg width="100%" height="100%" viewBox="0 0 800 200" className="overflow-visible">
                {/* Grid lines */}
                <defs>
                  <pattern id="grid" width="40" height="20" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 20" fill="none" stroke="#374151" strokeWidth="1"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />
                
                {/* Chart line */}
                {portfolioHistory.length > 1 && (() => {
                  const values = portfolioHistory.map(p => Number(p.total_value) || 0);
                  const minValue = Math.min(...values);
                  const maxValue = Math.max(...values);
                  
                  if (minValue === maxValue) {
                    // All values are the same, draw a horizontal line
                    return (
                      <polyline
                        fill="none"
                        stroke="#3b82f6"
                        strokeWidth="2"
                        points={`0,100 800,100`}
                      />
                    );
                  }
                  
                  return (
                    <polyline
                      fill="none"
                      stroke="#3b82f6"
                      strokeWidth="2"
                      points={portfolioHistory.map((point, index) => {
                        const x = portfolioHistory.length === 1 ? 400 : (index / (portfolioHistory.length - 1)) * 800;
                        const y = 200 - ((Number(point.total_value) - minValue) / (maxValue - minValue)) * 180;
                        return `${x},${y}`;
                      }).join(' ')}
                    />
                  );
                })()}
                
                {/* Data points */}
                {portfolioHistory.length > 0 && (() => {
                  const values = portfolioHistory.map(p => Number(p.total_value) || 0);
                  const minValue = Math.min(...values);
                  const maxValue = Math.max(...values);
                  
                  return portfolioHistory.map((point, index) => {
                    // Safe calculation for x coordinate
                    const x = portfolioHistory.length === 1 ? 400 : (index / (portfolioHistory.length - 1)) * 800;
                    
                    // Safe calculation for y coordinate
                    let y = 100; // Default center
                    if (minValue !== maxValue) {
                      y = 200 - ((Number(point.total_value) - minValue) / (maxValue - minValue)) * 180;
                    }
                    
                    return (
                      <circle
                        key={point.id}
                        cx={x}
                        cy={y}
                        r="3"
                        fill="#3b82f6"
                        className="hover:r-4 transition-all"
                      />
                    );
                  });
                })()}
              </svg>
              
              {/* Y-axis labels */}
              {portfolioHistory.length > 0 && (() => {
                const values = portfolioHistory.map(p => Number(p.total_value) || 0);
                const minValue = Math.min(...values);
                const maxValue = Math.max(...values);
                
                return (
                  <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-slate-400">
                    <span>${maxValue.toLocaleString()}</span>
                    <span>${minValue.toLocaleString()}</span>
                  </div>
                );
              })()}
              
              {/* X-axis labels */}
              {portfolioHistory.length > 0 && (
                <div className="absolute bottom-0 left-0 w-full flex justify-between text-xs text-slate-400">
                  <span>{new Date(portfolioHistory[0]?.as_of).toLocaleDateString()}</span>
                  <span>{new Date(portfolioHistory[portfolioHistory.length - 1]?.as_of).toLocaleDateString()}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Portfolio Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 mb-1">Total Portfolio</div>
              <div className="text-3xl font-bold text-white">${totalPortfolioValue.toLocaleString()}</div>
            </div>
            <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
              <span className="text-purple-400 text-xl">💼</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 mb-1">Free Cash</div>
              <div className="text-3xl font-bold text-green-400">${usdBalance.toLocaleString()}</div>
            </div>
            <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
              <span className="text-green-400 text-xl">💰</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 mb-1">Total Positions</div>
              <div className="text-3xl font-bold text-white">{totalPositions}</div>
            </div>
            <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
              <span className="text-blue-400 text-xl">📊</span>
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 mb-1">Total Invested</div>
              <div className="text-3xl font-bold text-white">
                ${totalInvested.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
              <span className="text-purple-400 text-xl">💰</span>
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg hover:shadow-xl transition-all duration-300">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 mb-1">Market Value</div>
              <div className="text-3xl font-bold text-white">
                ${totalMarketValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center">
              <span className="text-emerald-400 text-xl">📈</span>
            </div>
          </div>
        </div>
        
        <div className={`bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border shadow-lg hover:shadow-xl transition-all duration-300 ${
          totalPnL >= 0 ? 'border-green-500/30' : 'border-red-500/30'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 mb-1">Total P&L</div>
              <div className={`text-3xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                ${totalPnL.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </div>
              <div className={`text-sm font-medium ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                ({Number.isFinite(pnlPercentage) ? pnlPercentage.toFixed(2) : '0.00'}%)
              </div>
            </div>
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
              totalPnL >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'
            }`}>
              <span className={`text-xl ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {totalPnL >= 0 ? '📊' : '📉'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
        <h3 className="text-lg font-semibold text-white mb-6">Quick Actions</h3>
        <div className="flex flex-wrap gap-4">
          <a
            href="/positions"
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition-all duration-200 shadow-lg shadow-blue-500/25 font-medium"
          >
            View Positions
          </a>
          <a
            href="/positions"
            className="px-6 py-3 bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800 text-white rounded-lg transition-all duration-200 shadow-lg shadow-emerald-500/25 font-medium"
          >
            Add Position
          </a>
          <a
            href="/insights"
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white rounded-lg transition-all duration-200 shadow-lg shadow-purple-500/25 font-medium"
          >
            AI Analysis
          </a>
        </div>
      </div>

      {/* User Ranking */}
      {userRanking.length > 0 && (
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">🏆 Top Performers</h3>
            <span className="text-sm text-slate-400">Ranked by PnL %</span>
          </div>
          <div className="space-y-3">
            {userRanking.slice(0, 10).map((user, index) => (
              <div key={user.user_id} className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg border border-slate-600/30 hover:bg-slate-700/50 transition-colors">
                <div className="flex items-center space-x-4">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    index === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                    index === 1 ? 'bg-gray-400/20 text-gray-300' :
                    index === 2 ? 'bg-orange-500/20 text-orange-400' :
                    'bg-slate-600/20 text-slate-400'
                  }`}>
                    {user.rank}
                  </div>
                  <div>
                    <div className="text-white font-medium">{user.name}</div>
                    <div className="text-xs text-slate-400">{user.email}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-lg font-bold ${user.pnl_percentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {user.pnl_percentage >= 0 ? '+' : ''}{user.pnl_percentage.toFixed(1)}%
                  </div>
                  <div className="text-xs text-slate-400">
                    ${user.total_value.toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Positions Preview */}
      {positions.length > 0 && (
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">Recent Positions</h3>
            <a href="/positions" className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
              View all →
            </a>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="text-left py-3 text-slate-400 font-medium">Symbol</th>
                  <th className="text-right py-3 text-slate-400 font-medium">Quantity</th>
                  <th className="text-right py-3 text-slate-400 font-medium">Buy Price</th>
                  <th className="text-right py-3 text-slate-400 font-medium">Current Value</th>
                </tr>
              </thead>
              <tbody>
                {positions.slice(0, 5).map((pos) => {
                  const quantity = Number(pos.quantity) || 0;
                  const buyPrice = Number(pos.buy_price) || 0;
                  const currentPrice = Number(pos.last) || buyPrice;
                  const value = quantity * currentPrice;
                  const pnl = value - (quantity * buyPrice);
                  const pnlPercent = buyPrice > 0 ? (pnl / (quantity * buyPrice)) * 100 : 0;
                  
                  return (
                    <tr key={pos.id} className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors">
                      <td className="py-3 text-white font-medium">{pos.symbol}</td>
                      <td className="py-3 text-right text-slate-300">{quantity}</td>
                      <td className="py-3 text-right text-slate-300">
                        ${buyPrice > 0 ? buyPrice.toFixed(2) : '—'}
                      </td>
                      <td className="py-3 text-right">
                        <div className="text-slate-300">${value.toFixed(2)}</div>
                        {buyPrice > 0 && (
                          <div className={`text-xs ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {pnl >= 0 ? '+' : ''}{pnlPercent.toFixed(1)}%
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
