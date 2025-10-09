import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/auth';
import Layout from './components/Layout';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Positions from './pages/Positions';
// import InsightsOptimized from './pages/InsightsOptimized'; // DEPRECATED - use unified insights
import Insights from './pages/Insights';
import UnifiedInsights from './pages/UnifiedInsights';
import News from './pages/News';
import Settings from './pages/Settings';
import Admin from './pages/Admin';

// Protected Route component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { loggedIn } = useAuthStore();
  return loggedIn ? <>{children}</> : <Navigate to="/auth" replace />;
}

function App() {
  const { loggedIn } = useAuthStore();

  return (
    <Routes>
      {/* Auth route - only accessible when not logged in */}
      <Route 
        path="/auth" 
        element={loggedIn ? <Navigate to="/" replace /> : <Auth />} 
      />
      
      {/* Protected routes - only accessible when logged in */}
      <Route 
        path="/*" 
        element={
          <Layout>
            <Routes>
              <Route path="/" element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } />
              <Route path="/positions" element={
                <ProtectedRoute>
                  <Positions />
                </ProtectedRoute>
              } />
            <Route path="/insights" element={
                <ProtectedRoute>
                  <Insights /> 
                </ProtectedRoute>
              } />
              <Route path="/insights-unified" element={
                <ProtectedRoute>
                  <UnifiedInsights />
                </ProtectedRoute>
              } />
              {/* Redirect old URL to new one */}
              <Route path="/insights-v2" element={<Navigate to="/insights" replace />} />
              <Route path="/news" element={
                <ProtectedRoute>
                  <News />
                </ProtectedRoute>
              } />
              <Route path="/settings" element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              } />
              <Route path="/admin" element={
                <ProtectedRoute>
                  <Admin />
                </ProtectedRoute>
              } />
              {/* Redirect any unknown routes to dashboard */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Layout>
        } 
      />
    </Routes>
  );
}

export default App;
