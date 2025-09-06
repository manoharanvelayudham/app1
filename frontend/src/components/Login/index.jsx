import React, { useState } from 'react';
import { Brain, AlertCircle, RefreshCw } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Demo login function for quick testing
  const handleDemoLogin = async () => {
    setEmail('admin@company.com');
    setPassword('admin123');
    setLoading(true);
    setError('');

    try {
      // Simulate demo login
      await login('admin@company.com', 'admin123');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <Brain className="mx-auto h-12 w-12 text-blue-600" />
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Corporate Wellness Platform
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            AI-driven insights and behavioral analysis
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="flex items-center">
                  <AlertCircle className="w-4 h-4 text-red-500 mr-2" />
                  <span className="text-red-700 text-sm">{error}</span>
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
                  placeholder="Enter your email"
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
                  placeholder="Enter your password"
                />
              </div>
            </div>

            <div className="space-y-3">
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

              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Try Demo Login
              </button>
            </div>

            <div className="text-center">
              <div className="bg-blue-50 rounded-lg p-3 text-sm">
                <p className="font-medium text-blue-800 mb-1">Demo Credentials:</p>
                <p className="text-blue-700">Email: admin@company.com</p>
                <p className="text-blue-700">Password: admin123</p>
              </div>
            </div>
          </form>

          {/* Features preview */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Platform Features:</h3>
            <div className="space-y-2 text-xs text-gray-600">
              <div className="flex items-center">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></div>
                <span>AI-powered personality analysis</span>
              </div>
              <div className="flex items-center">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></div>
                <span>Competency gap identification</span>
              </div>
              <div className="flex items-center">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></div>
                <span>Personalized learning programs</span>
              </div>
              <div className="flex items-center">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></div>
                <span>Real-time progress tracking</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;