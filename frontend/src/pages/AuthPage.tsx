import React, { useState } from 'react';
import { LoginForm } from '../components/auth/LoginForm';
import { RegisterForm } from '../components/auth/RegisterForm';
import { authService } from '../services/authService';
import { useAuthStore } from '../store/auth';

export const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const setAuth = useAuthStore(state => state.setAuth);

  const handleLogin = async (email: string, password: string) => {
    // Use JWT login (all endpoints now use JWT)
    const jwtResponse = await authService.loginJWT(email, password);

    // Verify token to get roles
    const tokenInfo = await authService.verifyJWTToken(jwtResponse.access_token);

    // Store in auth store with token and roles
    setAuth(
      jwtResponse.email,
      jwtResponse.email.split('@')[0], // Use email prefix as name for now
      jwtResponse.user_id,
      tokenInfo.roles || [],
      jwtResponse.access_token
    );

    // Redirect based on role
    if (tokenInfo.roles?.includes('admin')) {
      window.location.href = '/admin';
    } else {
      window.location.href = '/dashboard';
    }
  };

  const handleRegister = async (email: string, name: string, password: string) => {
    await authService.register(email, name, password);
    // После успешной регистрации можно перенаправить пользователя
    window.location.href = '/dashboard';
  };

  return (
    <div>
      {isLogin ? (
        <LoginForm
          onLogin={handleLogin}
          onSwitchToRegister={() => setIsLogin(false)}
        />
      ) : (
        <RegisterForm
          onRegister={handleRegister}
          onSwitchToLogin={() => setIsLogin(true)}
        />
      )}
    </div>
  );
};








