import React from 'react';
import PropTypes from 'prop-types';
import { Trash2, Download } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { getLogger } from '../../utils/logger';

const logger = getLogger('LoadFileModule');

function LoadFileModule({ documents, loading, error, onDocumentUpload, onDocumentDelete, onRefresh }) {
  const { t } = useLanguage();

  const handleFileChange = (event) => {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
      // Create FormData object and add the file with field name 'file'
      const formData = new FormData();
      formData.append('file', files[0]); // Only upload one file at a time for now
      onDocumentUpload(formData);
    }
  };

  const handleDelete = async (documentId) => {
    try {
      logger.debug(`Attempting to delete document with ID: ${documentId}`);
      await onDocumentDelete(documentId);
      logger.debug(`Document deletion successful for ID: ${documentId}`);
      // Optionally, trigger a refresh or handle UI update here if not handled by parent
    } catch (err) {
      logger.error(`Document deletion failed:`, err);
      // Error is already handled and displayed by App.jsx
    }
  };

  return (
    <div className="space-y-6">
      {/* Document Upload Section */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">{t('documentLoading')}</h2>
        <p className="text-gray-600 mb-4">
          {t('documentLoadingDesc')}
        </p>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            className="hidden"
            id="fileUpload"
            accept=".pdf,.docx,.txt,.md,.csv"
          />
          <label htmlFor="fileUpload" className="cursor-pointer">
            <div className="text-purple-600 mx-auto mb-4 w-16 h-16 flex items-center justify-center">
              {/* Placeholder for a more relevant icon if needed */}
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-10 h-10">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l-3.75 3.75M12 9.75l3.75 3.75M3 17.25V6.75A2.25 2.25 0 015.25 4.5h13.5A2.25 2.25 0 0121 6.75v10.5A2.25 2.25 0 0118.75 21H5.25A2.25 2.25 0 013 17.25z" />
              </svg>
            </div>
            <p className="text-gray-700 mb-2">{t('dragDropFiles')}</p>
            <button 
              type="button" 
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
              onClick={() => document.getElementById('fileUpload').click()} // Trigger file input click
            >
              {t('selectFiles')}
            </button>
            <p className="text-xs text-gray-500 mt-2">{t('maxFileSize')}</p>
          </label>
        </div>
        {loading && <p className="text-purple-600 mt-4">{t('uploading')}</p>}
        {error && <p className="text-red-500 mt-4">{t('uploadError')}: {error.message || error}</p>}
      </div>

      {/* Document List Section */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">{t('documentList')}</h2>
          <button 
            onClick={() => {
              logger.debug('Refreshing document list...');
              onRefresh().catch(err => {
                logger.error('Error refreshing document list:', err);
              });
            }} 
            className="px-4 py-2 text-sm bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            disabled={loading}
          >
            {t('refresh')}
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('fileName')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('fileType')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('fileSize')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('uploadTime')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('pageCount')}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('actions')}</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {documents && documents.length > 0 ? (
                documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-medium text-gray-900">{doc.filename}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{doc.type}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{doc.size}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{doc.upload_time}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {(() => {
                        if (doc.pages !== undefined) {
                          return doc.pages;
                        }
                        if (doc.row_count !== undefined) {
                          return doc.row_count;
                        }
                        return '-';
                      })()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center">
                        <a
                          href={`/api/documents/${doc.id}/download`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-900 flex items-center mr-4"
                        >
                          <Download size={18} className="mr-1" />
                          {t('download')}
                        </a>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="text-red-600 hover:text-red-900 flex items-center"
                          disabled={loading}
                        >
                          <Trash2 size={18} className="mr-1" />
                          {t('delete')}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-gray-500">
                    {t('noDocumentsUploaded')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

LoadFileModule.propTypes = {
  documents: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    filename: PropTypes.string.isRequired,
    type: PropTypes.string,
    size: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    upload_time: PropTypes.string,
    pages: PropTypes.number,
  })).isRequired,
  loading: PropTypes.bool.isRequired,
  error: PropTypes.object, // Can be an Error object or null
  onDocumentUpload: PropTypes.func.isRequired,
  onDocumentDelete: PropTypes.func.isRequired, // Ensure this is required
  onRefresh: PropTypes.func.isRequired,
};

export default LoadFileModule;


