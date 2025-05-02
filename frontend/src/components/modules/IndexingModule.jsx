import React, { useState, useEffect } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';

// Default vector databases if config fails to load
const DEFAULT_VECTOR_DBS = {
  faiss: {
    name: "FAISS",
    description: "Facebook AI Similarity Search",
    local: true
  },
  chroma: {
    name: "Chroma",
    description: "Chroma Vector Database",
    local: true
  }
};

function IndexingModule({ embeddings = [], indices = [], documents = [], loading, error, onCreateIndex, onIndexDelete }) {
  const { t } = useLanguage();
  const [selectedEmbedding, setSelectedEmbedding] = useState('');
  const [indexType, setIndexType] = useState(''); // Initialize empty
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [indexResult, setIndexResult] = useState(null);
  const [vectorDatabases, setVectorDatabases] = useState(DEFAULT_VECTOR_DBS); // Initialize with default

  // 加载配置
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setConfigLoading(true);
        const configData = await loadConfig();
        setConfig(configData);
        
        // Safely set vector databases
        if (configData && 
            typeof configData === 'object' && 
            configData.vector_databases && 
            typeof configData.vector_databases === 'object') {
          setVectorDatabases(configData.vector_databases);
        } else {
          console.warn('Using default vector databases configuration');
          setVectorDatabases(DEFAULT_VECTOR_DBS);
        }
        
        // 设置默认值 - 使用 vector_databases
        const vdbs = (configData && 
                     typeof configData === 'object' && 
                     configData.vector_databases && 
                     typeof configData.vector_databases === 'object') 
                     ? configData.vector_databases 
                     : DEFAULT_VECTOR_DBS;
                     
        try {
          const availableTypes = vdbs ? Object.keys(vdbs) : [];
          if (Array.isArray(availableTypes) && availableTypes.length > 0) {
            setIndexType(availableTypes[0]); // Set default index type
          }
        } catch (err) {
          console.error('Error setting default index type:', err);
          // Fallback to first key in DEFAULT_VECTOR_DBS
          const defaultTypes = Object.keys(DEFAULT_VECTOR_DBS);
          if (defaultTypes.length > 0) {
            setIndexType(defaultTypes[0]);
          }
        }
      } catch (err) {
        console.error('Error loading configuration:', err);
        setVectorDatabases(DEFAULT_VECTOR_DBS);
        const availableTypes = Object.keys(DEFAULT_VECTOR_DBS);
        if (availableTypes && availableTypes.length > 0) {
          setIndexType(availableTypes[0]);
        }
      } finally {
        setConfigLoading(false);
      }
    };
    
    fetchConfig();
  }, []);

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedEmbedding || !indexType) return;
    
    try {
      // Find the document_id associated with the selected embedding_id
      const embeddingInfo = embeddings.find(emb => emb.embedding_id === selectedEmbedding);
      if (!embeddingInfo) {
        throw new Error("Selected embedding not found");
      }
      const result = await onCreateIndex(embeddingInfo.document_id, indexType, selectedEmbedding); // Pass embedding_id too
      setIndexResult(result);
    } catch (err) {
      // 错误已在 App.jsx 中处理
      console.error("Indexing failed in module:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">{t('vectorIndexing')}</h2>
        <p className="text-gray-600 mb-6">{t('indexingDesc')}</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('selectEmbeddings')}
            </label>
            { !Array.isArray(embeddings) && <p className="text-red-500 text-sm mt-1">{t('embeddingsNotLoadedError', 'Embeddings data is not available or invalid.')}</p> }
            <select
              value={selectedEmbedding}
              onChange={(e) => setSelectedEmbedding(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              required
              disabled={!Array.isArray(embeddings) || embeddings.length === 0}
            >
              <option value="">{!Array.isArray(embeddings) || embeddings.length === 0 ? t('noEmbeddingsAvailable') : t('selectEmbeddings')}</option>
              {/* Ensure embeddings and documents are arrays before mapping */}
              {Array.isArray(embeddings) && Array.isArray(documents) && embeddings.map((emb) => {
                const doc = documents.find(d => d.id === emb.document_id);
                const displayName = doc ? doc.filename : emb.document_id;
                return (
                  <option key={emb.embedding_id} value={emb.embedding_id}>
                    {displayName} ({t('model')}: {emb.model}, ID: {emb.embedding_id})
                  </option>
                );
              })}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('indexType')}
            </label>
            <select
              value={indexType}
              onChange={(e) => setIndexType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              disabled={configLoading || !(vectorDatabases && Object.keys(vectorDatabases).length > 0)}
            >
              {configLoading ? (
                <option>{t('loadingConfig')}...</option>
              ) : (
                (() => {
                  try {
                    if (vectorDatabases && typeof vectorDatabases === 'object') {
                      const keys = Object.keys(vectorDatabases);
                      if (Array.isArray(keys) && keys.length > 0) {
                        return keys.map((dbKey) => (
                          <option key={dbKey} value={dbKey}>
                            {vectorDatabases[dbKey]?.name || dbKey} ({vectorDatabases[dbKey]?.description || 'N/A'})
                          </option>
                        ));
                      }
                    }
                    return <option value="">{t('noIndexTypesConfigured')}</option>;
                  } catch (err) {
                    console.error('Error rendering vector database options:', err);
                    return <option value="">{t('errorLoadingOptions')}</option>;
                  }
                })()
              )}
            </select>
          </div>
          
          <div>
            <button
              type="submit"
              disabled={loading || configLoading || !selectedEmbedding || !indexType || !(vectorDatabases && Object.keys(vectorDatabases).length > 0)}
              className={`px-4 py-2 rounded-md text-white ${
                loading || configLoading || !selectedEmbedding || !indexType || !(vectorDatabases && Object.keys(vectorDatabases).length > 0)
                  ? 'bg-purple-400 cursor-not-allowed'
                  : 'bg-purple-600 hover:bg-purple-700'
              }`}
            >
              {loading ? t('processing') : t('createIndex')}
            </button>
          </div>
        </form>
      </div>
      
      {/* Display existing indices table */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">{t('existingIndices')}</h2> {/* Add translation key */}
        
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-purple-600"></div>
            <p className="mt-2 text-gray-600">{t('loading')}</p>
          </div>
        ) : (
          <div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('indexId')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('documentFilename')}</th> {/* Changed from documentId */}
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('vectorDb')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('collectionName')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('indexName')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('vectorCount')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Array.isArray(indices) && Array.isArray(documents) && indices.map((idx) => {
                    const doc = documents.find(d => d.id === idx.document_id);
                    return (
                      <tr key={idx.index_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{idx.index_id}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc ? doc.filename : idx.document_id}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{idx.vector_db}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{idx.collection_name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{idx.index_name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{idx.total_vectors}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button 
                            onClick={() => onIndexDelete(idx.index_id)} 
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
            
            {Array.isArray(indices) && indices.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p>{t('noIndices')}</p> {/* Add translation key */}
              </div>
            )}
          </div>
        )}
      </div>
      
      {indexResult && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold mb-4">{t('indexingResults')}</h2>
          
          <div className="mb-4">
            <h3 className="font-medium text-gray-700 mb-2">{t('indexInfo')}</h3>
            <div className="bg-gray-50 p-4 rounded-md text-sm">
              <p className="mb-1">
                <span className="font-medium">{t('embeddingId')}:</span> {indexResult.embedding_id}
              </p>
              <p className="mb-1">
                <span className="font-medium">{t('indexId')}:</span> {indexResult.index_id}
              </p>
              <p className="mb-1">
                <span className="font-medium">{t('indexType')}:</span> {vectorDatabases?.[indexResult.index_type]?.name || indexResult.index_type}
              </p>
              <p className="mb-1">
                <span className="font-medium">{t('timestamp')}:</span> {new Date().toLocaleString()}
              </p>
            </div>
          </div>
          
          <div>
            <h3 className="font-medium text-gray-700 mb-2">{t('statsInfo')}</h3>
            <div className="bg-gray-50 p-4 rounded-md text-sm">
              <p className="mb-1">
                <span className="font-medium">{t('vectorCount')}:</span> {indexResult.total_vectors}
              </p>
              <p>
                <span className="font-medium">{t('resultFile')}:</span> index_{indexResult.index_id}.json
              </p>
            </div>
          </div>
        </div>
      )}
      
      {!indexResult && !loading && (
        <div className="bg-gray-50 p-6 rounded-lg text-center text-gray-500">
          {t('noIndexCreated')}
        </div>
      )}
    </div>
  );
}

export default IndexingModule;
