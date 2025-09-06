import React, { useState, useEffect, createContext, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  BarChart3, 
  Users, 
  BookOpen, 
  MessageSquare, 
  Brain, 
  Settings, 
  LogOut, 
  User, 
  Palette,
  RefreshCw
} from 'lucide-react';

// Import enhanced utilities and components
import apiClient, { APIError } from './utils/api';
import QueryProvider, { queryKeys, prefetchQueries } from './contexts/QueryProvider';
import { defaultTheme, applyThemeToDocument } from './theme';
import { 
  Dashboard, 
  ProgramManagement, 
  ResponseSystem, 
  AIInsightsPanel, 
  AdminPanel,
  preloadByRole,
  preloadOnHover
} from './components/LazyComponents';
import { ThemeCustomizer } from './components/Branding';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Theme Context
const ThemeContext = createContext();

const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// Auth Context
const AuthContext = createContext();

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Theme Provider Component
const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('app_theme');
    return savedTheme ? JSON.parse(savedTheme) : defaultTheme;
  });

  const updateTheme = (newTheme) => {
    setTheme(newTheme);
    localStorage.setItem('app_theme', JSON.stringify(newTheme));
    applyThemeToDocument(newTheme);
  };

  useEffect(() => {
    applyThemeToDocument(theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, updateTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

// Enhanced Auth Provider with React Query
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  // User query
  const { data: userData, error: userError } = useQuery({
    queryKey: queryKeys.user,
    queryFn: () => apiClient.get('/users/me'),
    enabled: !!localStorage.getItem('access_token'),
    retry: false,
    onSuccess: (data) => {
      setUser(data);
      // Preload components based on user role
      preloadByRole(data.role);
      // Prefetch critical data
      prefetchQueries.dashboard(queryClient);
      prefetchQueries.userPrograms(queryClient);
      prefetchQueries.userInsights(queryClient);
    },
    onError: () => {
      localStorage.clear();
      setUser(null);
    },
    onSettled: () => {
      setLoading(false);
    }
  });

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: async ({ email, password }) => {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new APIError(errorData.detail || 'Login failed', response.status, errorData);
      }

      return response.json();
    },
    onSuccess: ({ access_token, refresh_token, user: userData }) => {
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      setUser(userData);
      queryClient.setQueryData(queryKeys.user, userData);
      
      // Preload components and data for the user
      preloadByRole(userData.role);
      setTimeout(() => {
        prefetchQueries.dashboard(queryClient);
        prefetchQueries.userPrograms(queryClient);
        prefetchQueries.userInsights(queryClient);
      }, 100);
    }
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: () => apiClient.post('/auth/logout'),
    onSettled: () => {
      localStorage.clear();
      setUser(null);
      queryClient.clear();
    }
  });

  const login = (email, password) => {
    return loginMutation.mutateAsync({ email, password });
  };

  const logout = () => {
    logoutMutation.mutate();
  };

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ 
      user, 
      login, 
      logout, 
      loading: loading || loginMutation.isLoading,
      loginError: loginMutation.error
    }}>
      {children}
    </AuthContext.Provider>
  );
};

// Enhanced Login Component
const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, loading, loginError } = useAuth();
  const { theme } = useTheme();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(email, password);
    } catch (error) {
      // Error is handled by the mutation
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          {theme.branding.logoUrl ? (
            <img
              src={theme.branding.logoUrl}
              alt="Company Logo"
              className="mx-auto h-12 w-auto"
            />
          ) : (
            <Brain className="mx-auto h-12 w-12 text-blue-600" />
          )}
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            {theme.branding.companyName}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {theme.branding.tagline}
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {loginError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="flex items-center">
                  <span className="text-red-700 text-sm">{loginError.message}</span>
                </div>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <div className="mt-1">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  'Sign in'
                )}
              </button>
            </div>

            <div className="text-center">
              <p className="text-sm text-gray-600">
                Demo credentials: admin@company.com / admin123
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Enhanced Navigation Component
const Navigation = ({ currentView, setCurrentView }) => {
  const { user, logout } = useAuth();
  const { theme } = useTheme();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'programs', label: 'Programs', icon: BookOpen },
    { id: 'responses', label: 'Responses', icon: MessageSquare },
    { id: 'insights', label: 'AI Insights', icon: Brain },
  ];

  if (user?.role === 'ADMIN') {
    navItems.push(
      { id: 'admin', label: 'Admin', icon: Settings },
      { id: 'branding', label: 'Branding', icon: Palette }
    );
  }

  return (
    <div className="bg-white shadow-sm border-r border-gray-200 h-full">
      <div className="p-6">
        <div className="flex items-center space-x-3">
          {theme.branding.logoUrl ? (
            <img
              src={theme.branding.logoUrl}
              alt="Company Logo"
              className="w-8 h-8 object-contain"
            />
          ) : (
            <Brain className="w-8 h-8 text-blue-600" />
          )}
          <div>
            <h1 className="text-lg font-semibold text-gray-900">
              {theme.branding.companyName.split(' ').slice(0, 2).join(' ')}
            </h1>
            <p className="text-xs text-gray-500">Enterprise Edition</p>
          </div>
        </div>
      </div>

      <nav className="px-4 space-y-2">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setCurrentView(item.id)}
            className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              currentView === item.id
                ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}
            {...preloadOnHover(item.id)}
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.label}
          </button>
        ))}
      </nav>

      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {user?.full_name || user?.email}
            </p>
            <p className="text-xs text-gray-500 capitalize">
              {user?.role?.toLowerCase()}
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4 mr-3" />
          Sign out
        </button>
      </div>
    </div>
  );
};

// Main App Component
const MainApp = () => {
  const [currentView, setCurrentView] = useState('dashboard');
  const { user, loading } = useAuth();
  const { theme } = useTheme();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'programs':
        return <ProgramManagement />;
      case 'responses':
        return <ResponseSystem />;
      case 'insights':
        return <AIInsightsPanel />;
      case 'admin':
        return user?.role === 'ADMIN' ? <AdminPanel /> : <Dashboard />;
      case 'branding':
        return user?.role === 'ADMIN' ? (
          <ThemeCustomizer 
            onThemeChange={(newTheme) => theme.updateTheme(newTheme)}
            currentTheme={theme}
          />
        ) : <Dashboard />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <div className="w-64 flex-shrink-0">
        <Navigation currentView={currentView} setCurrentView={setCurrentView} />
      </div>
      <div className="flex-1 overflow-auto">
        <main className="p-8">
          {renderView()}
        </main>
      </div>
    </div>
  );
};

// Root App Component with all providers
const App = () => {
  useEffect(() => {
    // Register service worker for PWA
    if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
      navigator.serviceWorker.register('/serviceWorker.js')
        .then((registration) => {
          console.log('SW registered: ', registration);
          
          // Request notification permission
          if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
          }
        })
        .catch((registrationError) => {
          console.log('SW registration failed: ', registrationError);
        });
    }
  }, []);

  return (
    <QueryProvider>
      <ThemeProvider>
        <AuthProvider>
          <MainApp />
        </AuthProvider>
      </ThemeProvider>
    </QueryProvider>
  );
};

export default App;