import React, { useState } from 'react';
import { LoginForm } from '../components/auth/LoginForm';
import { RegisterForm } from '../components/auth/RegisterForm';
import { authService } from '../services/authService';

export const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);

  const handleLogin = async (email: string, password: string) => {
    await authService.login(email, password);
    // После успешного логина можно перенаправить пользователя
    window.location.href = '/dashboard';
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







