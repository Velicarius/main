import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';

interface RequireAdminProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Component that requires admin role to render children
 * If user is not admin, redirects to home page or shows fallback
 *
 * Usage:
 * ```tsx
 * <RequireAdmin>
 *   <AdminPanel />
 * </RequireAdmin>
 * ```
 */
export function RequireAdmin({ children, fallback }: RequireAdminProps) {
  const { loggedIn, isAdmin } = useAuthStore();

  if (!loggedIn) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin()) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

interface RequireRoleProps {
  role: string;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Component that requires a specific role to render children
 *
 * Usage:
 * ```tsx
 * <RequireRole role="ops">
 *   <OpsPanel />
 * </RequireRole>
 * ```
 */
export function RequireRole({ role, children, fallback }: RequireRoleProps) {
  const { loggedIn, hasRole } = useAuthStore();

  if (!loggedIn) {
    return <Navigate to="/login" replace />;
  }

  if (!hasRole(role)) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

interface RequireAnyRoleProps {
  roles: string[];
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Component that requires any of the specified roles to render children
 *
 * Usage:
 * ```tsx
 * <RequireAnyRole roles={["admin", "ops"]}>
 *   <ManagementPanel />
 * </RequireAnyRole>
 * ```
 */
export function RequireAnyRole({ roles, children, fallback }: RequireAnyRoleProps) {
  const { loggedIn, hasRole } = useAuthStore();

  if (!loggedIn) {
    return <Navigate to="/login" replace />;
  }

  const hasAnyRole = roles.some(role => hasRole(role));

  if (!hasAnyRole) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
