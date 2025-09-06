import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import { 
  TrendingUp, 
  Users, 
  Target, 
  Award, 
  Calendar, 
  Download,
  Filter,
  RefreshCw
} from 'lucide-react';
import { apiService } from '../../utils/api';

const Analytics = () => {
  const [dateRange, setDateRange] = useState('30');
  const [selectedMetric, setSelectedMetric] = useState('all');

  // Fetch analytics data
  const { data: analyticsData, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics', dateRange, selectedMetric],
    queryFn: () => apiService.get(`/analytics/dashboard?days=${dateRange}&metric=${selectedMetric}`),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const { data: programMetrics } = useQuery({
    queryKey: ['program-metrics', dateRange],
    queryFn: () => apiService.get(`/analytics/programs?days=${dateRange}`),
    staleTime: 5 * 60 * 1000,
  });

  const { data: userProgress } = useQuery({
    queryKey: ['user-progress', dateRange],
    queryFn: () => apiService.get(`/analytics/progress?days=${dateRange}`),
    staleTime: 5 * 60 * 1000,
  });

  // Sample data for charts (fallback if API data not available)
  const sampleEngagementData = [
    { name: 'Week 1', engagement: 65, completion: 45 },
    { name: 'Week 2', engagement: 72, completion: 52 },
    { name: 'Week 3', engagement: 68, completion: 48 },
    { name: 'Week 4', engagement: 78, completion: 65 },
  ];

  const sampleProgramData = [
    { name: 'Fitness', value: 35, color: '#3B82F6' },
    { name: 'Nutrition', value: 25, color: '#10B981' },
    { name: 'Mental Health', value: 20, color: '#F59E0B' },
    { name: 'Sleep', value: 20, color: '#EF4444' },
  ];

  const handleExport = async () => {
    try {
      const response = await apiService.get('/export/analytics', {
        params: { days: dateRange, format: 'csv' },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `analytics-${dateRange}days.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600">Loading analytics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Failed to load analytics data</p>
        <button 
          onClick={() => refetch()}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const engagementData = analyticsData?.engagement || sampleEngagementData;
  const programDistribution = programMetrics?.distribution || sampleProgramData;
  const progressData = userProgress?.trends || sampleEngagementData;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-gray-600 mt-1">Comprehensive insights into wellness program performance</p>
        </div>
        <div className="flex space-x-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="365">Last year</option>
          </select>
          <button
            onClick={handleExport}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Users</p>
              <p className="text-2xl font-bold text-gray-900">
                {analyticsData?.totalUsers || '1,234'}
              </p>
            </div>
            <Users className="w-8 h-8 text-blue-500" />
          </div>
          <p className="text-xs text-green-600 mt-2">
            +12% from last period
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Avg Engagement</p>
              <p className="text-2xl font-bold text-gray-900">
                {analyticsData?.avgEngagement || '73%'}
              </p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-500" />
          </div>
          <p className="text-xs text-green-600 mt-2">
            +5% from last period
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Completion Rate</p>
              <p className="text-2xl font-bold text-gray-900">
                {analyticsData?.completionRate || '58%'}
              </p>
            </div>
            <Target className="w-8 h-8 text-orange-500" />
          </div>
          <p className="text-xs text-red-600 mt-2">
            -2% from last period
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Active Programs</p>
              <p className="text-2xl font-bold text-gray-900">
                {analyticsData?.activePrograms || '24'}
              </p>
            </div>
            <Award className="w-8 h-8 text-purple-500" />
          </div>
          <p className="text-xs text-green-600 mt-2">
            +3 new this month
          </p>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Engagement Trends */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Engagement Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={engagementData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="engagement" 
                stroke="#3B82F6" 
                strokeWidth={2}
                name="Engagement %"
              />
              <Line 
                type="monotone" 
                dataKey="completion" 
                stroke="#10B981" 
                strokeWidth={2}
                name="Completion %"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Program Distribution */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Program Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={programDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {programDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Progress Tracking */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Progress Tracking</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={progressData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="engagement" fill="#3B82F6" name="Engagement Score" />
            <Bar dataKey="completion" fill="#10B981" name="Completion Rate" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Recent Activity */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {(analyticsData?.recentActivity || [
            { user: 'John Doe', action: 'Completed Fitness Program', time: '2 hours ago' },
            { user: 'Jane Smith', action: 'Started Nutrition Challenge', time: '4 hours ago' },
            { user: 'Mike Johnson', action: 'Achieved Sleep Goal', time: '6 hours ago' },
            { user: 'Sarah Wilson', action: 'Joined Mental Health Workshop', time: '8 hours ago' },
          ]).map((activity, index) => (
            <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
              <div>
                <p className="font-medium text-gray-900">{activity.user}</p>
                <p className="text-sm text-gray-600">{activity.action}</p>
              </div>
              <span className="text-xs text-gray-500">{activity.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Analytics;
