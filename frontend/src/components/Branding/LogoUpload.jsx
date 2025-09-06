import React, { useState, useRef } from 'react';
import { Upload, X, Check, AlertCircle, Image } from 'lucide-react';

const LogoUpload = ({ onLogoUpload, currentLogo, maxSize = 10 * 1024 * 1024 }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [preview, setPreview] = useState(currentLogo);
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml', 'image/webp'];
    
    if (!allowedTypes.includes(file.type)) {
      return 'Please upload a valid image file (JPEG, PNG, SVG, or WebP)';
    }
    
    if (file.size > maxSize) {
      return `File size must be less than ${Math.round(maxSize / (1024 * 1024))}MB`;
    }
    
    return null;
  };

  const handleFileUpload = async (file) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError('');
    setUploading(true);

    try {
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target.result);
      };
      reader.readAsDataURL(file);

      // Upload file (in production, this would be an API call)
      const formData = new FormData();
      formData.append('logo', file);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // In production, replace with actual API call:
      // const response = await apiRequest('/branding/logo', {
      //   method: 'POST',
      //   body: formData,
      //   headers: {} // Don't set Content-Type for FormData
      // });
      
      if (onLogoUpload) {
        onLogoUpload({
          file,
          url: URL.createObjectURL(file),
          name: file.name,
          size: file.size
        });
      }
    } catch (err) {
      setError('Failed to upload logo. Please try again.');
      setPreview(currentLogo);
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const removeLogo = () => {
    setPreview(null);
    setError('');
    if (onLogoUpload) {
      onLogoUpload(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700">
          Company Logo
        </label>
        {preview && (
          <button
            onClick={removeLogo}
            className="text-red-600 hover:text-red-800 text-sm font-medium"
            disabled={uploading}
          >
            Remove Logo
          </button>
        )}
      </div>

      {preview ? (
        <div className="relative">
          <div className="flex items-center justify-center w-full h-32 bg-gray-50 border-2 border-gray-200 rounded-lg">
            <img
              src={preview}
              alt="Company Logo"
              className="max-h-24 max-w-full object-contain"
            />
          </div>
          {uploading && (
            <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                <span className="text-sm text-gray-600">Uploading...</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div
          className={`relative border-2 border-dashed rounded-lg p-6 transition-colors ${
            dragActive
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            disabled={uploading}
          />
          
          <div className="text-center">
            <div className="flex justify-center">
              {uploading ? (
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              ) : (
                <Image className="h-12 w-12 text-gray-400" />
              )}
            </div>
            
            <div className="mt-4">
              <p className="text-sm text-gray-600">
                {uploading ? (
                  'Uploading logo...'
                ) : (
                  <>
                    <span className="font-medium text-blue-600 hover:text-blue-500">
                      Click to upload
                    </span>
                    {' '}or drag and drop
                  </>
                )}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                PNG, JPG, SVG or WebP up to {Math.round(maxSize / (1024 * 1024))}MB
              </p>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center space-x-2 text-red-600 text-sm">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      <div className="text-xs text-gray-500">
        <p>• Recommended size: 200x60px for best results</p>
        <p>• Transparent backgrounds work best</p>
        <p>• SVG format recommended for scalability</p>
      </div>
    </div>
  );
};

export default LogoUpload;
