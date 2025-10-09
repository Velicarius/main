import { useState, useEffect } from 'react';

interface Schedule {
  id: string;
  task_name: string;
  task_type: string;
  cron_expression?: string;
  timezone: string;
  is_enabled: boolean;
  last_run_at?: string;
  last_run_status?: string;
  last_run_duration_ms?: number;
  next_run_at?: string;
  payload: Record<string, any>;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
}

export default function SchedulesPanel() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null);

  useEffect(() => {
    fetchSchedules();
  }, []);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API call
      
      // Mock data for now
      const mockData: Schedule[] = [
        {
          id: '1',
          task_name: 'prices.run_eod_refresh',
          task_type: 'celery',
          cron_expression: '30 23 * * *',
          timezone: 'Europe/Warsaw',
          is_enabled: true,
          last_run_at: '2025-01-14T23:30:00Z',
          last_run_status: 'success',
          last_run_duration_ms: 45000,
          next_run_at: '2025-01-15T23:30:00Z',
          payload: { symbols: ['AAPL', 'GOOGL'] },
          retry_count: 0,
          max_retries: 3,
          created_at: '2025-01-15T10:00:00Z',
          updated_at: '2025-01-15T10:00:00Z',
        },
        {
          id: '2',
          task_name: 'news.fetch_latest',
          task_type: 'celery',
          cron_expression: '0 */6 * * *',
          timezone: 'UTC',
          is_enabled: true,
          last_run_at: '2025-01-15T12:00:00Z',
          last_run_status: 'success',
          last_run_duration_ms: 12000,
          next_run_at: '2025-01-15T18:00:00Z',
          payload: { sources: ['newsapi', 'finnhub'] },
          retry_count: 0,
          max_retries: 3,
          created_at: '2025-01-15T10:00:00Z',
          updated_at: '2025-01-15T10:00:00Z',
        },
        {
          id: '3',
          task_name: 'insights.generate_daily',
          task_type: 'manual',
          cron_expression: undefined,
          timezone: 'UTC',
          is_enabled: false,
          last_run_at: '2025-01-14T00:00:00Z',
          last_run_status: 'failure',
          last_run_duration_ms: undefined,
          next_run_at: undefined,
          payload: { user_ids: ['all'] },
          retry_count: 2,
          max_retries: 3,
          created_at: '2025-01-15T10:00:00Z',
          updated_at: '2025-01-15T10:00:00Z',
        },
      ];
      
      setSchedules(mockData);
    } catch (error) {
      console.error('Failed to fetch schedules:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnabled = async (schedule: Schedule) => {
    try {
      setSchedules(prev => prev.map(s => 
        s.id === schedule.id 
          ? { ...s, is_enabled: !s.is_enabled }
          : s
      ));
    } catch (error) {
      console.error('Failed to toggle schedule:', error);
    }
  };

  const handleRunNow = async (schedule: Schedule) => {
    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/admin/v1/schedules/${schedule.id}/run-now`, {
      //   method: 'POST',
      // });
      
      // Update the schedule with new run info
      setSchedules(prev => prev.map(s => 
        s.id === schedule.id 
          ? { 
              ...s, 
              last_run_at: new Date().toISOString(),
              last_run_status: 'running',
              retry_count: 0
            }
          : s
      ));
    } catch (error) {
      console.error('Failed to run schedule:', error);
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'failure': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'running': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'timeout': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'celery': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'cron': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300';
      case 'manual': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return 'N/A';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
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
            Schedules
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Manage Celery tasks and cron jobs
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
        >
          <span>+</span>
          <span>Add Schedule</span>
        </button>
      </div>

      {/* Schedules Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Task
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Schedule
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Last Run
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {schedules.map((schedule) => (
                <tr key={schedule.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {schedule.task_name}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {schedule.timezone}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTypeColor(schedule.task_type)}`}>
                      {schedule.task_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {schedule.cron_expression || 'Manual'}
                    </div>
                    {schedule.next_run_at && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Next: {formatDate(schedule.next_run_at)}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {formatDate(schedule.last_run_at)}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {formatDuration(schedule.last_run_duration_ms)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(schedule.last_run_status)}`}>
                        {schedule.last_run_status || 'Never'}
                      </span>
                      {schedule.retry_count > 0 && (
                        <span className="text-xs text-yellow-600 dark:text-yellow-400">
                          ({schedule.retry_count}/{schedule.max_retries})
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleToggleEnabled(schedule)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          schedule.is_enabled ? 'bg-blue-500' : 'bg-gray-200 dark:bg-gray-600'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            schedule.is_enabled ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                      <button
                        onClick={() => handleRunNow(schedule)}
                        className="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300"
                        disabled={schedule.last_run_status === 'running'}
                      >
                        Run Now
                      </button>
                      <button
                        onClick={() => setEditingSchedule(schedule)}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        Edit
                      </button>
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
              {editingSchedule ? 'Edit Schedule' : 'Add Schedule'}
            </h3>
            <form className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Task Name
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="module.task_name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Task Type
                </label>
                <select className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                  <option value="celery">Celery</option>
                  <option value="cron">Cron</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Cron Expression
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="30 23 * * *"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Timezone
                </label>
                <select className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                  <option value="UTC">UTC</option>
                  <option value="Europe/Warsaw">Europe/Warsaw</option>
                  <option value="America/New_York">America/New_York</option>
                </select>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setEditingSchedule(null);
                  }}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md"
                >
                  {editingSchedule ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
