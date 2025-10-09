import type { UserWithRoles, PortfolioSummary, PortfolioHistoryPoint } from '../../../lib/api-admin';

interface UserPortfolioTabProps {
  user: UserWithRoles;
  portfolioSummary: PortfolioSummary | null;
  portfolioHistory: PortfolioHistoryPoint[];
  onRefresh: () => void;
}

export default function UserPortfolioTab({
  portfolioSummary,
  portfolioHistory,
  onRefresh,
}: UserPortfolioTabProps) {
  if (!portfolioSummary) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-gray-500 dark:text-gray-400">Loading portfolio data...</p>
      </div>
    );
  }

  const totalReturn = portfolioSummary.total_value - portfolioSummary.total_invested;
  const isProfit = totalReturn >= 0;

  return (
    <div className="space-y-6">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Portfolio Overview
        </h3>
        <button
          onClick={onRefresh}
          className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Portfolio Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Value */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-900/10 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase">
            Total Value
          </p>
          <p className="text-2xl font-bold text-blue-900 dark:text-blue-100 mt-1">
            ${portfolioSummary.total_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
            {portfolioSummary.positions_count} positions
          </p>
        </div>

        {/* Total Return */}
        <div className={`bg-gradient-to-br ${
          isProfit
            ? 'from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-900/10 border-green-200 dark:border-green-800'
            : 'from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-900/10 border-red-200 dark:border-red-800'
        } p-4 rounded-lg border`}>
          <p className={`text-xs font-medium uppercase ${
            isProfit ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
          }`}>
            Total Return
          </p>
          <p className={`text-2xl font-bold mt-1 ${
            isProfit ? 'text-green-900 dark:text-green-100' : 'text-red-900 dark:text-red-100'
          }`}>
            {isProfit ? '+' : ''}${totalReturn.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className={`text-xs mt-1 ${
            isProfit ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
          }`}>
            {isProfit ? '+' : ''}{portfolioSummary.total_return_pct.toFixed(2)}%
          </p>
        </div>

        {/* Total Invested */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-900/10 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
          <p className="text-xs font-medium text-purple-600 dark:text-purple-400 uppercase">
            Total Invested
          </p>
          <p className="text-2xl font-bold text-purple-900 dark:text-purple-100 mt-1">
            ${portfolioSummary.total_invested.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      {/* Allocation by Asset Class */}
      {Object.keys(portfolioSummary.allocation).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Asset Allocation
          </h4>
          <div className="space-y-3">
            {Object.entries(portfolioSummary.allocation)
              .sort((a, b) => b[1] - a[1])
              .map(([assetClass, percentage]) => (
                <div key={assetClass}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {assetClass}
                    </span>
                    <span className="text-sm font-bold text-gray-900 dark:text-white">
                      {percentage.toFixed(2)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all"
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Top Holdings */}
      {portfolioSummary.top_holdings.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Top Holdings
          </h4>
          <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Value
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    % of Portfolio
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {portfolioSummary.top_holdings.map((holding) => (
                  <tr key={holding.symbol}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {holding.symbol}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                      ${holding.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600 dark:text-gray-400">
                      {holding.pct_of_portfolio.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Portfolio History Chart Placeholder */}
      {portfolioHistory.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Portfolio Performance (Last 30 Days)
          </h4>
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {portfolioHistory.length} snapshots recorded
            </p>
            <div className="mt-2 space-y-1">
              {portfolioHistory.slice(-5).map((point) => (
                <div key={point.date} className="flex items-center justify-between text-xs">
                  <span className="text-gray-500 dark:text-gray-400">{point.date}</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    ${point.total_value.toLocaleString()}
                  </span>
                  <span className={point.total_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {point.total_return_pct >= 0 ? '+' : ''}{point.total_return_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {portfolioSummary.positions_count === 0 && (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            No positions in portfolio
          </p>
        </div>
      )}
    </div>
  );
}
