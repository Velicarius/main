import { useState, useEffect } from 'react';

interface AuditLogEntry {
  id: string;
  actor_id?: string;
  actor_type: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  entity_name?: string;
  before_state?: Record<string, any>;
  after_state?: Record<string, any>;
  timestamp: string;
  ip_address?: string;
  user_agent?: string;
  request_id?: string;
  metadata?: Record<string, any>;
}

export default function AuditLogPanel() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    action: '',
    entity_type: '',
    actor_type: '',
    date_from: '',
    date_to: '',
  });

  useEffect(() => {
    fetchEntries();
  }, [filters]);

  const fetchEntries = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API call
      
      // Mock data for now
      const mockData: AuditLogEntry[] = [
        {
          id: '1',
          actor_id: 'user-123',
          actor_type: 'user',
          action: 'create',
          entity_type: 'feature_flag',
          entity_id: 'flag-456',
          entity_name: 'NEW_FEATURE_ENABLE',
          before_state: undefined,
          after_state: { key: 'NEW_FEATURE_ENABLE', value: true },
          timestamp: '2025-01-15T14:30:00Z',
          ip_address: '192.168.1.100',
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
          request_id: 'req-789',
          metadata: { source: 'admin_panel' },
        },
        {
          id: '2',
          actor_id: 'user-123',
          actor_type: 'user',
          action: 'update',
          entity_type: 'api_provider',
          entity_id: 'provider-789',
          entity_name: 'OpenAI',
          before_state: { is_enabled: false },
          after_state: { is_enabled: true },
          timestamp: '2025-01-15T14:25:00Z',
          ip_address: '192.168.1.100',
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
          request_id: 'req-788',
          metadata: { source: 'admin_panel' },
        },
        {
          id: '3',
          actor_id: undefined,
          actor_type: 'system',
          action: 'run',
          entity_type: 'schedule',
          entity_id: 'schedule-123',
          entity_name: 'prices.run_eod_refresh',
          before_state: { last_run_at: null },
          after_state: { last_run_at: '2025-01-15T14:20:00Z', status: 'success' },
          timestamp: '2025-01-15T14:20:00Z',
          ip_address: undefined,
          user_agent: undefined,
          request_id: 'system-456',
          metadata: { duration_ms: 45000 },
        },
        {
          id: '4',
          actor_id: 'user-456',
          actor_type: 'user',
          action: 'login',
          entity_type: 'user',
          entity_id: 'user-456',
          entity_name: 'test@rbac.com',
          before_state: undefined,
          after_state: { last_login: '2025-01-15T14:15:00Z' },
          timestamp: '2025-01-15T14:15:00Z',
          ip_address: '192.168.1.101',
          user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
          request_id: 'req-787',
          metadata: { source: 'web_app' },
        },
        {
          id: '5',
          actor_id: 'user-123',
          actor_type: 'user',
          action: 'delete',
          entity_type: 'rate_limit',
          entity_id: 'limit-321',
          entity_name: 'user_456_insights',
          before_state: { scope: 'user', scope_id: 'user_456', limit: 100 },
          after_state: undefined,
          timestamp: '2025-01-15T14:10:00Z',
          ip_address: '192.168.1.100',
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
          request_id: 'req-786',
          metadata: { source: 'admin_panel' },
        },
      ];
      
      setEntries(mockData);
    } catch (error) {
      console.error('Failed to fetch audit entries:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'create': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'update': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'delete': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'login': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300';
      case 'run': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const getEntityTypeColor = (entityType: string) => {
    switch (entityType) {
      case 'feature_flag': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'api_provider': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'schedule': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300';
      case 'rate_limit': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'user': return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const getActorTypeColor = (actorType: string) => {
    switch (actorType) {
      case 'user': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'system': return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
      case 'api': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatState = (state: Record<string, any> | null | undefined) => {
    if (!state) return 'N/A';
    return JSON.stringify(state, null, 2);
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
            Audit Log
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Track all administrative actions and system events
          </p>
        </div>
        <button
          onClick={() => fetchEntries()}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
        >
          <span>🔄</span>
          <span>Refresh</span>
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Action
            </label>
            <select
              value={filters.action}
              onChange={(e) => setFilters(prev => ({ ...prev, action: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">All Actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
              <option value="login">Login</option>
              <option value="run">Run</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Entity Type
            </label>
            <select
              value={filters.entity_type}
              onChange={(e) => setFilters(prev => ({ ...prev, entity_type: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">All Entities</option>
              <option value="feature_flag">Feature Flag</option>
              <option value="api_provider">API Provider</option>
              <option value="schedule">Schedule</option>
              <option value="rate_limit">Rate Limit</option>
              <option value="user">User</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Actor Type
            </label>
            <select
              value={filters.actor_type}
              onChange={(e) => setFilters(prev => ({ ...prev, actor_type: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">All Actors</option>
              <option value="user">User</option>
              <option value="system">System</option>
              <option value="api">API</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              From Date
            </label>
            <input
              type="datetime-local"
              value={filters.date_from}
              onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              To Date
            </label>
            <input
              type="datetime-local"
              value={filters.date_to}
              onChange={(e) => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* Audit Entries Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Entity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Changes
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {formatDate(entry.timestamp)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getActorTypeColor(entry.actor_type)}`}>
                        {entry.actor_type}
                      </span>
                      {entry.actor_id && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {entry.actor_id}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getActionColor(entry.action)}`}>
                      {entry.action}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getEntityTypeColor(entry.entity_type)}`}>
                        {entry.entity_type}
                      </span>
                      {entry.entity_name && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {entry.entity_name}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900 dark:text-white max-w-xs">
                      <div className="truncate">
                        <strong>Before:</strong> {formatState(entry.before_state)}
                      </div>
                      <div className="truncate mt-1">
                        <strong>After:</strong> {formatState(entry.after_state)}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    <div>
                      {entry.ip_address && (
                        <div>IP: {entry.ip_address}</div>
                      )}
                      {entry.request_id && (
                        <div>Request: {entry.request_id}</div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center">
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Showing {entries.length} entries
        </div>
        <div className="flex space-x-2">
          <button className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600">
            Previous
          </button>
          <button className="px-3 py-1 text-sm bg-blue-500 text-white rounded">
            1
          </button>
          <button className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600">
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
