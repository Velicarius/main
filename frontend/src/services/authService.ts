const API_BASE_URL = 'http://localhost:8001';

interface LoginResponse {
  user_id: string;
  email: string;
  name?: string;
}

interface JWTLoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
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

  async loginJWT(email: string, password: string): Promise<JWTLoginResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
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

  async getJWTTokenForCurrentSession(): Promise<JWTLoginResponse | null> {
    // Try to get JWT token by verifying current session
    // This is a workaround to get JWT token from cookie-based session
    const user = await this.getCurrentUser();

    if (!user.authenticated || !user.email) {
      return null;
    }

    // Unfortunately, we need the password to get JWT token
    // For now, return null and user must re-login with JWT
    return null;
  }

  async verifyJWTToken(token: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/auth/verify?token=${encodeURIComponent(token)}`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error('Token verification failed');
    }

    return await response.json();
  }
}

export const authService = new AuthService();








