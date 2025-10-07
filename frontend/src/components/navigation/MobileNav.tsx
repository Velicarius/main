import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import { logout as apiLogout } from '../../lib/api';

interface MobileNavProps {
  isOpen: boolean;
  onClose: () => void;
  navItems: Array<{ path: string; label: string }>;
}

export const MobileNav: React.FC<MobileNavProps> = ({ isOpen, onClose, navItems }) => {
  const location = useLocation();
  const { email, loggedIn, logout } = useAuthStore();

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when menu is open
      document.body.style.overflow = 'hidden';
      return () => {
        document.removeEventListener('keydown', handleEscape);
        document.body.style.overflow = '';
      };
    }
  }, [isOpen, onClose]);

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      logout();
      onClose();
      window.location.reload();
    }
  };

  const handleLinkClick = () => {
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-out Menu */}
      <div
        className="fixed top-0 left-0 h-full w-64 bg-slate-900/95 backdrop-blur-xl border-r border-slate-800/50 z-50 md:hidden transform transition-transform duration-300 ease-in-out"
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation menu"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800/50">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">AI</span>
            </div>
            <h2 className="text-lg font-bold text-white">Portfolio</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-2"
            aria-label="Close menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* User Info */}
        {loggedIn && email && (
          <div className="p-4 border-b border-slate-800/50">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center">
                <span className="text-slate-300 font-medium text-sm">
                  {email.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-400">Signed in as</p>
                <p className="text-white font-medium truncate">{email}</p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Links */}
        <nav className="p-4 space-y-2" role="navigation">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={handleLinkClick}
              className={`block px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                location.pathname === item.path
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Logout Button */}
        {loggedIn && (
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-800/50">
            <button
              onClick={handleLogout}
              className="w-full px-4 py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white rounded-lg transition-all duration-200 text-sm font-medium shadow-lg"
            >
              Logout
            </button>
          </div>
        )}
      </div>
    </>
  );
};
