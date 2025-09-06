import React from 'react';
import { BarChart3, BookOpen, MessageSquare, Brain, Settings, LogOut, User } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

const Navigation = ({ currentView, setCurrentView }) => {
  const { user, logout } = useAuth();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, roles: ['CLIENT', 'TRAINER', 'ADMIN'] },
    { id: 'programs', label: 'Programs', icon: BookOpen, roles: ['CLIENT', 'TRAINER', 'ADMIN'] },
    { id: 'responses', label: 'Responses', icon: MessageSquare, roles: ['CLIENT', 'TRAINER', 'ADMIN'] },
    { id: 'insights', label: 'AI Insights', icon: Brain, roles: ['CLIENT', 'TRAINER', 'ADMIN'] },
    { id: 'admin', label: 'Admin Panel', icon: Settings, roles: ['ADMIN'] },
  ];

  // Filter nav items based on user role
  const filteredNavItems = navItems.filter(item => 
    item.roles.includes(user?.role)
  );

  const handleNavClick = (viewId) => {
    setCurrentView(viewId);
  };

  const handleLogout = async () => {
    if (window.confirm('Are you sure you want to sign out?')) {
      await logout();
    }
  };

  return (
    <div className="bg-white shadow-sm border-r border-gray-200 h-full flex flex-col">
      {/* Logo and branding */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Wellness AI</h1>
            <p className="text-xs text-gray-500">Corporate Edition</p>
          </div>
        </div>
      </div>

      {/* Navigation menu */}
      <nav className="flex-1 px-6 py-4">
        <ul className="space-y-1">
          {filteredNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            
            return (
              <li key={item.id}>
                <button
                  onClick={() => handleNavClick(item.id)}
                  className={`w-full group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-150 ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <Icon className={`w-5 h-5 mr-3 flex-shrink-0 ${
                    isActive ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-600'
                  }`} />
                  <span className="truncate">{item.label}</span>
                  
                  {/* Active indicator */}
                  {isActive && (
                    <div className="ml-auto w-2 h-2 bg-blue-500 rounded-full"></div>
                  )}
                </button>
              </li>
            );
          })}
        </ul>

        {/* Quick stats or notifications could go here */}
        <div className="mt-8 p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
          <div className="flex items-center justify-between text-sm">
            <span className="text-blue-800 font-medium">Your Progress</span>
            <span className="text-blue-600">78%</span>
          </div>
          <div className="mt-2 bg-white rounded-full h-2">
            <div className="bg-gradient-to-r from-blue-400 to-blue-500 h-2 rounded-full" style={{ width: '78%' }}></div>
          </div>
          <p className="text-xs text-blue-600 mt-2">Keep up the great work!</p>
        </div>
      </nav>

      {/* User profile section */}
      <div className="border-t border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center">
            <User className="w-5 h-5 text-gray-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {user?.first_name} {user?.last_name}
            </p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          </div>
        </div>

        {/* Role badge */}
        <div className="flex items-center justify-between mb-4">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            user?.role === 'ADMIN' 
              ? 'bg-purple-100 text-purple-800' 
              : user?.role === 'TRAINER'
              ? 'bg-green-100 text-green-800'
              : 'bg-blue-100 text-blue-800'
          }`}>
            {user?.role}
          </span>
          <div className="w-2 h-2 bg-green-400 rounded-full" title="Online"></div>
        </div>

        {/* Logout button */}
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg transition-colors group"
        >
          <LogOut className="w-4 h-4 mr-2 text-gray-400 group-hover:text-gray-600" />
          Sign out
        </button>
      </div>
    </div>
  );
};

export default Navigation;