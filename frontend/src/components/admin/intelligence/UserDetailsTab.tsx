import { useState } from 'react';
import type { UserWithRoles, Role, UserQuotas } from '../../../lib/api-admin';

interface UserDetailsTabProps {
  user: UserWithRoles;
  allRoles: Role[];
  onAssignRole: (roleName: string) => Promise<void>;
  onRemoveRole: (roleName: string) => Promise<void>;
  getRoleBadgeColor: (roleName: string) => string;
  quotas: UserQuotas | null;
}

export default function UserDetailsTab({
  user,
  allRoles,
  onAssignRole,
  onRemoveRole,
  getRoleBadgeColor,
  quotas,
}: UserDetailsTabProps) {
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [selectedRoleToAdd, setSelectedRoleToAdd] = useState<string>('');

  const getAvailableRoles = () => {
    return allRoles.filter(role => !user.roles.includes(role.name));
  };

  const handleAssignRole = async () => {
    if (!selectedRoleToAdd) return;

    try {
      await onAssignRole(selectedRoleToAdd);
      setShowRoleModal(false);
      setSelectedRoleToAdd('');
    } catch (error) {
      // Error is already handled in parent
    }
  };

  const handleRemoveRole = async (roleName: string) => {
    if (!confirm(`Remove role "${roleName}" from ${user.email}?`)) {
      return;
    }

    try {
      await onRemoveRole(roleName);
    } catch (error) {
      // Error is already handled in parent
    }
  };

  return (
    <div className="space-y-6">
      {/* User Basic Info */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          User Information
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              Email
            </label>
            <p className="text-sm text-gray-900 dark:text-white mt-1">
              {user.email}
            </p>
          </div>

          {user.name && (
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Name
              </label>
              <p className="text-sm text-gray-900 dark:text-white mt-1">
                {user.name}
              </p>
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              User ID
            </label>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 font-mono">
              {user.id}
            </p>
          </div>

          {user.usd_balance !== undefined && (
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Balance
              </label>
              <p className="text-sm text-gray-900 dark:text-white mt-1">
                ${user.usd_balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD
              </p>
            </div>
          )}

          {user.created_at && (
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Member Since
              </label>
              <p className="text-sm text-gray-900 dark:text-white mt-1">
                {new Date(user.created_at).toLocaleDateString()}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Plan Information */}
      {quotas?.plan && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Subscription Plan
          </h3>
          <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-start justify-between">
              <div>
                <h4 className="text-lg font-bold text-blue-900 dark:text-blue-100">
                  {quotas.plan.name}
                </h4>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                  Plan Code: {quotas.plan.code}
                </p>
              </div>
              <span className="inline-flex px-3 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                Active
              </span>
            </div>

            {/* Plan Limits */}
            {quotas.plan.limits && Object.keys(quotas.plan.limits).length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-medium text-blue-700 dark:text-blue-300 uppercase mb-2">
                  Plan Limits
                </p>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(quotas.plan.limits).map(([key, value]) => (
                    <div key={key} className="bg-white dark:bg-gray-800 p-2 rounded">
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {key.replace(/_/g, ' ')}
                      </p>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Plan Features */}
            {quotas.plan.features && Object.keys(quotas.plan.features).length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-medium text-blue-700 dark:text-blue-300 uppercase mb-2">
                  Features
                </p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(quotas.plan.features).map(([key, value]) => (
                    <span
                      key={key}
                      className={`inline-flex px-2 py-1 text-xs rounded-full ${
                        value === true
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                      }`}
                    >
                      {key.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Roles Section */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Assigned Roles
          </h3>
          <button
            onClick={() => setShowRoleModal(true)}
            disabled={getAvailableRoles().length === 0}
            className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            + Add Role
          </button>
        </div>

        <div className="space-y-2">
          {user.roles.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">
              No roles assigned
            </p>
          ) : (
            user.roles.map((roleName) => {
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

      {/* Add Role Modal */}
      {showRoleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Assign Role to {user.email}
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
