import React, { lazy, Suspense } from 'react';
import { RefreshCw } from 'lucide-react';

// Loading component for lazy-loaded components
const LoadingFallback = ({ message = 'Loading...' }) => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center">
      <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
      <p className="text-gray-600">{message}</p>
    </div>
  </div>
);

// Error boundary for lazy components
class LazyErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Lazy component error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="text-red-500 mb-2">⚠️</div>
            <p className="text-gray-600">Failed to load component</p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-2 px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Higher-order component for lazy loading with error boundary
const withLazyLoading = (Component, fallbackMessage) => {
  return React.forwardRef((props, ref) => (
    <LazyErrorBoundary>
      <Suspense fallback={<LoadingFallback message={fallbackMessage} />}>
        <Component {...props} ref={ref} />
      </Suspense>
    </LazyErrorBoundary>
  ));
};

// Lazy-loaded components
export const LazyDashboard = lazy(() => 
  import('./Dashboard').then(module => ({ default: module.default }))
);

export const LazyProgramManagement = lazy(() => 
  import('./Programs').then(module => ({ default: module.default }))
);

export const LazyResponseSystem = lazy(() => 
  import('./Responses').then(module => ({ default: module.default }))
);

export const LazyAIInsightsPanel = lazy(() => 
  import('./AIInsights').then(module => ({ default: module.default }))
);

export const LazyAnalyticsDashboard = lazy(() => 
  import('./Analytics').then(module => ({ default: module.default }))
);

export const LazyAdminPanel = lazy(() => 
  import('./Admin').then(module => ({ default: module.default }))
);

export const LazyThemeCustomizer = lazy(() => 
  import('./Branding/ThemeCustomizer').then(module => ({ default: module.default }))
);

// Pre-configured lazy components with loading messages
export const Dashboard = withLazyLoading(LazyDashboard, 'Loading dashboard...');
export const ProgramManagement = withLazyLoading(LazyProgramManagement, 'Loading programs...');
export const ResponseSystem = withLazyLoading(LazyResponseSystem, 'Loading responses...');
export const AIInsightsPanel = withLazyLoading(LazyAIInsightsPanel, 'Loading AI insights...');
export const AnalyticsDashboard = withLazyLoading(LazyAnalyticsDashboard, 'Loading analytics...');
export const AdminPanel = withLazyLoading(LazyAdminPanel, 'Loading admin panel...');
export const ThemeCustomizer = withLazyLoading(LazyThemeCustomizer, 'Loading theme customizer...');

// Preload utilities for performance optimization
export const preloadComponents = {
  dashboard: () => import('./Dashboard'),
  programs: () => import('./Programs'),
  responses: () => import('./Responses'),
  insights: () => import('./AIInsights'),
  analytics: () => import('./Analytics'),
  admin: () => import('./Admin'),
  branding: () => import('./Branding/ThemeCustomizer'),
};

// Preload critical components on user interaction
export const preloadOnHover = (componentName) => {
  return {
    onMouseEnter: () => {
      if (preloadComponents[componentName]) {
        preloadComponents[componentName]();
      }
    },
  };
};

// Preload components based on user role
export const preloadByRole = (userRole) => {
  const roleBasedPreloads = {
    'ADMIN': ['dashboard', 'programs', 'responses', 'insights', 'analytics', 'admin'],
    'TRAINER': ['dashboard', 'programs', 'responses', 'insights', 'analytics'],
    'CLIENT': ['dashboard', 'programs', 'responses', 'insights'],
  };

  const componentsToPreload = roleBasedPreloads[userRole] || ['dashboard'];
  
  componentsToPreload.forEach(componentName => {
    if (preloadComponents[componentName]) {
      // Preload after a short delay to not block initial render
      setTimeout(() => {
        preloadComponents[componentName]();
      }, 1000);
    }
  });
};

export { LoadingFallback, LazyErrorBoundary, withLazyLoading };
