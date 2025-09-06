import React, { useState, useEffect } from 'react';
import { 
  Brain, 
  TrendingUp, 
  Target, 
  Star, 
  RefreshCw, 
  BarChart3,
  Award,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
  BookOpen,
  Users
} from 'lucide-react';
import { apiService, getPriorityColor } from '../../utils/api';

const AIInsights = () => {
  const [insights, setInsights] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const fetchAIData = async () => {
      try {
        setLoading(true);
        const [insightsData, analyticsData] = await Promise.all([
          apiService.getAIInsights(),
          apiService.getAnalyticsSummary(1) // Replace with actual user ID
        ]);
        setInsights(insightsData);
        setAnalytics(analyticsData);
      } catch (error) {
        console.error('Error fetching AI data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAIData();
  }, []);

  const generateNewInsights = async () => {
    try {
      setGenerating(true);
      await apiService.generateNewInsights(1); // Replace with actual user ID
      
      // Refresh insights after generation
      const newInsights = await apiService.getAIInsights();
      setInsights(newInsights);
    } catch (error) {
      console.error('Error generating insights:', error);
      alert('Failed to generate new insights');
    } finally {
      setGenerating(false);
    }
  };

  const getConfidenceWidth = (score) => `${Math.round(score * 100)}%`;
  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const MetricCard = ({ title, value, icon: Icon, color, subtitle, trend }) => (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <div className="flex items-baseline space-x-2">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            {trend && (
              <div className={`flex items-center text-sm font-medium ${
                trend > 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                <TrendingUp className={`w-4 h-4 mr-1 ${trend < 0 ? 'rotate-180' : ''}`} />
                {Math.abs(trend)}%
              </div>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-xl ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  );

  const InsightCard = ({ insight }) => (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              insight.category === 'Leadership' ? 'bg-blue-100 text-blue-800' :
              insight.category === 'Communication' ? 'bg-green-100 text-green-800' :
              insight.category === 'Teamwork' ? 'bg-purple-100 text-purple-800' :
              insight.category === 'Innovation' ? 'bg-orange-100 text-orange-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {insight.category}
            </div>
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPriorityColor(insight.priority)}`}>
              {insight.priority} priority
            </span>
          </div>
          <p className="text-gray-900 font-medium leading-relaxed">{insight.insight}</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex-1 mr-4">
          <div className="flex items-center space-x-2 text-sm">
            <span className="text-gray-600">Confidence:</span>
            <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-32">
              <div 
                className={`h-2 rounded-full transition-all duration-500 ${getConfidenceColor(insight.confidence_score)}`}
                style={{ width: getConfidenceWidth(insight.confidence_score) }}
              />
            </div>
            <span className="text-gray-600 font-medium">
              {Math.round(insight.confidence_score * 100)}%
            </span>
          </div>
        </div>
        <button className="text-blue-600 hover:text-blue-800 text-sm font-medium px-3 py-1 rounded-lg hover:bg-blue-50 transition-colors">
          View Details
        </button>
      </div>
    </div>
  );

  const CompetencyGap = ({ gap, index }) => (
    <div className="flex items-center justify-between p-4 bg-orange-50 rounded-lg border border-orange-100">
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
          <span className="text-orange-600 font-semibold text-sm">{index + 1}</span>
        </div>
        <div>
          <h4 className="font-medium text-orange-900">{gap}</h4>
          <p className="text-xs text-orange-600">Identified skill gap</p>
        </div>
      </div>
      <button className="text-orange-600 hover:text-orange-800 text-sm font-medium">
        Get Training
      </button>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-gray-600">Analyzing your data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Insights</h1>
          <p className="text-gray-600 mt-1">Personalized insights powered by artificial intelligence</p>
        </div>
        <button 
          onClick={generateNewInsights}
          disabled={generating}
          className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? (
            <RefreshCw className="w-4 h-4 mr-2 inline animate-spin" />
          ) : (
            <Brain className="w-4 h-4 mr-2 inline" />
          )}
          {generating ? 'Generating...' : 'Generate New Insights'}
        </button>
      </div>

      {/* Analytics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Personality Score"
          value={`${analytics?.personality_score}/100`}
          icon={Star}
          color="bg-gradient-to-br from-blue-500 to-blue-600"
          subtitle="Overall assessment"
          trend={5}
        />
        <MetricCard
          title="Growth Trend"
          value={analytics?.growth_trend === 'positive' ? 'Positive' : 'Stable'}
          icon={TrendingUp}
          color="bg-gradient-to-br from-green-500 to-green-600"
          subtitle="Based on recent activity"
        />
        <MetricCard
          title="Active Recommendations"
          value={analytics?.recommendations_count}
          icon={Target}
          color="bg-gradient-to-br from-purple-500 to-purple-600"
          subtitle="Personalized suggestions"
        />
        <MetricCard
          title="Skill Areas"
          value={insights.length}
          icon={BarChart3}
          color="bg-gradient-to-br from-orange-500 to-orange-600"
          subtitle="Analyzed categories"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Insights */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">Latest Insights</h2>
                <div className="flex items-center text-sm text-gray-500">
                  <Zap className="w-4 h-4 mr-1" />
                  AI-Generated
                </div>
              </div>
            </div>
            <div className="p-6">
              {insights.length > 0 ? (
                <div className="space-y-4">
                  {insights.map(insight => (
                    <InsightCard key={insight.id} insight={insight} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Brain className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p>No insights available yet</p>
                  <button 
                    onClick={generateNewInsights}
                    className="mt-3 text-purple-600 hover:text-purple-800 font-medium"
                  >
                    Generate your first insights
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Competency Gaps */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 text-orange-500" />
                <h2 className="text-lg font-semibold text-gray-900">Skill Gaps</h2>
              </div>
            </div>
            <div className="p-6">
              {analytics?.competency_gaps?.length > 0 ? (
                <div className="space-y-3">
                  {analytics.competency_gaps.map((gap, index) => (
                    <CompetencyGap key={gap} gap={gap} index={index} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-gray-500">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                  <p className="text-sm">No skill gaps identified</p>
                </div>
              )}
            </div>
          </div>

          {/* Progress Tracker */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                <Award className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="font-semibold text-blue-900 mb-1">Progress Status</h3>
              <p className="text-sm text-blue-600 mb-4">Your wellness journey</p>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-blue-800">Overall Progress</span>
                  <span className="font-medium text-blue-900">
                    {analytics?.personality_score || 0}%
                  </span>
                </div>
                <div className="bg-white rounded-full h-3">
                  <div 
                    className="bg-gradient-to-r from-blue-400 to-blue-500 h-3 rounded-full transition-all duration-1000"
                    style={{ width: `${analytics?.personality_score || 0}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
            </div>
            <div className="p-6 space-y-3">
              <button className="w-full flex items-center justify-center px-4 py-3 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 transition-colors">
                <Brain className="w-4 h-4 mr-2" />
                Request Analysis
              </button>
              <button className="w-full flex items-center justify-center px-4 py-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors">
                <BookOpen className="w-4 h-4 mr-2" />
                View Reports
              </button>
              <button className="w-full flex items-center justify-center px-4 py-3 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors">
                <Users className="w-4 h-4 mr-2" />
                Schedule Coaching
              </button>
            </div>
          </div>

          {/* AI Processing Status */}
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-6 border border-gray-200">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-gray-700">AI Status</span>
            </div>
            <div className="space-y-2 text-xs text-gray-600">
              <div className="flex justify-between">
                <span>Data Processing</span>
                <span className="text-green-600">Complete</span>
              </div>
              <div className="flex justify-between">
                <span>Pattern Analysis</span>
                <span className="text-green-600">Complete</span>
              </div>
              <div className="flex justify-between">
                <span>Next Update</span>
                <span className="text-blue-600">In 2 hours</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Insights History */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Insights Timeline</h2>
            <div className="flex items-center text-sm text-gray-500">
              <Clock className="w-4 h-4 mr-1" />
              Last 30 days
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {/* Timeline items */}
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <Brain className="w-4 h-4 text-blue-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-1">
                  <span className="text-sm font-medium text-gray-900">Leadership Assessment Completed</span>
                  <span className="text-xs text-gray-500">2 days ago</span>
                </div>
                <p className="text-sm text-gray-600">AI identified strong potential in strategic thinking and decision-making processes.</p>
              </div>
            </div>

            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-green-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-1">
                  <span className="text-sm font-medium text-gray-900">Performance Trend Analysis</span>
                  <span className="text-xs text-gray-500">1 week ago</span>
                </div>
                <p className="text-sm text-gray-600">Positive growth trend detected in communication and teamwork skills.</p>
              </div>
            </div>

            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                <Target className="w-4 h-4 text-purple-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-1">
                  <span className="text-sm font-medium text-gray-900">Personalized Recommendations Generated</span>
                  <span className="text-xs text-gray-500">2 weeks ago</span>
                </div>
                <p className="text-sm text-gray-600">New training suggestions created based on competency gap analysis.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIInsights;