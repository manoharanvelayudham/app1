import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      // Validate token and get user info
      apiRequest('/users/me')
        .then(userData => {
          setUser(userData);
        })
        .catch(() => {
          localStorage.clear();
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const apiRequest = async (endpoint, options = {}) => {
    const token = localStorage.getItem('access_token');
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers
    };

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
      });

      if (response.status === 401) {
        // Try to refresh token
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          try {
            const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ refresh_token: refreshToken })
            });
            
            if (refreshResponse.ok) {
              const { access_token } = await refreshResponse.json();
              localStorage.setItem('access_token', access_token);
              // Retry original request
              return apiRequest(endpoint, options);
            }
          } catch (refreshError) {
            localStorage.clear();
            window.location.href = '/login';
            throw refreshError;
          }
        }
        localStorage.clear();
        window.location.href = '/login';
        throw new Error('Authentication failed');
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Request failed');
      }

      return response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  };

  const login = async (email, password) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const { access_token, refresh_token, user: userData } = await response.json();
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      setUser(userData);
      return userData;
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.clear();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, apiRequest }}>
      {children}
    </AuthContext.Provider>
  );
};