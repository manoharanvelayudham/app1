// Enhanced API utility with comprehensive JWT handling and error management
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

class APIClient {
  constructor() {
    this.refreshPromise = null;
  }

  async refreshToken() {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this._performTokenRefresh();
    
    try {
      const result = await this.refreshPromise;
      this.refreshPromise = null;
      return result;
    } catch (error) {
      this.refreshPromise = null;
      throw error;
    }
  }

  async _performTokenRefresh() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (!response.ok) {
      localStorage.clear();
      window.location.href = '/login';
      throw new Error('Token refresh failed');
    }

    const { access_token, refresh_token: newRefreshToken } = await response.json();
    localStorage.setItem('access_token', access_token);
    
    if (newRefreshToken) {
      localStorage.setItem('refresh_token', newRefreshToken);
    }

    return access_token;
  }

  async request(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    const isFormData = options.body instanceof FormData;
    
    const headers = {
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...(!isFormData && { 'Content-Type': 'application/json' }),
      ...options.headers
    };

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401 && token) {
        try {
          await this.refreshToken();
          
          // Retry request with new token
          const newToken = localStorage.getItem('access_token');
          const retryHeaders = {
            ...headers,
            'Authorization': `Bearer ${newToken}`
          };
          
          const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...config,
            headers: retryHeaders
          });

          if (!retryResponse.ok) {
            const errorData = await this._parseErrorResponse(retryResponse);
            throw new APIError(
              errorData.detail || 'Request failed after token refresh',
              retryResponse.status,
              errorData
            );
          }

          return this._parseResponse(retryResponse);
        } catch (refreshError) {
          localStorage.clear();
          window.location.href = '/login';
          throw new APIError('Authentication failed', 401, { detail: 'Token refresh failed' });
        }
      }

      if (!response.ok) {
        const errorData = await this._parseErrorResponse(response);
        throw new APIError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData
        );
      }

      return this._parseResponse(response);
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      
      // Network or other errors
      console.error('API Request failed:', error);
      throw new APIError('Network error or server unavailable', 0, { detail: error.message });
    }
  }

  async _parseResponse(response) {
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }
    
    return response.text();
  }

  async _parseErrorResponse(response) {
    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      return { detail: await response.text() };
    } catch {
      return { detail: `HTTP ${response.status}: ${response.statusText}` };
    }
  }

  // Convenience methods
  async get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  async post(endpoint, data, options = {}) {
    const body = data instanceof FormData ? data : JSON.stringify(data);
    return this.request(endpoint, { ...options, method: 'POST', body });
  }

  async put(endpoint, data, options = {}) {
    const body = data instanceof FormData ? data : JSON.stringify(data);
    return this.request(endpoint, { ...options, method: 'PUT', body });
  }

  async patch(endpoint, data, options = {}) {
    const body = data instanceof FormData ? data : JSON.stringify(data);
    return this.request(endpoint, { ...options, method: 'PATCH', body });
  }

  async delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }

  // File upload with progress tracking
  async uploadFile(endpoint, file, onProgress = null, additionalData = {}) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      
      formData.append('file', file);
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });

      // Progress tracking
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            onProgress(percentComplete);
          }
        });
      }

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch {
            resolve(xhr.responseText);
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new APIError(error.detail || 'Upload failed', xhr.status, error));
          } catch {
            reject(new APIError(`Upload failed: ${xhr.statusText}`, xhr.status));
          }
        }
      });

      xhr.addEventListener('error', () => {
        reject(new APIError('Network error during upload', 0));
      });

      const token = localStorage.getItem('access_token');
      xhr.open('POST', `${API_BASE_URL}${endpoint}`);
      
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.send(formData);
    });
  }
}

// Create singleton instance
const apiClient = new APIClient();

// Export both the class and instance
export { APIClient, APIError };
export default apiClient;

// Legacy compatibility - maintain the same interface as the original apiRequest
export const apiRequest = (endpoint, options = {}) => {
  return apiClient.request(endpoint, options);
};

