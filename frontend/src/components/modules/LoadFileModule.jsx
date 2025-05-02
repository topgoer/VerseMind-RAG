import React, { useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

function LoadFileModule({ documents, loading, error, onDocumentUpload, onRefresh, onDocumentDelete }) { // Add onDocumentDelete prop
  const { t } = useLanguage();
  const [dragActive, setDragActive] = useState(false);
  
  // 处理文件拖放
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };
  
  // 处理文件放置
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
      // Reset input value if possible (might need ref, simpler to handle in handleChange)
    }
  };
  
  // 处理文件选择
  const handleChange = (e) => {
    e.preventDefault();
    
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
      // Reset the input value to allow re-selecting the same file
      e.target.value = null; 
    }
  };
  
  // 处理文件上传
  const handleFiles = (files) => {
    const formData = new FormData();
    formData.append('file', files[0]);
    
    onDocumentUpload(formData)
      .then(() => {
        // 上传成功后的处理
      })
      .catch((error) => {
        console.error('上传失败:', error);
      });
  };
  
  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  // 格式化日期
  const formatDate = (dateString) => {
    if (!dateString) return '';
    
    // 假设格式为 "20250412_090000"
    const year = dateString.substring(0, 4);
    const month = dateString.substring(4, 6);
    const day = dateString.substring(6, 8);
    const hour = dateString.substring(9, 11);
    const minute = dateString.substring(11, 13);
    
    return `${year}-${month}-${day} ${hour}:${minute}`;
  };

  // 处理删除确认
  const handleDeleteClick = (docId, docFilename) => {
    if (window.confirm(t('confirmDeleteMessage', { item: docFilename }))) {
      onDocumentDelete(docId);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">{t('documentLoading')}</h2>
        <p className="text-gray-600 mb-4">
          {t('documentLoadingDesc')}
        </p>
        
        <div 
          className={`border-2 border-dashed rounded-lg p-8 text-center ${
            dragActive ? 'border-purple-500 bg-purple-50' : 'border-gray-300'
          }`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
        >
          <div className="space-y-4">
            <div className="text-4xl">📄</div>
            <p className="text-gray-700">
              {t('dragDropFiles')}
            </p>
            <label className="inline-block px-4 py-2 bg-purple-600 text-white rounded-md cursor-pointer hover:bg-purple-700 transition-colors">
              {t('selectFiles')}
              <input
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.md,.csv"
                onChange={handleChange}
              />
            </label>
            <p className="text-sm text-gray-500">
              {t('maxFileSize')}
            </p>
          </div>
        </div>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">{t('documentList')}</h2>
          <button 
            onClick={onRefresh}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
          >
            {t('refresh')}
          </button>
        </div>
        
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-purple-600"></div>
            <p className="mt-2 text-gray-600">{t('loading')}</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>{t('noDocuments')}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('fileName')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('fileType')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('fileSize')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('uploadTime')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('pageCount')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <span className="mr-2">
                          {doc.file_type === 'pdf' ? '📕' :
                           doc.file_type === 'docx' ? '📘' :
                           doc.file_type === 'csv' ? '📊' :
                           doc.file_type === 'txt' ? '📄' :
                           doc.file_type === 'png' || doc.file_type === 'jpg' || doc.file_type === 'jpeg' || doc.file_type === 'webp' || doc.file_type === 'gif' ? '🖼️' :
                           '📝'}
                        </span>
                        <span className="font-medium text-gray-900">{doc.filename}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {doc.file_type.toUpperCase()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {formatFileSize(doc.file_size)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {formatDate(doc.upload_time)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {doc.pages}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button 
                        onClick={() => handleDeleteClick(doc.id, doc.filename)} // Updated onClick handler
                        className="text-red-600 hover:text-red-900"
                      >
                        {t('delete')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default LoadFileModule;

