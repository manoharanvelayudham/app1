import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Eye, 
  Edit3, 
  Trash2, 
  RefreshCw, 
  Search,
  Filter,
  MessageSquare,
  Calendar,
  FileText,
  Upload,
  X,
  Save,
  Send
} from 'lucide-react';
import { apiService, getStatusColor, formatDate } from '../../utils/api';

const Responses = () => {
  const [responses, setResponses] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingResponse, setEditingResponse] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [responsesData, programsData] = await Promise.all([
          apiService.getMyResponses(),
          apiService.getPrograms()
        ]);
        setResponses(responsesData);
        setPrograms(programsData);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const filteredResponses = responses.filter(response => {
    const matchesSearch = response.program_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         response.content.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || response.status === filterStatus;
    
    return matchesSearch && matchesStatus;
  });

  const handleDelete = async (responseId) => {
    if (window.confirm('Are you sure you want to delete this response?')) {
      try {
        await apiService.deleteResponse(responseId);
        setResponses(prev => prev.filter(r => r.id !== responseId));
      } catch (error) {
        console.error('Error deleting response:', error);
        alert('Failed to delete response');
      }
    }
  };

  const CreateResponseModal = () => {
    const [formData, setFormData] = useState({
      program_id: '',
      content: '',
      type: 'text'
    });
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (isDraft = false) => {
      if (!formData.program_id || !formData.content.trim()) {
        alert('Please fill in all required fields');
        return;
      }

      try {
        setSubmitting(true);
        const responseData = {
          ...formData,
          status: isDraft ? 'draft' : 'submitted'
        };
        
        const newResponse = await apiService.createResponse(responseData);
        
        // Add program title to response
        const program = programs.find(p => p.id === parseInt(formData.program_id));
        const responseWithTitle = {
          ...newResponse,
          program_title: program?.title || 'Unknown Program'
        };
        
        setResponses(prev => [responseWithTitle, ...prev]);
        setShowCreateModal(false);
        setFormData({ program_id: '', content: '', type: 'text' });
      } catch (error) {
        console.error('Error creating response:', error);
        alert('Failed to create response');
      } finally {
        setSubmitting(false);
      }
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
          {/* Modal Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Create New Response</h2>
            <button
              onClick={() => setShowCreateModal(false)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Modal Body */}
          <div className="p-6 space-y-6">
            {/* Program Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Program <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.program_id}
                onChange={(e) => setFormData(prev => ({ ...prev, program_id: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select a program...</option>
                {programs.map(program => (
                  <option key={program.id} value={program.id}>{program.title}</option>
                ))}
              </select>
            </div>

            {/* Response Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Response Type</label>
              <div className="flex space-x-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="text"
                    checked={formData.type === 'text'}
                    onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
                    className="mr-2"
                  />
                  <FileText className="w-4 h-4 mr-1" />
                  Text Response
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="file"
                    checked={formData.type === 'file'}
                    onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
                    className="mr-2"
                  />
                  <Upload className="w-4 h-4 mr-1" />
                  File Upload
                </label>
              </div>
            </div>

            {/* Content */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {formData.type === 'text' ? 'Your Response' : 'Description'} <span className="text-red-500">*</span>
              </label>
              <textarea 
                value={formData.content}
                onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 h-40 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder={formData.type === 'text' ? 'Share your thoughts, insights, or reflections...' : 'Describe what you\'re uploading...'}
              />
              <div className="text-xs text-gray-500 mt-1">
                {formData.content.length}/1000 characters
              </div>
            </div>

            {/* File Upload (if file type selected) */}
            {formData.type === 'file' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Upload File</label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors">
                  <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600 mb-1">Click to upload or drag and drop</p>
                  <p className="text-xs text-gray-500">PDF, DOC, DOCX, or images up to 10MB</p>
                  <input type="file" className="hidden" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" />
                </div>
              </div>
            )}
          </div>

          {/* Modal Footer */}
          <div className="flex space-x-3 p-6 border-t border-gray-200">
            <button
              onClick={() => setShowCreateModal(false)}
              className="flex-1 border border-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-50 transition-colors"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              onClick={() => handleSubmit(true)}
              disabled={submitting}
              className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              {submitting ? <RefreshCw className="w-4 h-4 mr-2 inline animate-spin" /> : <Save className="w-4 h-4 mr-2 inline" />}
              Save Draft
            </button>
            <button
              onClick={() => handleSubmit(false)}
              disabled={submitting}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {submitting ? <RefreshCw className="w-4 h-4 mr-2 inline animate-spin" /> : <Send className="w-4 h-4 mr-2 inline" />}
              Submit
            </button>
          </div>
        </div>
      </div>
    );
  };

  const ResponseCard = ({ response }) => (
    <div className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">{response.program_title}</h3>
          <div className="flex items-center space-x-4 text-sm text-gray-500">
            <div className="flex items-center">
              <Calendar className="w-4 h-4 mr-1" />
              <span>{formatDate(response.created_at)}</span>
            </div>
            <div className="flex items-center">
              <FileText className="w-4 h-4 mr-1" />
              <span className="capitalize">{response.type}</span>
            </div>
          </div>
        </div>
        <span className={`px-3 py-1 text-xs font-medium rounded-full ${getStatusColor(response.status)}`}>
          {response.status.charAt(0).toUpperCase() + response.status.slice(1)}
        </span>
      </div>

      <div className="mb-4">
        <p className="text-gray-700 text-sm leading-relaxed">
          {response.content.length > 200 
            ? `${response.content.substring(0, 200)}...` 
            : response.content
          }
        </p>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-gray-100">
        <div className="flex space-x-2">
          <button className="flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium">
            <Eye className="w-4 h-4 mr-1" />
            View
          </button>
          {response.status === 'draft' && (
            <button 
              onClick={() => setEditingResponse(response)}
              className="flex items-center text-green-600 hover:text-green-800 text-sm font-medium"
            >
              <Edit3 className="w-4 h-4 mr-1" />
              Edit
            </button>
          )}
        </div>
        <button 
          onClick={() => handleDelete(response.id)}
          className="flex items-center text-red-600 hover:text-red-800 text-sm font-medium"
        >
          <Trash2 className="w-4 h-4 mr-1" />
          Delete
        </button>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading responses...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Responses</h1>
          <p className="text-gray-600 mt-1">Track and manage your program responses</p>
        </div>
        <button 
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4 mr-2 inline" />
          New Response
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search responses..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Status filter */}
          <div className="relative">
            <Filter className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
            >
              <option value="all">All Status</option>
              <option value="draft">Draft</option>
              <option value="submitted">Submitted</option>
              <option value="reviewed">Reviewed</option>
            </select>
          </div>
        </div>

        {/* Filter summary */}
        <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
          <span>
            Showing {filteredResponses.length} of {responses.length} responses
          </span>
          {(searchTerm || filterStatus !== 'all') && (
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterStatus('all');
              }}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Responses List */}
      {filteredResponses.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredResponses.map(response => (
            <ResponseCard key={response.id} response={response} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No responses found</h3>
          <p className="text-gray-600 mb-4">
            {searchTerm || filterStatus !== 'all' 
              ? 'Try adjusting your search or filters'
              : 'Start by creating your first response'
            }
          </p>
          {!searchTerm && filterStatus === 'all' ? (
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4 mr-2 inline" />
              Create First Response
            </button>
          ) : (
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterStatus('all');
              }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Response Statistics */}
      <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-6 border border-green-100">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-900">{responses.length}</div>
            <div className="text-sm text-green-600">Total Responses</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-900">
              {responses.filter(r => r.status === 'submitted').length}
            </div>
            <div className="text-sm text-blue-600">Submitted</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-900">
              {responses.filter(r => r.status === 'draft').length}
            </div>
            <div className="text-sm text-yellow-600">Drafts</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-900">
              {responses.filter(r => r.status === 'reviewed').length}
            </div>
            <div className="text-sm text-purple-600">Reviewed</div>
          </div>
        </div>
      </div>

      {/* Create Response Modal */}
      {showCreateModal && <CreateResponseModal />}
    </div>
  );
};

export default Responses;