// Mock data for development/demo purposes
export const mockData = {
  dashboardStats: {
    total_users: 245,
    active_programs: 12,
    completed_responses: 1543,
    ai_insights_generated: 89,
    recent_activity: [
      { id: 1, type: 'enrollment', message: 'John Doe enrolled in Leadership Development', timestamp: '2 hours ago' },
      { id: 2, type: 'response', message: 'Sarah Smith submitted response for Team Collaboration', timestamp: '4 hours ago' },
      { id: 3, type: 'insight', message: 'AI generated new insights for Marketing Team', timestamp: '6 hours ago' }
    ]
  },

  programs: [
    { id: 1, title: 'Leadership Development', description: 'Enhance leadership skills and capabilities', difficulty: 'intermediate', duration: '6 weeks', enrolled: 45 },
    { id: 2, title: 'Team Collaboration', description: 'Improve team dynamics and communication', difficulty: 'beginner', duration: '4 weeks', enrolled: 67 },
    { id: 3, title: 'Innovation Mindset', description: 'Foster creativity and innovative thinking', difficulty: 'advanced', duration: '8 weeks', enrolled: 32 }
  ],

  responses: [
    { id: 1, program_title: 'Leadership Development', content: 'My leadership style has evolved significantly through this program. I\'ve learned to balance authority with empathy...', type: 'text', status: 'submitted', created_at: '2024-01-15' },
    { id: 2, program_title: 'Team Collaboration', content: 'Working with diverse teams has taught me the importance of active listening and clear communication...', type: 'text', status: 'draft', created_at: '2024-01-14' },
    { id: 3, program_title: 'Innovation Mindset', content: 'Innovation requires stepping out of comfort zones and challenging conventional thinking...', type: 'text', status: 'reviewed', created_at: '2024-01-13' }
  ],

  aiInsights: [
    { id: 1, category: 'Leadership', insight: 'Shows strong potential in strategic thinking and decision-making processes', confidence_score: 0.85, priority: 'high' },
    { id: 2, category: 'Communication', insight: 'Excellent written communication skills with room for improvement in verbal presentation', confidence_score: 0.78, priority: 'medium' },
    { id: 3, category: 'Teamwork', insight: 'Could benefit from active listening training and conflict resolution skills', confidence_score: 0.72, priority: 'high' },
    { id: 4, category: 'Innovation', insight: 'Demonstrates creative problem-solving abilities and open-mindedness to new ideas', confidence_score: 0.81, priority: 'medium' }
  ],

  analytics: {
    personality_score: 78,
    competency_gaps: ['Active Listening', 'Strategic Planning', 'Conflict Resolution'],
    recommendations_count: 5,
    growth_trend: 'positive'
  },

  adminUsers: [
    { id: 1, name: 'John Doe', email: 'john@company.com', role: 'CLIENT', status: 'active', last_login: '2024-01-15' },
    { id: 2, name: 'Jane Smith', email: 'jane@company.com', role: 'TRAINER', status: 'active', last_login: '2024-01-14' },
    { id: 3, name: 'Bob Johnson', email: 'bob@company.com', role: 'CLIENT', status: 'inactive', last_login: '2024-01-10' },
    { id: 4, name: 'Alice Wilson', email: 'alice@company.com', role: 'ADMIN', status: 'active', last_login: '2024-01-15' }
  ],

  systemHealth: {
    database: 'healthy',
    ai_service: 'healthy',
    api_response_time: '125ms',
    uptime: '99.9%',
    last_backup: '2024-01-15 02:00:00',
    active_connections: 47
  }
};

