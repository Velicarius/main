const API_BASE_URL = 'http://localhost:8001';

interface LoginResponse {
  user_id: string;
  email: string;
  name: string;
}

interface RegisterResponse {
  user_id: string;
  email: string;
  name: string;
}

interface User {
  authenticated: boolean;
  user_id?: string;
  email?: string;
  name?: string;
}

class AuthService {
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/users/login-json`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Важно для сохранения cookies/sessions
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    return await response.json();
  }

  async register(email: string, name: string, password: string): Promise<RegisterResponse> {
    const response = await fetch(`${API_BASE_URL}/users/register-json`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ email, name, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    return await response.json();
  }

  async logout(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/users/logout`, {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Logout failed');
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      method: 'GET',
      credentials: 'include',
    });

    if (!response.ok) {
      return { authenticated: false };
    }

    return await response.json();
  }

  async checkAuth(): Promise<boolean> {
    const user = await this.getCurrentUser();
    return user.authenticated;
  }
}

export const authService = new AuthService();





