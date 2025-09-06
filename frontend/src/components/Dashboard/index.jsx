import React, { useState, useEffect } from 'react';
import { 
  Users, 
  BookOpen, 
  MessageSquare, 
  Brain, 
  TrendingUp,
  Activity,
  RefreshCw,
  AlertCircle,
  Calendar,
  Target,
  Award,
  Clock
} from 'lucide-react';
import { apiService } from '../../utils/api';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const data = await apiService.getDashboardStats();
        setStats(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const refreshData = async () => {
    setLoading(true);
    try {
      const data = await apiService.getDashboardStats();
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, icon: Icon, color, trend, description }) => (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <div className="flex items-baseline space-x-2">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            {trend && (
              <span className={`text-sm font-medium ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {trend > 0 ? '+' : ''}{trend}%
              </span>
            )}
          </div>
          {description && (
            <p className="text-xs text-gray-500 mt-1">{description}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  );

  const ActivityItem = ({ activity }) => {
    const getActivityIcon = (type) => {
      switch (type) {
        case 'enrollment':
          return <BookOpen className="w-4 h-4 text-blue-500" />;
        case 'response':
          return <MessageSquare className="w-4 h-4 text-green-500" />;
        case 'insight':
          return <Brain className="w-4 h-4 text-purple-500" />;
        default:
          return <Activity className="w-4 h-4 text-gray-400" />;
      }
    };

    return (
      <div className="flex items-start space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
        <div className="flex-shrink-0 mt-1">
          {getActivityIcon(activity.type)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-900 font-medium">{activity.message}</p>
          <div className="flex items-center mt-1 text-xs text-gray-500">
            <Clock className="w-3 h-3 mr-1" />
            <span>{activity.timestamp}</span>
          </div>
        </div>
      </div>
    );
  };

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
          <div>
            <h3 className="text-red-800 font-medium">Error loading dashboard</h3>
            <p className="text-red-700 text-sm mt-1">{error}</p>
            <button 
              onClick={refreshData}
              className="mt-3 text-red-600 hover:text-red-800 text-sm font-medium"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Welcome back! Here's what's happening in your wellness journey.</p>
        </div>
        <button 
          onClick={refreshData}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <RefreshCw className="w-4 h-4 mr-2 inline animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4 mr-2 inline" />
          )}
          Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Users"
          value={stats?.total_users?.toLocaleString()}
          icon={Users}
          color="bg-gradient-to-br from-blue-500 to-blue-600"
          trend={12}
          description="Active participants"
        />
        <StatCard
          title="Active Programs"
          value={stats?.active_programs}
          icon={BookOpen}
          color="bg-gradient-to-br from-green-500 to-green-600"
          trend={8}
          description="Running this month"
        />
        <StatCard
          title="Responses"
          value={stats?.completed_responses?.toLocaleString()}
          icon={MessageSquare}
          color="bg-gradient-to-br from-purple-500 to-purple-600"
          trend={24}
          description="Completed this week"
        />
        <StatCard
          title="AI Insights"
          value={stats?.ai_insights_generated}
          icon={Brain}
          color="bg-gradient-to-br from-orange-500 to-orange-600"
          trend={15}
          description="Generated recently"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="p-6 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Activity className="w-5 h-5 text-gray-400" />
                <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
              </div>
              <span className="text-xs text-gray-500">Last updated: just now</span>
            </div>
          </div>
          <div className="p-6">
            {stats?.recent_activity?.length > 0 ? (
              <div className="space-y-1">
                {stats.recent_activity.map(activity => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Activity className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>No recent activity</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Stats Sidebar */}
        <div className="space-y-6">
          {/* Weekly Progress */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <TrendingUp className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-blue-900">Weekly Progress</h3>
                <p className="text-sm text-blue-600">Your wellness journey</p>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-blue-800">Engagement</span>
                <span className="text-sm font-medium text-blue-900">85%</span>
              </div>
              <div className="bg-white rounded-full h-2">
                <div className="bg-gradient-to-r from-blue-400 to-blue-500 h-2 rounded-full" style={{ width: '85%' }}></div>
              </div>
            </div>
          </div>

          {/* Upcoming Events */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center space-x-2 mb-4">
              <Calendar className="w-5 h-5 text-gray-400" />
              <h3 className="font-semibold text-gray-900">Upcoming</h3>
            </div>
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Team Workshop</p>
                  <p className="text-xs text-gray-500">Tomorrow, 2:00 PM</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                <div>
                  <p className="text-sm font-medium text-gray-900">AI Insights Review</p>
                  <p className="text-xs text-gray-500">Friday, 10:00 AM</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Monthly Assessment</p>
                  <p className="text-xs text-gray-500">Next week</p>
                </div>
              </div>
            </div>
          </div>

          {/* Achievement Badge */}
          <div className="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border border-yellow-100">
            <div className="text-center">
              <Award className="w-8 h-8 text-yellow-600 mx-auto mb-2" />
              <h3 className="font-semibold text-yellow-900 mb-1">Achievement Unlocked!</h3>
              <p className="text-sm text-yellow-700">Consistent Participant</p>
              <div className="mt-3 text-xs text-yellow-600">
                Completed 5 programs in a row
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;