// API service functions that can switch between mock and real API
export const apiService = {
  // Dashboard APIs
  getDashboardStats: async () => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // In production, replace with:
    // return apiRequest('/dashboard/stats');
    return mockData.dashboardStats;
  },

  // Program APIs
  getPrograms: async () => {
    await new Promise(resolve => setTimeout(resolve, 800));
    // return apiRequest('/programs/');
    return mockData.programs;
  },

  enrollInProgram: async (programId) => {
    await new Promise(resolve => setTimeout(resolve, 500));
    // return apiRequest('/enrollments/', { 
    //   method: 'POST', 
    //   body: JSON.stringify({ program_id: programId }) 
    // });
    return { success: true, message: 'Enrolled successfully' };
  },

  // Response APIs
  getMyResponses: async () => {
    await new Promise(resolve => setTimeout(resolve, 600));
    // return apiRequest('/responses/me');
    return mockData.responses;
  },

  createResponse: async (responseData) => {
    await new Promise(resolve => setTimeout(resolve, 700));
    // return apiRequest('/responses/', {
    //   method: 'POST',
    //   body: JSON.stringify(responseData)
    // });
    return { id: Date.now(), ...responseData, created_at: new Date().toISOString() };
  },

  updateResponse: async (responseId, responseData) => {
    await new Promise(resolve => setTimeout(resolve, 500));
    // return apiRequest(`/responses/${responseId}`, {
    //   method: 'PUT',
    //   body: JSON.stringify(responseData)
    // });
    return { success: true };
  },

  deleteResponse: async (responseId) => {
    await new Promise(resolve => setTimeout(resolve, 400));
    // return apiRequest(`/responses/${responseId}`, { method: 'DELETE' });
    return { success: true };
  },

  // AI & Analytics APIs
  getAIInsights: async () => {
    await new Promise(resolve => setTimeout(resolve, 900));
    // return apiRequest('/api/v1/ai/insights/me');
    return mockData.aiInsights;
  },

  getAnalyticsSummary: async (userId) => {
    await new Promise(resolve => setTimeout(resolve, 800));
    // return apiRequest(`/api/v1/ai/analytics/summary/${userId}`);
    return mockData.analytics;
  },

  generateNewInsights: async (userId) => {
    await new Promise(resolve => setTimeout(resolve, 2000));
    // return apiRequest(`/api/v1/ai/generate-insights/${userId}`, { method: 'POST' });
    return { success: true, insights_generated: 3 };
  },

  // Admin APIs
  getAllUsers: async () => {
    await new Promise(resolve => setTimeout(resolve, 800));
    // return apiRequest('/users/');
    return mockData.adminUsers;
  },

  getSystemHealth: async () => {
    await new Promise(resolve => setTimeout(resolve, 500));
    // return apiRequest('/health');
    return mockData.systemHealth;
  },

  createUser: async (userData) => {
    await new Promise(resolve => setTimeout(resolve, 600));
    // return apiRequest('/users/', {
    //   method: 'POST',
    //   body: JSON.stringify(userData)
    // });
    return { id: Date.now(), ...userData };
  },

  updateUser: async (userId, userData) => {
    await new Promise(resolve => setTimeout(resolve, 500));
    // return apiRequest(`/users/${userId}`, {
    //   method: 'PUT',
    //   body: JSON.stringify(userData)
    // });
    return { success: true };
  },

  deleteUser: async (userId) => {
    await new Promise(resolve => setTimeout(resolve, 400));
    // return apiRequest(`/users/${userId}`, { method: 'DELETE' });
    return { success: true };
  }
};

// Utility functions
export const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

export const getStatusColor = (status) => {
  const statusColors = {
    'submitted': 'bg-green-100 text-green-800',
    'draft': 'bg-yellow-100 text-yellow-800',
    'reviewed': 'bg-blue-100 text-blue-800',
    'active': 'bg-green-100 text-green-800',
    'inactive': 'bg-red-100 text-red-800',
    'pending': 'bg-yellow-100 text-yellow-800'
  };
  return statusColors[status] || 'bg-gray-100 text-gray-800';
};

export const getDifficultyColor = (difficulty) => {
  const difficultyColors = {
    'beginner': 'bg-green-100 text-green-800',
    'intermediate': 'bg-yellow-100 text-yellow-800',
    'advanced': 'bg-red-100 text-red-800'
  };
  return difficultyColors[difficulty] || 'bg-gray-100 text-gray-800';
};

export const getPriorityColor = (priority) => {
  const priorityColors = {
    'high': 'bg-red-100 text-red-800',
    'medium': 'bg-yellow-100 text-yellow-800',
    'low': 'bg-green-100 text-green-800'
  };
  return priorityColors[priority] || 'bg-gray-100 text-gray-800';
};