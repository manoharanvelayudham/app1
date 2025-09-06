import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Eye, 
  Users, 
  Calendar, 
  RefreshCw, 
  Search,
  Filter,
  BookOpen,
  Target,
  Star,
  CheckCircle
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService, getDifficultyColor } from '../../utils/api';

const Programs = () => {
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('all');
  const [enrolling, setEnrolling] = useState(null);
  const { user } = useAuth();

  useEffect(() => {
    const fetchPrograms = async () => {
      try {
        setLoading(true);
        const data = await apiService.getPrograms();
        setPrograms(data);
      } catch (error) {
        console.error('Error fetching programs:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPrograms();
  }, []);

  const handleEnroll = async (programId) => {
    try {
      setEnrolling(programId);
      await apiService.enrollInProgram(programId);
      
      // Update program enrollment count
      setPrograms(prevPrograms => 
        prevPrograms.map(program => 
          program.id === programId 
            ? { ...program, enrolled: program.enrolled + 1 }
            : program
        )
      );
      
      // Show success message
      alert('Successfully enrolled in program!');
    } catch (error) {
      console.error('Enrollment failed:', error);
      alert('Failed to enroll in program. Please try again.');
    } finally {
      setEnrolling(null);
    }
  };

  const filteredPrograms = programs.filter(program => {
    const matchesSearch = program.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         program.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDifficulty = filterDifficulty === 'all' || program.difficulty === filterDifficulty;
    
    return matchesSearch && matchesDifficulty;
  });

  const ProgramCard = ({ program }) => (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all duration-200 overflow-hidden">
      {/* Program header with gradient */}
      <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6 text-white">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-xl font-semibold mb-2">{program.title}</h3>
            <p className="text-blue-100 text-sm line-clamp-2">{program.description}</p>
          </div>
          <div className="ml-4">
            <span className={`px-3 py-1 text-xs font-medium rounded-full ${getDifficultyColor(program.difficulty)} bg-opacity-20 text-white border border-white border-opacity-30`}>
              {program.difficulty}
            </span>
          </div>
        </div>
      </div>

      {/* Program content */}
      <div className="p-6">
        {/* Program stats */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <div className="flex items-center">
              <Calendar className="w-4 h-4 mr-1" />
              <span>{program.duration}</span>
            </div>
            <div className="flex items-center">
              <Users className="w-4 h-4 mr-1" />
              <span>{program.enrolled} enrolled</span>
            </div>
          </div>
          <div className="flex items-center space-x-1">
            {[...Array(5)].map((_, i) => (
              <Star key={i} className={`w-4 h-4 ${i < 4 ? 'text-yellow-400 fill-current' : 'text-gray-300'}`} />
            ))}
          </div>
        </div>

        {/* Program features */}
        <div className="space-y-2 mb-6">
          <div className="flex items-center text-sm text-gray-600">
            <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
            <span>AI-powered insights</span>
          </div>
          <div className="flex items-center text-sm text-gray-600">
            <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
            <span>Progress tracking</span>
          </div>
          <div className="flex items-center text-sm text-gray-600">
            <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
            <span>Expert guidance</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex space-x-3">
          <button 
            onClick={() => handleEnroll(program.id)}
            disabled={enrolling === program.id}
            className="flex-1 bg-blue-600 text-white py-2.5 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {enrolling === program.id ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 inline animate-spin" />
                Enrolling...
              </>
            ) : (
              <>
                <Target className="w-4 h-4 mr-2 inline" />
                Enroll Now
              </>
            )}
          </button>
          <button className="px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
            <Eye className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading programs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Learning Programs</h1>
          <p className="text-gray-600 mt-1">Discover AI-powered wellness and development programs</p>
        </div>
        {(user?.role === 'TRAINER' || user?.role === 'ADMIN') && (
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
            <Plus className="w-4 h-4 mr-2 inline" />
            Create Program
          </button>
        )}
      </div>

      {/* Filters and Search */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search programs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Difficulty filter */}
          <div className="relative">
            <Filter className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <select
              value={filterDifficulty}
              onChange={(e) => setFilterDifficulty(e.target.value)}
              className="pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
            >
              <option value="all">All Levels</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>

        {/* Filter summary */}
        <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
          <span>
            Showing {filteredPrograms.length} of {programs.length} programs
          </span>
          {(searchTerm || filterDifficulty !== 'all') && (
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterDifficulty('all');
              }}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Programs Grid */}
      {filteredPrograms.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPrograms.map(program => (
            <ProgramCard key={program.id} program={program} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <BookOpen className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No programs found</h3>
          <p className="text-gray-600 mb-4">
            {searchTerm || filterDifficulty !== 'all' 
              ? 'Try adjusting your search or filters'
              : 'No programs are available at the moment'
            }
          </p>
          {(searchTerm || filterDifficulty !== 'all') && (
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterDifficulty('all');
              }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Program statistics */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mb-3">
              <BookOpen className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-blue-900">{programs.length}</div>
            <div className="text-sm text-blue-600">Total Programs</div>
          </div>
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mb-3">
              <Users className="w-6 h-6 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-green-900">
              {programs.reduce((sum, program) => sum + program.enrolled, 0)}
            </div>
            <div className="text-sm text-green-600">Total Enrollments</div>
          </div>
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mb-3">
              <Target className="w-6 h-6 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-purple-900">4.2</div>
            <div className="text-sm text-purple-600">Average Rating</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Programs;