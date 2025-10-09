import { useState } from 'react';
import { useAuthStore } from '../store/auth';
import { RequireAdmin } from '../components/auth/RequireAdmin';
import UserIntelligencePanel from '../components/admin/UserIntelligencePanel';
import ApiProvidersPanel from '../components/admin/ApiProvidersPanel';
import FeatureFlagsPanel from '../components/admin/FeatureFlagsPanel';
import RateLimitsPanel from '../components/admin/RateLimitsPanel';
import SchedulesPanel from '../components/admin/SchedulesPanel';
import CachePoliciesPanel from '../components/admin/CachePoliciesPanel';
import SystemSettingsPanel from '../components/admin/SystemSettingsPanel';
import AuditLogPanel from '../components/admin/AuditLogPanel';

export default function Admin() {
  const { email, name } = useAuthStore();
  const [activeTab, setActiveTab] = useState('overview');

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'users', label: 'User Intelligence', icon: '👥' },
    { id: 'api-providers', label: 'API Providers', icon: '🔌' },
    { id: 'feature-flags', label: 'Feature Flags', icon: '🚩' },
    { id: 'rate-limits', label: 'Rate Limits', icon: '⏱️' },
    { id: 'schedules', label: 'Schedules', icon: '⏰' },
    { id: 'cache-policies', label: 'Cache Policies', icon: '💾' },
    { id: 'system-settings', label: 'System Settings', icon: '⚙️' },
    { id: 'audit-log', label: 'Audit Log', icon: '📋' },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return <AdminOverview />;
      case 'users':
        return <UserIntelligencePanel />;
      case 'api-providers':
        return <ApiProvidersPanel />;
      case 'feature-flags':
        return <FeatureFlagsPanel />;
      case 'rate-limits':
        return <RateLimitsPanel />;
      case 'schedules':
        return <SchedulesPanel />;
      case 'cache-policies':
        return <CachePoliciesPanel />;
      case 'system-settings':
        return <SystemSettingsPanel />;
      case 'audit-log':
        return <AuditLogPanel />;
      default:
        return <AdminOverview />;
    }
  };

  return (
    <RequireAdmin>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  Admin Panel
                </h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  System administration and configuration
                </p>
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {name || email}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Administrator
                  </p>
                </div>
                <div className="h-8 w-8 bg-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm font-medium">
                    {(name || email || 'A').charAt(0).toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Sidebar */}
            <div className="lg:w-64 flex-shrink-0">
              <nav className="space-y-1">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      activeTab === tab.id
                        ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    <span className="mr-3 text-lg">{tab.icon}</span>
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            {/* Main Content */}
            <div className="flex-1">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-6">
                  {renderTabContent()}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </RequireAdmin>
  );
}

// Overview component
function AdminOverview() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          System Overview
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Welcome to the admin panel. Use the navigation to manage different aspects of the system.
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-blue-50 dark:bg-blue-900/20 p-6 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center">
            <div className="p-2 bg-blue-500 rounded-lg">
              <span className="text-white text-xl">🔌</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                API Providers
              </p>
              <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                Active
              </p>
            </div>
          </div>
        </div>

        <div className="bg-green-50 dark:bg-green-900/20 p-6 rounded-lg border border-green-200 dark:border-green-800">
          <div className="flex items-center">
            <div className="p-2 bg-green-500 rounded-lg">
              <span className="text-white text-xl">🚩</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-green-600 dark:text-green-400">
                Feature Flags
              </p>
              <p className="text-2xl font-bold text-green-900 dark:text-green-100">
                Configured
              </p>
            </div>
          </div>
        </div>

        <div className="bg-yellow-50 dark:bg-yellow-900/20 p-6 rounded-lg border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-500 rounded-lg">
              <span className="text-white text-xl">⏱️</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                Rate Limits
              </p>
              <p className="text-2xl font-bold text-yellow-900 dark:text-yellow-100">
                Set
              </p>
            </div>
          </div>
        </div>

        <div className="bg-purple-50 dark:bg-purple-900/20 p-6 rounded-lg border border-purple-200 dark:border-purple-800">
          <div className="flex items-center">
            <div className="p-2 bg-purple-500 rounded-lg">
              <span className="text-white text-xl">⏰</span>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-purple-600 dark:text-purple-400">
                Schedules
              </p>
              <p className="text-2xl font-bold text-purple-900 dark:text-purple-100">
                Running
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Recent Activity
        </h3>
        <div className="space-y-3">
          <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
            <span className="w-2 h-2 bg-green-400 rounded-full mr-3"></span>
            System started successfully
            <span className="ml-auto">2 minutes ago</span>
          </div>
          <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
            <span className="w-2 h-2 bg-blue-400 rounded-full mr-3"></span>
            Admin panel accessed
            <span className="ml-auto">5 minutes ago</span>
          </div>
          <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
            <span className="w-2 h-2 bg-yellow-400 rounded-full mr-3"></span>
            Database migrations applied
            <span className="ml-auto">1 hour ago</span>
          </div>
        </div>
      </div>
    </div>
  );
}
