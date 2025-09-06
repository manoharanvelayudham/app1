import React from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

// Create a client with optimized settings for enterprise use
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache for 5 minutes by default
      staleTime: 5 * 60 * 1000,
      // Keep data in cache for 10 minutes
      cacheTime: 10 * 60 * 1000,
      // Retry failed requests 3 times
      retry: 3,
      // Retry with exponential backoff
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // Refetch on window focus for real-time data
      refetchOnWindowFocus: true,
      // Don't refetch on reconnect to avoid spam
      refetchOnReconnect: false,
      // Background refetch interval (5 minutes for dashboards)
      refetchInterval: false,
    },
    mutations: {
      // Retry mutations once
      retry: 1,
      // Show loading states
      onError: (error) => {
        console.error('Mutation error:', error);
        // In production, you might want to show a toast notification
      },
    },
  },
});

// Query keys for consistent caching
export const queryKeys = {
  // User-related queries
  user: ['user'],
  userProfile: ['user', 'profile'],
  userPreferences: ['user', 'preferences'],
  
  // Dashboard queries
  dashboard: ['dashboard'],
  dashboardStats: ['dashboard', 'stats'],
  recentActivity: ['dashboard', 'activity'],
  
  // Program queries
  programs: ['programs'],
  program: (id) => ['programs', id],
  userPrograms: ['programs', 'user'],
  programEnrollments: (id) => ['programs', id, 'enrollments'],
  
  // Response queries
  responses: ['responses'],
  response: (id) => ['responses', id],
  userResponses: ['responses', 'user'],
  programResponses: (programId) => ['responses', 'program', programId],
  
  // AI Insights queries
  aiInsights: ['ai-insights'],
  userInsights: ['ai-insights', 'user'],
  insightDetails: (id) => ['ai-insights', id],
  
  // Analytics queries
  analytics: ['analytics'],
  userAnalytics: ['analytics', 'user'],
  programAnalytics: (id) => ['analytics', 'program', id],
  
  // System queries
  systemHealth: ['system', 'health'],
  systemConfig: ['system', 'config'],
  
  // Branding queries
  branding: ['branding'],
  theme: ['branding', 'theme'],
  logo: ['branding', 'logo'],
};

// Custom hooks for common queries
export const useInvalidateQueries = () => {
  const queryClient = useQueryClient();
  
  return {
    invalidateUser: () => queryClient.invalidateQueries(queryKeys.user),
    invalidateDashboard: () => queryClient.invalidateQueries(queryKeys.dashboard),
    invalidatePrograms: () => queryClient.invalidateQueries(queryKeys.programs),
    invalidateResponses: () => queryClient.invalidateQueries(queryKeys.responses),
    invalidateInsights: () => queryClient.invalidateQueries(queryKeys.aiInsights),
    invalidateAll: () => queryClient.invalidateQueries(),
  };
};

// Prefetch utilities for performance optimization
export const prefetchQueries = {
  dashboard: (queryClient) => {
    return queryClient.prefetchQuery({
      queryKey: queryKeys.dashboardStats,
      queryFn: () => import('../utils/api').then(api => api.default.get('/dashboard/stats')),
      staleTime: 2 * 60 * 1000, // 2 minutes
    });
  },
  
  userPrograms: (queryClient) => {
    return queryClient.prefetchQuery({
      queryKey: queryKeys.userPrograms,
      queryFn: () => import('../utils/api').then(api => api.default.get('/programs/user')),
      staleTime: 5 * 60 * 1000, // 5 minutes
    });
  },
  
  userInsights: (queryClient) => {
    return queryClient.prefetchQuery({
      queryKey: queryKeys.userInsights,
      queryFn: () => import('../utils/api').then(api => api.default.get('/ai-insights/user')),
      staleTime: 10 * 60 * 1000, // 10 minutes
    });
  },
};

// Background sync for offline support
export const backgroundSync = {
  syncPendingMutations: async () => {
    // This would sync any pending mutations when back online
    const mutations = queryClient.getMutationCache().getAll();
    const pendingMutations = mutations.filter(mutation => mutation.state.status === 'loading');
    
    for (const mutation of pendingMutations) {
      try {
        await mutation.execute();
      } catch (error) {
        console.error('Background sync failed for mutation:', error);
      }
    }
  },
  
  refreshCriticalData: async () => {
    // Refresh critical data when back online
    await Promise.allSettled([
      queryClient.refetchQueries(queryKeys.user),
      queryClient.refetchQueries(queryKeys.dashboardStats),
      queryClient.refetchQueries(queryKeys.userPrograms),
    ]);
  },
};

const QueryProvider = ({ children }) => {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools 
          initialIsOpen={false} 
          position="bottom-right"
          toggleButtonProps={{
            style: {
              marginLeft: '5px',
              transform: 'scale(0.8)',
            },
          }}
        />
      )}
    </QueryClientProvider>
  );
};

export { queryClient };
export default QueryProvider;
