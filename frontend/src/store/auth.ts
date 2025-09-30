import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  email: string | null;
  name: string | null;
  user_id: string | null;
  loggedIn: boolean;
  setAuth: (email: string, name: string, user_id: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      email: null,
      name: null,
      user_id: null,
      loggedIn: false,
      setAuth: (email: string, name: string, user_id: string) => {
        set({ email, name, user_id, loggedIn: true });
      },
      logout: () => {
        set({ email: null, name: null, user_id: null, loggedIn: false });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        email: state.email,
        name: state.name,
        user_id: state.user_id,
        loggedIn: state.loggedIn,
      }),
    }
  )
);
