import React, { useState, useEffect } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';

function EmbeddingFileModule({ documents, embeddings = [], loading, error, onCreateEmbeddings, onEmbeddingDelete, globalSelectedDocument, onLoadEmbeddings }) {
  const { t } = useLanguage();
  const [selectedDocument, setSelectedDocument] = useState('');
  const [provider, setProvider] = useState(''); // Initialize empty
  const [model, setModel] = useState(''); // Initialize empty
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [embeddingResult, setEmbeddingResult] = useState(null); // Keep track of the last result for display
  const [filteredEmbeddings, setFilteredEmbeddings] = useState([]);

  // 加载配置 - 使用缓存版本
  useEffect(() => {
    const fetchConfig = async () => {
      setConfigLoading(true);
      try {
        // 使用 loadConfig() 获取缓存的配置
        const configData = await loadConfig();
        setConfig(configData);
        
        // 设置默认值 - 使用 embedding_models
        if (configData && configData.embedding_models) {
          const availableProviders = Object.keys(configData.embedding_models);
          if (availableProviders.length > 0) {
            const defaultProvider = availableProviders[0];
            setProvider(defaultProvider);
            if (configData.embedding_models[defaultProvider] && configData.embedding_models[defaultProvider].length > 0) {
              setModel(configData.embedding_models[defaultProvider][0].id);
            }
          }
        }
      } catch (err) {
        console.error("Failed to load config:", err);
      } finally {
        setConfigLoading(false);
      }
    };
    
    fetchConfig();
  }, []);

  // Sync with global selected document if provided
  useEffect(() => {
    if (globalSelectedDocument && globalSelectedDocument.id) {
      setSelectedDocument(globalSelectedDocument.id);
    }
  }, [globalSelectedDocument]);

  // Reload embeddings when document selection changes
  useEffect(() => {
    if (selectedDocument && onLoadEmbeddings) {
      // Reload embeddings when a document is selected to ensure we have the latest data
      onLoadEmbeddings();
    }
  }, [selectedDocument, onLoadEmbeddings]);

  // Filter embeddings when selectedDocument or embeddings change
  useEffect(() => {
    if (embeddings && embeddings.length > 0) {
      if (selectedDocument) {
        const filtered = embeddings.filter(embed => embed.document_id === selectedDocument);
        setFilteredEmbeddings(filtered);
        console.log(`Filtered ${filtered.length} embeddings for document ID ${selectedDocument}`);
      } else {
        setFilteredEmbeddings(embeddings);
        console.log(`Showing all ${embeddings.length} embeddings - no document selected`);
      }
    } else {
      setFilteredEmbeddings([]);
      console.log('No embeddings available to filter');
    }
  }, [selectedDocument, embeddings]);

  // 处理提供商变更
  const handleProviderChange = (e) => {
    const newProvider = e.target.value;
    setProvider(newProvider);
    
    // 当提供商变更时，选择该提供商的第一个嵌入模型
    if (config && config.embedding_models && config.embedding_models[newProvider] && config.embedding_models[newProvider].length > 0) {
      setModel(config.embedding_models[newProvider][0].id);
    } else {
      setModel(''); // Reset model if provider has no models
    }
  };

  // 处理文档选择变更
  const handleDocumentChange = (e) => {
    const newDocId = e.target.value;
    setSelectedDocument(newDocId);
  };

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedDocument || !provider || !model) return;
    
    try {
      const result = await onCreateEmbeddings(selectedDocument, provider, model);
      setEmbeddingResult(result); // Update the last result
    } catch (err) {
      // 错误已在 App.jsx 中处理
      console.error("Embedding failed in module:", err);
    }
  };

  // 获取提供商显示名称
  const getProviderDisplayName = (providerId) => {
    switch(providerId) {
      case 'ollama': return 'Ollama (本地)';
      case 'openai': return 'OpenAI';
      case 'deepseek': return 'DeepSeek';
      default: return providerId;
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">{t('vectorEmbedding')}</h2>
        <p className="text-gray-600 mb-6">{t('embeddingDesc')}</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('selectDocument')}
            </label>
            <select
              value={selectedDocument}
              onChange={handleDocumentChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              required
              disabled={documents.length === 0}
            >
              <option value="">{documents.length === 0 ? t('noDocumentsLoaded') : t('selectDocument')}</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename} ({doc.title})
                </option>
              ))}
            </select>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('embeddingProvider')}
              </label>
              <select
                value={provider}
                onChange={handleProviderChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                disabled={configLoading}
              >
                {configLoading ? (
                  <option>{t('loadingConfig')}...</option>
                ) : config && config.embedding_models ? (
                  Object.keys(config.embedding_models).map((providerId) => (
                    <option key={providerId} value={providerId}>
                      {getProviderDisplayName(providerId)}
                    </option>
                  ))
                ) : (
                  <option value="">{t('noProvidersConfigured')}</option>
                )}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('embeddingModel')} {/* 明确是嵌入模型 */}
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                disabled={configLoading || !provider}
              >
                {configLoading ? (
                  <option>{t('loadingConfig')}...</option>
                ) : config && config.embedding_models && config.embedding_models[provider] && config.embedding_models[provider].length > 0 ? (
                  config.embedding_models[provider].map((modelInfo) => (
                    <option key={modelInfo.id} value={modelInfo.id}>
                      {modelInfo.name} ({modelInfo.dimensions} {t('dimensions')})
                    </option>
                  ))
                ) : (
                  <option value="">{provider ? t('noModelsForProvider') : t('selectProviderFirst')}</option>
                )}
              </select>
            </div>
          </div>
          
          <div>
            <button
              type="submit"
              disabled={loading || configLoading || !selectedDocument || !provider || !model}
              className={`px-4 py-2 rounded-md text-white ${
                loading || configLoading || !selectedDocument || !provider || !model
                  ? 'bg-purple-400 cursor-not-allowed'
                  : 'bg-purple-600 hover:bg-purple-700'
              }`}
            >
              {loading ? t('processing') : t('generateEmbeddings')}
            </button>
          </div>
        </form>
      </div>
      
      {/* Display existing embeddings table */} 
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">{t('existingEmbeddings')}</h2> 
          
          {/* Document filter selector */}
          <div className="flex items-center">
            <span className="text-sm text-gray-500 mr-2">{t('filterByDocument')}:</span>
            <select
              value={selectedDocument}
              onChange={handleDocumentChange}
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
                onClick={() => setSelectedDocument('')}
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
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
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
    </div>
  );
}

export default EmbeddingFileModule;

