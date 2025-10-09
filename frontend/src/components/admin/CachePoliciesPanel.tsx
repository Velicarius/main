import { useState, useEffect } from 'react';

interface CachePolicy {
  id: string;
  dataset: string;
  ttl_seconds: number;
  swr_enabled: boolean;
  swr_stale_seconds?: number;
  swr_refresh_threshold?: number;
  etag_enabled: boolean;
  ims_enabled: boolean;
  purge_allowed: boolean;
  compression_enabled: boolean;
  circuit_breaker_enabled: boolean;
  circuit_breaker_threshold?: number;
  circuit_breaker_window_seconds?: number;
  circuit_breaker_recovery_seconds?: number;
  meta: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export default function CachePoliciesPanel() {
  const [policies, setPolicies] = useState<CachePolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<CachePolicy | null>(null);

  useEffect(() => {
    fetchPolicies();
  }, []);

  const fetchPolicies = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API call
      
      // Mock data for now
      const mockData: CachePolicy[] = [
        {
          id: '1',
          dataset: 'news',
          ttl_seconds: 3600,
          swr_enabled: true,
          swr_stale_seconds: 7200,
          swr_refresh_threshold: 0.8,
          etag_enabled: true,
          ims_enabled: true,
          purge_allowed: true,
          compression_enabled: false,
          circuit_breaker_enabled: true,
          circuit_breaker_threshold: 3,
          circuit_breaker_window_seconds: 300,
          circuit_breaker_recovery_seconds: 600,
          meta: { priority: 'high' },
          created_at: '2025-01-15T10:00:00Z',
          updated_at: '2025-01-15T10:00:00Z',
        },
        {
          id: '2',
          dataset: 'prices',
          ttl_seconds: 300,
          swr_enabled: false,
          etag_enabled: false,
          ims_enabled: false,
          purge_allowed: true,
          compression_enabled: true,
          circuit_breaker_enabled: false,
          meta: { priority: 'critical' },
          created_at: '2025-01-15T10:00:00Z',
          updated_at: '2025-01-15T10:00:00Z',
        },
        {
          id: '3',
          dataset: 'insights',
          ttl_seconds: 86400,
          swr_enabled: true,
          swr_stale_seconds: 172800,
          swr_refresh_threshold: 0.5,
          etag_enabled: true,
          ims_enabled: false,
          purge_allowed: false,
          compression_enabled: true,
          circuit_breaker_enabled: true,
          circuit_breaker_threshold: 5,
          circuit_breaker_window_seconds: 600,
          circuit_breaker_recovery_seconds: 1200,
          meta: { priority: 'medium' },
          created_at: '2025-01-15T10:00:00Z',
          updated_at: '2025-01-15T10:00:00Z',
        },
      ];
      
      setPolicies(mockData);
    } catch (error) {
      console.error('Failed to fetch policies:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePurgeCache = async (policy: CachePolicy) => {
    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/admin/v1/cache-policies/${policy.id}/purge`, {
      //   method: 'POST',
      // });
      
      alert(`Cache purged for ${policy.dataset}`);
    } catch (error) {
      console.error('Failed to purge cache:', error);
    }
  };

  const formatTTL = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };

  const getDatasetColor = (dataset: string) => {
    switch (dataset) {
      case 'news': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'prices': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'insights': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Cache Policies
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Configure caching strategies and TTL settings
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
        >
          <span>+</span>
          <span>Add Policy</span>
        </button>
      </div>

      {/* Policies Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Dataset
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  TTL
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Features
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Circuit Breaker
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {policies.map((policy) => (
                <tr key={policy.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getDatasetColor(policy.dataset)}`}>
                      {policy.dataset}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {formatTTL(policy.ttl_seconds)}
                    </div>
                    {policy.swr_enabled && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        SWR: {formatTTL(policy.swr_stale_seconds || 0)}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {policy.swr_enabled && (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                          SWR
                        </span>
                      )}
                      {policy.etag_enabled && (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300">
                          ETag
                        </span>
                      )}
                      {policy.ims_enabled && (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300">
                          IMS
                        </span>
                      )}
                      {policy.compression_enabled && (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300">
                          Compress
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {policy.circuit_breaker_enabled ? (
                      <div className="text-sm text-gray-900 dark:text-white">
                        <div>Threshold: {policy.circuit_breaker_threshold}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          Window: {formatTTL(policy.circuit_breaker_window_seconds || 0)}
                        </div>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500 dark:text-gray-400">Disabled</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setEditingPolicy(policy)}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        Edit
                      </button>
                      {policy.purge_allowed && (
                        <button
                          onClick={() => handlePurgeCache(policy)}
                          className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                        >
                          Purge
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {editingPolicy ? 'Edit Cache Policy' : 'Add Cache Policy'}
            </h3>
            <form className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Dataset
                </label>
                <select className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                  <option value="news">News</option>
                  <option value="prices">Prices</option>
                  <option value="insights">Insights</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  TTL (seconds)
                </label>
                <input
                  type="number"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="3600"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Features
                </label>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input type="checkbox" className="rounded border-gray-300" />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">SWR (Stale-While-Revalidate)</span>
                  </label>
                  <label className="flex items-center">
                    <input type="checkbox" className="rounded border-gray-300" />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">ETag</span>
                  </label>
                  <label className="flex items-center">
                    <input type="checkbox" className="rounded border-gray-300" />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">If-Modified-Since</span>
                  </label>
                  <label className="flex items-center">
                    <input type="checkbox" className="rounded border-gray-300" />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Compression</span>
                  </label>
                </div>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setEditingPolicy(null);
                  }}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md"
                >
                  {editingPolicy ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
