import { useState, useEffect } from 'react';
import { usersAPI, rolesAPI, type UserWithRoles, type Role } from '../../lib/api-admin';

export default function UserManagementPanel() {
  const [users, setUsers] = useState<UserWithRoles[]>([]);
  const [allRoles, setAllRoles] = useState<Role[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserWithRoles | null>(null);
  const [loading, setLoading] = useState(true);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [selectedRoleToAdd, setSelectedRoleToAdd] = useState<string>('');

  useEffect(() => {
    fetchUsers();
    fetchRoles();
  }, []);

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

  const handleAssignRole = async () => {
    if (!selectedUser || !selectedRoleToAdd) return;

    try {
      await usersAPI.assignRole(selectedUser.id, selectedRoleToAdd);

      // Refresh user data
      const updatedUser = await usersAPI.get(selectedUser.id);
      setSelectedUser(updatedUser);

      // Update user in list
      setUsers(prev => prev.map(u =>
        u.id === selectedUser.id ? updatedUser : u
      ));

      setShowRoleModal(false);
      setSelectedRoleToAdd('');
    } catch (error) {
      console.error('Failed to assign role:', error);
      alert(`Failed to assign role: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleRemoveRole = async (roleName: string) => {
    if (!selectedUser) return;

    if (!confirm(`Remove role "${roleName}" from ${selectedUser.email}?`)) {
      return;
    }

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
    }
  };

  const getAvailableRoles = () => {
    if (!selectedUser) return allRoles;
    return allRoles.filter(role => !selectedUser.roles.includes(role.name));
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
          User Management
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Manage users and their role assignments
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Users List */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Users ({users.length})
            </h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[600px] overflow-y-auto">
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
                          No roles assigned
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

        {/* User Details */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {selectedUser ? 'User Details' : 'Select a User'}
            </h3>
          </div>

          {selectedUser ? (
            <div className="p-6 space-y-6">
              {/* User Info */}
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Email
                  </label>
                  <p className="text-sm text-gray-900 dark:text-white mt-1">
                    {selectedUser.email}
                  </p>
                </div>

                {selectedUser.name && (
                  <div>
                    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      Name
                    </label>
                    <p className="text-sm text-gray-900 dark:text-white mt-1">
                      {selectedUser.name}
                    </p>
                  </div>
                )}

                <div>
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    User ID
                  </label>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 font-mono">
                    {selectedUser.id}
                  </p>
                </div>

                {selectedUser.usd_balance !== undefined && (
                  <div>
                    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      Balance
                    </label>
                    <p className="text-sm text-gray-900 dark:text-white mt-1">
                      ${selectedUser.usd_balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD
                    </p>
                  </div>
                )}
              </div>

              {/* Roles Section */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Assigned Roles
                  </label>
                  <button
                    onClick={() => setShowRoleModal(true)}
                    disabled={getAvailableRoles().length === 0}
                    className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    + Add Role
                  </button>
                </div>

                <div className="space-y-2">
                  {selectedUser.roles.length === 0 ? (
                    <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                      No roles assigned
                    </p>
                  ) : (
                    selectedUser.roles.map((roleName) => {
                      const roleDetails = allRoles.find(r => r.name === roleName);
                      return (
                        <div
                          key={roleName}
                          className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                        >
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRoleBadgeColor(roleName)}`}>
                                {roleName}
                              </span>
                            </div>
                            {roleDetails?.description && (
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {roleDetails.description}
                              </p>
                            )}
                          </div>
                          <button
                            onClick={() => handleRemoveRole(roleName)}
                            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                            title="Remove role"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Select a user from the list to view and manage their details
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Add Role Modal */}
      {showRoleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Assign Role to {selectedUser?.email}
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Select Role
                </label>
                <select
                  value={selectedRoleToAdd}
                  onChange={(e) => setSelectedRoleToAdd(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">-- Select a role --</option>
                  {getAvailableRoles().map((role) => (
                    <option key={role.id} value={role.name}>
                      {role.name} {role.description && `- ${role.description}`}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowRoleModal(false);
                    setSelectedRoleToAdd('');
                  }}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAssignRole}
                  disabled={!selectedRoleToAdd}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Assign Role
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
