import React from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';

function EmbeddingTable({ 
  filteredEmbeddings, 
  documents, 
  selectedDocument, 
  onDocumentChange, 
  onClearFilter, 
  loading, 
  onEmbeddingDelete 
}) {
  const { t } = useLanguage();

  // Get provider display name
  const getProviderDisplayName = (providerId) => {
    switch(providerId) {
      case 'ollama': return 'Ollama (本地)';
      case 'openai': return 'OpenAI';
      case 'deepseek': return 'DeepSeek';
      default: return providerId;
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">{t('existingEmbeddings')}</h2> 
        
        {/* Document filter selector */}
        <div className="flex items-center">
          <span className="text-sm text-gray-500 mr-2">{t('filterByDocument')}:</span>
          <select
            value={selectedDocument}
            onChange={onDocumentChange}
            className="text-sm px-3 py-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
          >
            <option value="">{t('allDocuments')}</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}
              </option>
            ))}
          </select>
          {selectedDocument && (
            <button 
              onClick={onClearFilter}
              className="ml-2 text-xs text-purple-600 hover:text-purple-800"
            >
              {t('clearFilter')}
            </button>
          )}
        </div>
      </div>
      
      {loading ? (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-purple-600"></div>
          <p className="mt-2 text-gray-600">{t('loading')}</p>
        </div>
      ) : (
        <div>
          {filteredEmbeddings.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('embeddingId')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('documentId')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('provider')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('embeddingModel')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('dimensions')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('vectorCount')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('actions')}</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredEmbeddings.map((emb) => {
                    const doc = Array.isArray(documents) ? documents.find(d => d.id === emb.document_id) : null;
                    return (
                      <tr key={emb.embedding_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{emb.embedding_id}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc ? doc.filename : emb.document_id}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{getProviderDisplayName(emb.provider)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{emb.model}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{emb.dimensions}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{emb.total_embeddings}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button 
                            onClick={() => onEmbeddingDelete(emb.embedding_id)} 
                            className="text-red-600 hover:text-red-900"
                          >
                            {t('delete')}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 bg-gray-50 rounded-md">
              {selectedDocument ? (
                <div>
                  <p className="text-gray-600 mb-2">{t('noEmbeddingsForDocument')}</p>
                  <p className="text-sm text-gray-500">{t('useFormAboveToCreateEmbeddings')}</p>
                </div>
              ) : (
                <p className="text-gray-600">{t('noEmbeddingsAvailable')}</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

EmbeddingTable.propTypes = {
  filteredEmbeddings: PropTypes.array.isRequired,
  documents: PropTypes.array.isRequired,
  selectedDocument: PropTypes.string.isRequired,
  onDocumentChange: PropTypes.func.isRequired,
  onClearFilter: PropTypes.func.isRequired,
  loading: PropTypes.bool.isRequired,
  onEmbeddingDelete: PropTypes.func.isRequired
};

export default EmbeddingTable;
