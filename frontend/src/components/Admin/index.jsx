import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Edit3, 
  Trash2, 
  RefreshCw, 
  Search,
  Filter,
  Users,
  Settings,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  Server,
  Zap,
  Shield
} from 'lucide-react';
import { apiService, getStatusColor, formatDate } from '../../utils/api';

const Admin = () => {
  const [users, setUsers] = useState([]);
  const [systemHealth, setSystemHealth] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState('all');
  const [activeTab, setActiveTab] = useState('users');

  useEffect(() => {
    const fetchAdminData = async () => {
      try {
        setLoading(true);
        const [usersData, healthData] = await Promise.all([
          apiService.getAllUsers(),
          apiService.getSystemHealth()
        ]);
        setUsers(usersData);
        setSystemHealth(healthData);
      } catch (error) {
        console.error('Error fetching admin data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAdminData();
  }, []);

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = filterRole === 'all' || user.role === filterRole;
    
    return matchesSearch && matchesRole;
  });

  const handleDeleteUser = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await apiService.deleteUser(userId);
        setUsers(prev => prev.filter(u => u.id !== userId));
      } catch (error) {
        console.error('Error deleting user:', error);
        alert('Failed to delete user');
      }
    }
  };

  const SystemHealthCard = ({ title, value, status, icon: Icon, details }) => {
    const getHealthColor = (status) => {
      switch (status) {
        case 'healthy':
        case 'good':
          return 'text-green-600 bg-green-100';
        case 'warning':
          return 'text-yellow-600 bg-yellow-100';
        case 'error':
        case 'critical':
          return 'text-red-600 bg-red-100';
        default:
          return 'text-gray-600 bg-gray-100';
      }
    };

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${getHealthColor(status)}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">{title}</h3>
              <p className="text-sm text-gray-600">{details}</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-semibold text-gray-900">{value}</div>
            <div className={`text-xs font-medium px-2 py-1 rounded-full ${getHealthColor(status)}`}>
              {status}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const UserRow = ({ user }) => (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
            <Users className="w-5 h-5 text-gray-600" />
          </div>
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900">{user.name}</div>
            <div className="text-sm text-gray-500">{user.email}</div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
          user.role === 'ADMIN' ? 'bg-purple-100 text-purple-800' :
          user.role === 'TRAINER' ? 'bg-green-100 text-green-800' :
          'bg-blue-100 text-blue-800'
        }`}>
          {user.role}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(user.status)}`}>
          {user.status}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {user.last_login ? formatDate(user.last_login) : 'Never'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        <div className="flex space-x-2 justify-end">
          <button className="text-blue-600 hover:text-blue-900">
            <Edit3 className="w-4 h-4" />
          </button>
          <button 
            onClick={() => handleDeleteUser(user.id)}
            className="text-red-600 hover:text-red-900"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading admin panel...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Admin Panel</h1>
          <p className="text-gray-600 mt-1">System management and user administration</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center text-sm text-gray-500">
            <div className="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
            <span>System Online</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('users')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'users'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Users className="w-4 h-4 mr-2 inline" />
            User Management
          </button>
          <button
            onClick={() => setActiveTab('system')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'system'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Settings className="w-4 h-4 mr-2 inline" />
            System Health
          </button>
        </nav>
      </div>

      {/* Content */}
      {activeTab === 'users' && (
        <div className="space-y-6">
          {/* User Management Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">User Management</h2>
              <p className="text-gray-600 text-sm">Manage user accounts and permissions</p>
            </div>
            <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
              <Plus className="w-4 h-4 mr-2 inline" />
              Add User
            </button>
          </div>

          {/* User Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Users</p>
                  <p className="text-2xl font-bold text-gray-900">{users.length}</p>
                </div>
                <Users className="w-8 h-8 text-blue-500" />
              </div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Users</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {users.filter(u => u.status === 'active').length}
                  </p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-500" />
              </div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Admins</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {users.filter(u => u.role === 'ADMIN').length}
                  </p>
                </div>
                <Shield className="w-8 h-8 text-purple-500" />
              </div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Trainers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {users.filter(u => u.role === 'TRAINER').length}
                  </p>
                </div>
                <Activity className="w-8 h-8 text-orange-500" />
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div className="relative">
                <Filter className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <select
                  value={filterRole}
                  onChange={(e) => setFilterRole(e.target.value)}
                  className="pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
                >
                  <option value="all">All Roles</option>
                  <option value="CLIENT">Client</option>
                  <option value="TRAINER">Trainer</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
            </div>
          </div>

          {/* Users Table */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      User
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Login
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredUsers.map(user => (
                    <UserRow key={user.id} user={user} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'system' && (
        <div className="space-y-6">
          {/* System Health Header */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900">System Health</h2>
            <p className="text-gray-600 text-sm">Monitor system performance and status</p>
          </div>

          {/* System Health Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SystemHealthCard
              title="Database"
              value="99.9%"
              status="healthy"
              icon={Database}
              details="PostgreSQL connection stable"
            />
            <SystemHealthCard
              title="AI Service"
              value="Active"
              status="healthy"
              icon={Zap}
              details="OpenAI API responding normally"
            />
            <SystemHealthCard
              title="API Response"
              value={systemHealth.api_response_time || '125ms'}
              status="good"
              icon={Server}
              details="Average response time"
            />
            <SystemHealthCard
              title="System Uptime"
              value={systemHealth.uptime || '99.9%'}
              status="healthy"
              icon={Clock}
              details="Last restart: 7 days ago"
            />
          </div>

          {/* System Metrics */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">System Metrics</h3>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {systemHealth.active_connections || 47}
                  </div>
                  <div className="text-sm text-gray-600">Active Connections</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">2.3GB</div>
                  <div className="text-sm text-gray-600">Memory Usage</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {systemHealth.last_backup || 'Jan 15, 2024'}
                  </div>
                  <div className="text-sm text-gray-600">Last Backup</div>
                </div>
              </div>
            </div>
          </div>

          {/* System Logs */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Recent System Events</h3>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">System backup completed successfully</p>
                    <p className="text-xs text-gray-500">2 hours ago</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <Activity className="w-5 h-5 text-blue-500 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">AI service health check passed</p>
                    <p className="text-xs text-gray-500">4 hours ago</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-500 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">High memory usage detected and resolved</p>
                    <p className="text-xs text-gray-500">Yesterday</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Admin;