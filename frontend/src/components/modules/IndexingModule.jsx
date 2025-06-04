import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';
import { fetchEmbeddingsDirectly } from '../../services/api';

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

function IndexingModule({ embeddings = [], indices = [], documents = [], loading, error, onCreateIndex, onIndexDelete, onRefresh, onLoadEmbeddings }) {
  const { t } = useLanguage();
  const [selectedEmbedding, setSelectedEmbedding] = useState('');
  const [indexType, setIndexType] = useState(''); // Initialize empty
  const [configLoading, setConfigLoading] = useState(true);
  const [indexResult, setIndexResult] = useState(null);
  const [vectorDatabases, setVectorDatabases] = useState(DEFAULT_VECTOR_DBS); // Initialize with default
  const [initialLoadDone, setInitialLoadDone] = useState(false);
  const [collectionName, setCollectionName] = useState('');
  const [selectedCollection, setSelectedCollection] = useState('');
  const [availableCollections, setAvailableCollections] = useState([]);

  // Load embeddings when component mounts or when embeddings array is empty
  useEffect(() => {
    const loadEmbeddingsData = async () => {
      // console.log('[IndexingModule] Loading embeddings data, current status:', { 
      //   hasEmbeddings: Array.isArray(embeddings) && embeddings.length > 0,
      //   initialLoadDone
      // });
      
      try {
        // First try to use the provided onLoadEmbeddings function
        if (onLoadEmbeddings && typeof onLoadEmbeddings === 'function') {
          await onLoadEmbeddings();
          setInitialLoadDone(true);
        } 
        // If we still don't have embeddings after calling onLoadEmbeddings, fetch directly from API
        else if (!Array.isArray(embeddings) || embeddings.length === 0) {
          // console.log('[IndexingModule] Directly fetching embeddings from backend API');
          await fetchEmbeddingsDirectlyFromAPI();
          setInitialLoadDone(true);
        }
      } catch (error) {
        console.error('[IndexingModule] Error loading embeddings:', error);
      }
    };

    // Direct fetch function that doesn't rely on parent component state
    const fetchEmbeddingsDirectlyFromAPI = async () => {
      try {
        const data = await fetchEmbeddingsDirectly();
        
        if (Array.isArray(data) && data.length > 0) {
          // console.log('[IndexingModule] Successfully fetched embeddings directly:', data.length);
          // If we have a setEmbeddings function in the parent component, update it
          if (typeof onLoadEmbeddings === 'function') {
            await onLoadEmbeddings(); // This will update the parent's state
          }
          return data;
        }
      } catch (err) {
        console.error('[IndexingModule] Error directly fetching embeddings:', err);
        throw err;
      }
    };

    // Always try to load embeddings on mount if we don't have any
    if ((!Array.isArray(embeddings) || embeddings.length === 0) && !loading && !initialLoadDone) {
      // console.log('[IndexingModule] Loading embeddings on component mount or empty state');
      loadEmbeddingsData();
    }

    // Reset initialLoadDone when component unmounts
    return () => {
      setInitialLoadDone(false);
    };
  }, [embeddings, onLoadEmbeddings, loading, initialLoadDone]);

  // 加载配置
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setConfigLoading(true);
        const configData = await loadConfig();
        
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

  // Automatically set the first embedding if available
  useEffect(() => {
    if (Array.isArray(embeddings) && embeddings.length > 0 && !selectedEmbedding) {
      // console.log('[IndexingModule] Embeddings loaded, setting first embedding as default');
      setSelectedEmbedding(embeddings[0].embedding_id);
    }
  }, [embeddings, selectedEmbedding]);
  
  // Extract and update available collections whenever indices change
  useEffect(() => {
    if (Array.isArray(indices) && indices.length > 0) {
      // Get unique collection names
      const uniqueCollections = [...new Set(indices.map(idx => idx.collection_name))].filter(Boolean);
      setAvailableCollections(uniqueCollections);
      
      // If we have collections and no selected collection, select the first one
      if (uniqueCollections.length > 0 && !selectedCollection) {
        setSelectedCollection(uniqueCollections[0]);
      }
    } else {
      setAvailableCollections([]);
    }
  }, [indices, selectedCollection]);

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedEmbedding || !indexType) return;
    
    try {
      // Find the embedding info
      const embeddingInfo = embeddings.find(emb => emb.embedding_id === selectedEmbedding);
      if (!embeddingInfo) {
        throw new Error("Selected embedding not found");
      }

      // console.log('[IndexingModule] Type of onCreateIndex:', typeof onCreateIndex);
      // console.log('[IndexingModule] Creating index for document:', embeddingInfo.document_id);
      // console.log('[IndexingModule] Using vector DB:', indexType);
      // console.log('[IndexingModule] Using embedding ID:', selectedEmbedding);
      // console.log('[IndexingModule] Using collection name:', collectionName || 'default');

      if (typeof onCreateIndex !== 'function') {
        console.error('[IndexingModule] onCreateIndex is not a function. Props received by IndexingModule:', { embeddings, indices, documents, loading, error, onCreateIndex, onIndexDelete, onRefresh });
        throw new TypeError('onCreateIndex prop is not a function as expected in IndexingModule.');
      }

      // Check if we need to modify App.jsx's handleCreateIndex function to accept collection_name
      // For now, we're assuming App.jsx will handle generating a default collection name if none is provided
      // Create a document-specific default collection name if none provided
      const finalCollectionName = collectionName || `col_${embeddingInfo.document_id.substring(0, 10)}`;
      
      // Call createIndex with the expected parameters: documentId, vectorDb, embeddingId, collectionName, indexName
      const result = await onCreateIndex(
        embeddingInfo.document_id, 
        indexType, 
        selectedEmbedding,
        finalCollectionName,
        null // indexName - let backend auto-generate
      );
      
      setIndexResult(result);
      
      // console.log('[IndexingModule] Index creation result:', result);
      // console.log('[IndexingModule] Using collection:', finalCollectionName);
      
      // If the collection we used is not in our list, add it
      if (!availableCollections.includes(finalCollectionName)) {
        setAvailableCollections([...availableCollections, finalCollectionName]);
      }
      
      // Select the collection we just used
      setSelectedCollection(finalCollectionName);
      
    } catch (err) {
      // 错误已在 App.jsx 中处理
      console.error("Indexing failed in module:", err);
    }
  };

  // Handle refresh request
  const handleRefresh = async () => {
    if (onRefresh && typeof onRefresh === 'function') {
      await onRefresh();
    }
    
    // Also refresh embeddings
    if (onLoadEmbeddings && typeof onLoadEmbeddings === 'function') {
      await onLoadEmbeddings();
    }
  };

  // Support for manual reload of embeddings - tries both methods
  const handleLoadEmbeddings = async () => {
    try {
      if (onLoadEmbeddings && typeof onLoadEmbeddings === 'function') {
        // console.log('[IndexingModule] Refreshing embeddings via parent component');
        await onLoadEmbeddings();
      } else {
        // console.log('[IndexingModule] Refreshing embeddings directly from API');
        await fetchEmbeddingsDirectlyFromAPI();
      }
      // console.log('[IndexingModule] Embeddings refresh completed');
    } catch (error) {
      console.error('[IndexingModule] Error refreshing embeddings:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">{t('vectorIndexing')}</h2>
        <p className="text-gray-600 mb-6">{t('indexingDesc')}</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-sm font-medium text-gray-700">
                {t('selectEmbeddings')}
              </label>
              {!loading && (
                <button
                  type="button"
                  onClick={handleLoadEmbeddings}
                  className="text-xs text-purple-600 hover:text-purple-800 flex items-center"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  {t('refreshEmbeddings')}
                </button>
              )}
            </div>
            {!Array.isArray(embeddings) && <p className="text-red-500 text-sm mt-1">{t('embeddingsNotLoadedError', 'Embeddings data is not available or invalid.')}</p>}
            {Array.isArray(embeddings) && embeddings.length === 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-amber-600 text-sm">{t('noEmbeddingsFound', 'No embeddings found. Try refreshing or go to the Vector Embedding page.')}</p>
                  <button
                    type="button"
                    onClick={handleLoadEmbeddings}
                    className="px-2 py-1 bg-purple-100 text-purple-700 rounded-md text-xs flex items-center hover:bg-purple-200"
                    disabled={loading}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {loading ? t('refreshing', 'Refreshing...') : t('forceRefresh', 'Force Refresh')}
                  </button>
                </div>
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-center text-amber-800 mb-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="font-medium">{t('vectorEmbeddingsRequired', 'Vector Embeddings Required')}</span>
                  </div>
                  <p className="text-sm text-amber-700 mb-3">{t('beforeIndexingHelp', 'Before creating a vector index, you need to generate vector embeddings for your documents.')}</p>
                  <a 
                    href="#embedding"
                    onClick={(e) => {
                      e.preventDefault();
                      if (window.setActiveModule) {
                        window.setActiveModule('embedding');
                      } else {
                        // Fallback: Try to find and click the embedding tab
                        const embeddingTab = document.querySelector('[data-module="embedding"]');
                        if (embeddingTab) embeddingTab.click();
                      }
                    }}
                    className="inline-flex items-center px-3 py-2 border border-amber-300 text-sm font-medium rounded-md text-amber-700 bg-amber-100 hover:bg-amber-200"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 9l3 3m0 0l-3 3m3-3H8m13 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {t('goToVectorEmbedding', 'Go to Vector Embedding')}
                  </a>
                </div>
              </div>
            )}
            <select
              value={selectedEmbedding}
              onChange={(e) => setSelectedEmbedding(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              required
              disabled={!Array.isArray(embeddings) || embeddings.length === 0 || loading}
            >
              <option value="">
                {(() => {
                  if (loading) {
                    return t('loading');
                  }
                  
                  if (!Array.isArray(embeddings) || embeddings.length === 0) {
                    return t('noEmbeddingsAvailable');
                  }
                  
                  return t('selectEmbeddings');
                })()}
              </option>
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
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('collectionName')}
            </label>
            <div className="space-y-2">
              {availableCollections.length > 0 && (
                <div className="flex flex-col mb-2">
                  <select
                    value={collectionName}
                    onChange={(e) => {
                      if (e.target.value === "new") {
                        // If "Create new collection" is selected, reset to empty string for custom input
                        setCollectionName("");
                      } else if (e.target.value === "none") {
                        // If "No collection" is selected, clear the collection name
                        setCollectionName("");
                      } else {
                        setCollectionName(e.target.value);
                      }
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="none">{t('selectCollection')}</option>
                    {availableCollections.map(collection => (
                      <option key={collection} value={collection}>{collection}</option>
                    ))}
                    <option value="new">{t('newCollection')}</option>
                  </select>
                </div>
              )}
              
              {/* Always show text input for collection name */}
              <input
                type="text"
                value={collectionName}
                onChange={(e) => setCollectionName(e.target.value)}
                placeholder={t('collectionPlaceholder')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {t('collectionDescription', 'Group related indices into a collection for better organization')}
            </p>
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
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">{t('existingIndices')}</h2>
          <button 
            onClick={handleRefresh}
            disabled={loading}
            className={`px-3 py-1 rounded-md text-sm ${loading ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600 text-white'}`}
          >
            <span className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {loading ? t('refreshing') : t('refresh')}
            </span>
          </button>
        </div>
        
        {/* Collection filter selector */}
        <div className="flex items-center mb-4">
          <label className="text-sm font-medium text-gray-700 mr-2">
            {t('filterByCollection')}:
          </label>
          <select
            value={selectedCollection}
            onChange={(e) => setSelectedCollection(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 text-sm"
          >
            <option value="">{t('allCollections')}</option>
            {availableCollections.map(collection => (
              <option key={collection} value={collection}>{collection}</option>
            ))}
          </select>
        </div>
        
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
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{t('actions')}</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Array.isArray(indices) && Array.isArray(documents) && indices
                    .filter(idx => !selectedCollection || idx.collection_name === selectedCollection)
                    .map((idx) => {
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
                <p>{t('noIndices')}</p>
              </div>
            )}
            
            {Array.isArray(indices) && indices.length > 0 && selectedCollection &&
              indices.filter(idx => idx.collection_name === selectedCollection).length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p>{t('noIndicesInCollection', 'No indices in this collection')} ({selectedCollection})</p>
              </div>
            )}
            
            {error && (
              <div className="mt-4 bg-red-50 p-4 rounded-md">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293-1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
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
                <span className="font-medium">{t('indexType')}:</span> {vectorDatabases?.[indexResult.vector_db]?.name || indexResult.vector_db || "unknown"}
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
      
      {!indexResult && !loading && indices.length === 0 && (
        <div className="bg-gray-50 p-6 rounded-lg text-center text-gray-500">
          {t('noIndexCreated')}
        </div>
      )}
    </div>
  );
}

// Add PropTypes validation for component props
IndexingModule.propTypes = {
  embeddings: PropTypes.array,
  indices: PropTypes.array,
  documents: PropTypes.array,
  loading: PropTypes.bool,
  error: PropTypes.string,
  onCreateIndex: PropTypes.func,
  onIndexDelete: PropTypes.func,
  onRefresh: PropTypes.func,
  onLoadEmbeddings: PropTypes.func
};

export default IndexingModule;
