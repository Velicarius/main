import { useState, useEffect } from 'react';
import {
  usersAPI,
  rolesAPI,
  userIntelligenceAPI,
  type UserWithRoles,
  type Role,
  type PortfolioSummary,
  type PortfolioHistoryPoint,
  type UserActivityResponse,
  type UserUsageStats,
  type UserQuotas
} from '../../lib/api-admin';
import UserDetailsTab from './intelligence/UserDetailsTab';
import UserPortfolioTab from './intelligence/UserPortfolioTab';
import UserActivityTab from './intelligence/UserActivityTab';
import UserUsageTab from './intelligence/UserUsageTab';

export default function UserIntelligencePanel() {
  const [users, setUsers] = useState<UserWithRoles[]>([]);
  const [allRoles, setAllRoles] = useState<Role[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserWithRoles | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('details');

  // Intelligence data
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [portfolioHistory, setPortfolioHistory] = useState<PortfolioHistoryPoint[]>([]);
  const [activityData, setActivityData] = useState<UserActivityResponse | null>(null);
  const [usageStats, setUsageStats] = useState<UserUsageStats | null>(null);
  const [quotas, setQuotas] = useState<UserQuotas | null>(null);

  const tabs = [
    { id: 'details', label: 'Details', icon: '👤' },
    { id: 'portfolio', label: 'Portfolio', icon: '💼' },
    { id: 'activity', label: 'Activity', icon: '📊' },
    { id: 'usage', label: 'Usage & Limits', icon: '⚡' },
  ];

  useEffect(() => {
    fetchUsers();
    fetchRoles();
  }, []);

  useEffect(() => {
    if (selectedUser) {
      // Fetch intelligence data when user is selected
      fetchIntelligenceData(selectedUser.id);
    }
  }, [selectedUser]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const data = await usersAPI.list();
      setUsers(data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      alert(`Failed to fetch users: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const data = await rolesAPI.list();
      setAllRoles(data);
    } catch (error) {
      console.error('Failed to fetch roles:', error);
    }
  };

  const fetchIntelligenceData = async (userId: string) => {
    try {
      // Fetch all intelligence data in parallel
      const [portfolio, history, activity, usage, quotasData] = await Promise.allSettled([
        userIntelligenceAPI.getPortfolioSummary(userId),
        userIntelligenceAPI.getPortfolioHistory(userId, 30),
        userIntelligenceAPI.getActivity(userId, { days: 7, limit: 50 }),
        userIntelligenceAPI.getUsageStats(userId, { days: 30 }),
        userIntelligenceAPI.getQuotas(userId),
      ]);

      if (portfolio.status === 'fulfilled') setPortfolioSummary(portfolio.value);
      if (history.status === 'fulfilled') setPortfolioHistory(history.value);
      if (activity.status === 'fulfilled') setActivityData(activity.value);
      if (usage.status === 'fulfilled') setUsageStats(usage.value);
      if (quotasData.status === 'fulfilled') setQuotas(quotasData.value);
    } catch (error) {
      console.error('Failed to fetch intelligence data:', error);
    }
  };

  const handleUserSelect = async (user: UserWithRoles) => {
    try {
      // Fetch fresh user data with roles
      const userData = await usersAPI.get(user.id);
      setSelectedUser(userData);
    } catch (error) {
      console.error('Failed to fetch user details:', error);
      alert(`Failed to fetch user details: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleAssignRole = async (roleName: string) => {
    if (!selectedUser) return;

    try {
      await usersAPI.assignRole(selectedUser.id, roleName);

      // Refresh user data
      const updatedUser = await usersAPI.get(selectedUser.id);
      setSelectedUser(updatedUser);

      // Update user in list
      setUsers(prev => prev.map(u =>
        u.id === selectedUser.id ? updatedUser : u
      ));
    } catch (error) {
      console.error('Failed to assign role:', error);
      alert(`Failed to assign role: ${error instanceof Error ? error.message : 'Unknown error'}`);
      throw error;
    }
  };

  const handleRemoveRole = async (roleName: string) => {
    if (!selectedUser) return;

    try {
      await usersAPI.removeRole(selectedUser.id, roleName);

      // Refresh user data
      const updatedUser = await usersAPI.get(selectedUser.id);
      setSelectedUser(updatedUser);

      // Update user in list
      setUsers(prev => prev.map(u =>
        u.id === selectedUser.id ? updatedUser : u
      ));
    } catch (error) {
      console.error('Failed to remove role:', error);
      alert(`Failed to remove role: ${error instanceof Error ? error.message : 'Unknown error'}`);
      throw error;
    }
  };

  const getRoleBadgeColor = (roleName: string) => {
    switch (roleName) {
      case 'admin':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'user':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'viewer':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
      default:
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300';
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
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          User Intelligence
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Comprehensive view of user details, portfolio, activity, and usage metrics
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Users List */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Users ({users.length})
              </h3>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[700px] overflow-y-auto">
              {users.map((user) => (
                <div
                  key={user.id}
                  onClick={() => handleUserSelect(user)}
                  className={`px-6 py-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                    selectedUser?.id === user.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {user.email}
                        </span>
                        {user.name && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            ({user.name})
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {user.roles.map((role) => (
                          <span
                            key={role}
                            className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${getRoleBadgeColor(role)}`}
                          >
                            {role}
                          </span>
                        ))}
                        {user.roles.length === 0 && (
                          <span className="text-xs text-gray-400 dark:text-gray-500 italic">
                            No roles
                          </span>
                        )}
                      </div>
                    </div>
                    {selectedUser?.id === user.id && (
                      <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* User Intelligence Content */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            {selectedUser ? (
              <>
                {/* Tabs Navigation */}
                <div className="border-b border-gray-200 dark:border-gray-700">
                  <nav className="flex space-x-8 px-6" aria-label="Tabs">
                    {tabs.map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                          activeTab === tab.id
                            ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                        }`}
                      >
                        <span className="mr-2">{tab.icon}</span>
                        {tab.label}
                      </button>
                    ))}
                  </nav>
                </div>

                {/* Tab Content */}
                <div className="p-6">
                  {activeTab === 'details' && (
                    <UserDetailsTab
                      user={selectedUser}
                      allRoles={allRoles}
                      onAssignRole={handleAssignRole}
                      onRemoveRole={handleRemoveRole}
                      getRoleBadgeColor={getRoleBadgeColor}
                      quotas={quotas}
                    />
                  )}
                  {activeTab === 'portfolio' && (
                    <UserPortfolioTab
                      user={selectedUser}
                      portfolioSummary={portfolioSummary}
                      portfolioHistory={portfolioHistory}
                      onRefresh={() => fetchIntelligenceData(selectedUser.id)}
                    />
                  )}
                  {activeTab === 'activity' && (
                    <UserActivityTab
                      user={selectedUser}
                      activityData={activityData}
                      onRefresh={() => fetchIntelligenceData(selectedUser.id)}
                    />
                  )}
                  {activeTab === 'usage' && (
                    <UserUsageTab
                      user={selectedUser}
                      usageStats={usageStats}
                      quotas={quotas}
                      onRefresh={() => fetchIntelligenceData(selectedUser.id)}
                    />
                  )}
                </div>
              </>
            ) : (
              <div className="p-6 text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  Select a user from the list to view their intelligence data
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
