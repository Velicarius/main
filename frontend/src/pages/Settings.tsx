import { useState } from 'react';
import { useAuthStore } from '../store/auth';
import { getBaseUrl, setBaseUrl } from '../lib/api';
import LLMTestPanel from '../components/LLMTestPanel';
import ModelsSection from '../components/ModelsSection';

export default function Settings() {
  const { email, user_id, logout } = useAuthStore();
  const [activeTab, setActiveTab] = useState('profile');
  const [backendUrl, setBackendUrl] = useState(getBaseUrl());
  const [showToast, setShowToast] = useState(false);

  const tabs = [
    { id: 'profile', label: 'Profile', icon: '👤' },
    { id: 'preferences', label: 'Preferences', icon: '⚙️' },
    { id: 'llm-test', label: 'LLM Test', icon: '🔬' },
    { id: 'security', label: 'Security', icon: '🔒' },
    { id: 'about', label: 'About', icon: 'ℹ️' },
  ];

  const handleApplyBackendUrl = () => {
    setBaseUrl(backendUrl);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 2000);
  };

  const handleLogout = async () => {
    if (confirm('Are you sure you want to logout?')) {
      logout();
      window.location.reload();
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
            ⚙️ Settings
          </h1>
          <p className="text-slate-400 mt-2">Manage your account and application preferences</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-4 border border-slate-700/50 shadow-lg">
            <nav className="space-y-2">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/25'
                      : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'
                  }`}
                >
                  <span className="text-lg">{tab.icon}</span>
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50 shadow-lg">
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-white">Profile Information</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                    <div className="px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200">
                      {email || 'Not available'}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">User ID</label>
                    <div className="px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 font-mono text-sm">
                      {user_id || 'Not available'}
                    </div>
                  </div>
                </div>
                <div className="pt-4 border-t border-slate-700/50">
                  <button
                    onClick={handleLogout}
                    className="px-6 py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white rounded-lg transition-all duration-200 shadow-lg shadow-red-500/25 font-medium"
                  >
                    Logout
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'preferences' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-white">Preferences</h2>
                <div className="space-y-4">
                  <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                    <h3 className="font-medium text-white mb-2">Backend URL</h3>
                    <p className="text-sm text-slate-400 mb-4">Configure the API server address</p>
                    <div className="flex gap-3">
                      <input
                        type="text"
                        value={backendUrl}
                        onChange={(e) => setBackendUrl(e.target.value)}
                        placeholder="http://localhost:8001"
                        className="flex-1 px-4 py-3 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 backdrop-blur-sm transition-all duration-200"
                      />
                      <button
                        onClick={handleApplyBackendUrl}
                        className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition-all duration-200 shadow-lg shadow-blue-500/25 font-medium"
                      >
                        Apply
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                    <div>
                      <h3 className="font-medium text-white">Dark Mode</h3>
                      <p className="text-sm text-slate-400">Use dark theme for the application</p>
                    </div>
                    <div className="w-12 h-6 bg-blue-600 rounded-full relative">
                      <div className="w-5 h-5 bg-white rounded-full absolute top-0.5 right-0.5"></div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                    <div>
                      <h3 className="font-medium text-white">Auto-refresh</h3>
                      <p className="text-sm text-slate-400">Automatically refresh portfolio data</p>
                    </div>
                    <div className="w-12 h-6 bg-slate-600 rounded-full relative">
                      <div className="w-5 h-5 bg-white rounded-full absolute top-0.5 left-0.5"></div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                    <div>
                      <h3 className="font-medium text-white">Notifications</h3>
                      <p className="text-sm text-slate-400">Receive portfolio alerts and updates</p>
                    </div>
                    <div className="w-12 h-6 bg-blue-600 rounded-full relative">
                      <div className="w-5 h-5 bg-white rounded-full absolute top-0.5 right-0.5"></div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'llm-test' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-white">LLM Test Panel</h2>
                <p className="text-slate-400">Test and interact with local LLM models</p>
                <div className="space-y-6">
                  <LLMTestPanel />
                  <ModelsSection />
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-white">Security</h2>
                <div className="space-y-4">
                  <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                    <h3 className="font-medium text-white mb-2">Password</h3>
                    <p className="text-sm text-slate-400 mb-4">Change your account password</p>
                    <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
                      Change Password
                    </button>
                  </div>
                  <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                    <h3 className="font-medium text-white mb-2">Two-Factor Authentication</h3>
                    <p className="text-sm text-slate-400 mb-4">Add an extra layer of security to your account</p>
                    <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
                      Enable 2FA
                    </button>
                  </div>
                  <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                    <h3 className="font-medium text-white mb-2">Session Management</h3>
                    <p className="text-sm text-slate-400 mb-4">Manage your active sessions</p>
                    <button className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors">
                      View Sessions
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'about' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-white">About</h2>
                <div className="space-y-4">
                  <div className="p-6 bg-gradient-to-r from-blue-900/20 to-purple-900/20 rounded-lg border border-blue-500/30">
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                        <span className="text-white font-bold text-lg">AI</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white">AI Portfolio</h3>
                        <p className="text-slate-400">Version 1.0.0</p>
                      </div>
                    </div>
                    <p className="text-slate-300 leading-relaxed">
                      AI Portfolio is a modern investment portfolio management platform powered by artificial intelligence. 
                      Get professional insights, risk analysis, and portfolio optimization recommendations.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                      <h4 className="font-medium text-white mb-2">Features</h4>
                      <ul className="text-sm text-slate-400 space-y-1">
                        <li>• AI-powered portfolio analysis</li>
                        <li>• Real-time market data</li>
                        <li>• Risk assessment</li>
                        <li>• Performance tracking</li>
                      </ul>
                    </div>
                    <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600/30">
                      <h4 className="font-medium text-white mb-2">Technology</h4>
                      <ul className="text-sm text-slate-400 space-y-1">
                        <li>• React + TypeScript</li>
                        <li>• FastAPI + Python</li>
                        <li>• OpenAI GPT-4</li>
                        <li>• PostgreSQL</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Toast Notification */}
      {showToast && (
        <div className="fixed top-20 right-4 bg-gradient-to-r from-green-600 to-emerald-600 text-white px-4 py-3 rounded-lg shadow-xl z-50 backdrop-blur-sm border border-green-500/20">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-white rounded-full"></div>
            <span className="text-sm font-medium">Backend URL updated</span>
          </div>
        </div>
      )}
    </div>
  );
}
