import type { UserWithRoles, UserUsageStats, UserQuotas } from '../../../lib/api-admin';

interface UserUsageTabProps {
  user: UserWithRoles;
  usageStats: UserUsageStats | null;
  quotas: UserQuotas | null;
  onRefresh: () => void;
}

export default function UserUsageTab({
  usageStats,
  quotas,
  onRefresh,
}: UserUsageTabProps) {
  if (!usageStats || !quotas) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-gray-500 dark:text-gray-400">Loading usage data...</p>
      </div>
    );
  }

  const getQuotaStatusColor = (quota: any) => {
    if (quota.is_over_hard_cap) {
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
    } else if (quota.is_over_soft_cap) {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
    }
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
  };

  const getQuotaBarColor = (quota: any) => {
    if (quota.is_over_hard_cap) {
      return 'bg-red-500';
    } else if (quota.is_over_soft_cap) {
      return 'bg-yellow-500';
    }
    return 'bg-green-500';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Usage & Limits
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Last {usageStats.period_days} days
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase">
            Total Requests
          </p>
          <p className="text-2xl font-bold text-blue-900 dark:text-blue-100 mt-1">
            {usageStats.total_requests.toLocaleString()}
          </p>
        </div>

        <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg border border-red-200 dark:border-red-800">
          <p className="text-xs font-medium text-red-600 dark:text-red-400 uppercase">
            Total Errors
          </p>
          <p className="text-2xl font-bold text-red-900 dark:text-red-100 mt-1">
            {usageStats.total_errors.toLocaleString()}
          </p>
        </div>

        <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
          <p className="text-xs font-medium text-purple-600 dark:text-purple-400 uppercase">
            Error Rate
          </p>
          <p className="text-2xl font-bold text-purple-900 dark:text-purple-100 mt-1">
            {usageStats.total_requests > 0
              ? ((usageStats.total_errors / usageStats.total_requests) * 100).toFixed(2)
              : '0.00'}%
          </p>
        </div>
      </div>

      {/* Usage by Provider */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Usage by Provider
        </h4>
        <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Provider
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Requests
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Errors
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Tokens
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Avg Response
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
              {Object.entries(usageStats.by_provider).length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                    No usage data
                  </td>
                </tr>
              ) : (
                Object.entries(usageStats.by_provider)
                  .sort((a, b) => b[1].requests - a[1].requests)
                  .map(([provider, stats]) => (
                    <tr key={provider}>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {provider}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                        {stats.requests.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600 dark:text-gray-400">
                        {stats.errors.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600 dark:text-gray-400">
                        {stats.tokens.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600 dark:text-gray-400">
                        {stats.avg_response_time_ms !== null ? `${stats.avg_response_time_ms}ms` : '-'}
                      </td>
                    </tr>
                  ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quotas & Limits */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Current Quotas
        </h4>
        {quotas.quotas.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
            No quotas configured for this user
          </p>
        ) : (
          <div className="space-y-4">
            {quotas.quotas.map((quota, index) => (
              <div
                key={index}
                className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h5 className="text-sm font-semibold text-gray-900 dark:text-white">
                      {quota.resource_type.replace(/_/g, ' ')}
                    </h5>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Period: {quota.period}
                      {quota.period_start && quota.period_end && (
                        <span className="ml-2">
                          ({new Date(quota.period_start).toLocaleDateString()} - {new Date(quota.period_end).toLocaleDateString()})
                        </span>
                      )}
                    </p>
                  </div>
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded ${getQuotaStatusColor(quota)}`}>
                    {quota.is_over_hard_cap ? 'Over Limit' : quota.is_over_soft_cap ? 'Warning' : 'OK'}
                  </span>
                </div>

                {/* Usage Bar */}
                <div className="mt-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-600 dark:text-gray-400">
                      {quota.current_usage.toLocaleString()} / {quota.hard_cap.toLocaleString()}
                    </span>
                    <span className="text-xs font-semibold text-gray-900 dark:text-white">
                      {quota.usage_percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${getQuotaBarColor(quota)}`}
                      style={{ width: `${Math.min(quota.usage_percentage, 100)}%` }}
                    ></div>
                  </div>
                </div>

                {/* Soft Cap Indicator */}
                {quota.soft_cap && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Soft cap: {quota.soft_cap.toLocaleString()}
                    {quota.is_over_soft_cap && ' (exceeded)'}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Usage Timeline */}
      {usageStats.by_date.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Usage Timeline
          </h4>
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {usageStats.by_date.slice(-10).reverse().map((point) => (
                <div key={point.date} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">
                    {new Date(point.date).toLocaleDateString()}
                  </span>
                  <div className="flex items-center space-x-4">
                    <span className="text-gray-900 dark:text-white font-medium">
                      {point.requests} requests
                    </span>
                    {point.errors > 0 && (
                      <span className="text-red-600 dark:text-red-400">
                        {point.errors} errors
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
