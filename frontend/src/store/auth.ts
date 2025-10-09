import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  email: string | null;
  name: string | null;
  user_id: string | null;
  roles: string[];
  loggedIn: boolean;
  accessToken: string | null;
  setAuth: (email: string, name: string, user_id: string, roles?: string[], accessToken?: string) => void;
  logout: () => void;
  hasRole: (role: string) => boolean;
  isAdmin: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      email: null,
      name: null,
      user_id: null,
      roles: [],
      loggedIn: false,
      accessToken: null,
      setAuth: (email: string, name: string, user_id: string, roles: string[] = [], accessToken?: string) => {
        set({ email, name, user_id, roles, loggedIn: true, accessToken: accessToken || null });

        // Also store token for admin API if provided
        if (accessToken) {
          localStorage.setItem('admin_access_token', accessToken);
        }
      },
      logout: () => {
        set({ email: null, name: null, user_id: null, roles: [], loggedIn: false, accessToken: null });
        localStorage.removeItem('admin_access_token');
      },
      hasRole: (role: string) => {
        return get().roles.includes(role);
      },
      isAdmin: () => {
        return get().roles.includes('admin');
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        email: state.email,
        name: state.name,
        user_id: state.user_id,
        roles: state.roles,
        loggedIn: state.loggedIn,
        accessToken: state.accessToken,
      }),
    }
  )
);
