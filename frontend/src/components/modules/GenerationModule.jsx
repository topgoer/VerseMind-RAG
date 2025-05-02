import React, { useState, useEffect } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';

function GenerationModule({ indices = [], documents = [], loading, error, onGenerateText, onSearch }) { // Add indices, documents, onSearch props
  const { t } = useLanguage();
  const [selectedIndex, setSelectedIndex] = useState(''); // Add state for selected index
  const [provider, setProvider] = useState(''); 
  const [model, setModel] = useState(''); 
  const [prompt, setPrompt] = useState('');
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [generationResult, setGenerationResult] = useState(null);
  const [currentSearchResults, setCurrentSearchResults] = useState(null); // To hold search results before generation

  // 加载配置
  useEffect(() => {
    const fetchConfig = async () => {
      setConfigLoading(true);
      const configData = await loadConfig();
      setConfig(configData);
      setConfigLoading(false);
      
      // 设置默认值 - 使用 model_groups
      if (configData && configData.model_groups) {
        const availableProviders = Object.keys(configData.model_groups);
        if (availableProviders.length > 0) {
          const defaultProvider = availableProviders[0];
          setProvider(defaultProvider);
          if (configData.model_groups[defaultProvider] && configData.model_groups[defaultProvider].length > 0) {
            setModel(configData.model_groups[defaultProvider][0].id);
          }
        }
      }
    };
    
    fetchConfig();
  }, []);

  // 处理提供商变更
  const handleProviderChange = (e) => {
    const newProvider = e.target.value;
    setProvider(newProvider);
    
    // 当提供商变更时，选择该提供商的第一个聊天模型
    if (config && config.model_groups && config.model_groups[newProvider] && config.model_groups[newProvider].length > 0) {
      setModel(config.model_groups[newProvider][0].id);
    } else {
      setModel(''); // Reset model if provider has no models
    }
  };

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedIndex || !provider || !model || !prompt.trim()) return;
    
    try {
      // Step 1: Perform search using the selected index and prompt
      const searchResult = await onSearch(selectedIndex, prompt, 3, 0.7); // Use default topK=3, threshold=0.7 for context
      setCurrentSearchResults(searchResult); // Store search results

      if (searchResult && searchResult.search_id) {
        // Step 2: Generate text using the search results
        const result = await onGenerateText(searchResult.search_id, prompt, provider, model);
        setGenerationResult(result);
      } else {
        // Handle case where search failed or returned no results
        console.error("Search returned no results, cannot generate text.");
        // Optionally, set an error state or message for the user
      }

    } catch (err) {
      // 错误已在 App.jsx 中处理
      console.error("Search or Generation failed in module:", err);
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
        <h2 className="text-xl font-semibold mb-4">{t('textGeneration')}</h2>
        <p className="text-gray-600 mb-6">{t('generationDesc')}</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Index Selection Dropdown */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('selectIndex')}
            </label>
            <select
              value={selectedIndex}
              onChange={(e) => setSelectedIndex(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              required
              disabled={!Array.isArray(indices) || indices.length === 0}
            >
              <option value="">{!Array.isArray(indices) || indices.length === 0 ? t('noIndicesAvailable') : t('selectIndex')}</option>
              {Array.isArray(indices) && Array.isArray(documents) && indices.map((idx) => {
                const doc = documents.find(d => d.id === idx.document_id);
                const displayName = doc ? doc.filename : idx.document_id;
                const indexTypeName = config?.vector_databases?.[idx.vector_db]?.name || idx.vector_db;
                return (
                  <option key={idx.index_id} value={idx.index_id}>
                    {displayName} ({t('indexType')}: {indexTypeName}, ID: {idx.index_id})
                  </option>
                );
              })}
            </select>
          </div>

          {/* Provider and Model Selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('providerLabel')} {/* Correct label */}
              </label>
              <select
                value={provider}
                onChange={handleProviderChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                disabled={configLoading}
              >
                {configLoading ? (
                  <option>{t('loadingConfig')}...</option>
                ) : config && config.model_groups ? (
                  Object.keys(config.model_groups).map((providerId) => (
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
                {t('modelLabel')} {/* Correct label */}
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                disabled={configLoading || !provider}
              >
                {configLoading ? (
                  <option>{t('loadingConfig')}...</option>
                ) : config && config.model_groups && config.model_groups[provider] && config.model_groups[provider].length > 0 ? (
                  config.model_groups[provider].map((modelInfo) => (
                    <option key={modelInfo.id} value={modelInfo.id}>
                      {modelInfo.id} {/* Display the full ID */}
                    </option>
                  ))
                ) : (
                  <option value="">{provider ? t('noModelsForProvider') : t('selectProviderFirst')}</option>
                )}
              </select>
            </div>
          </div>
          
          {/* Prompt Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('prompt')}
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={t('promptPlaceholder')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 resize-none"
              rows={3}
              required
              disabled={!selectedIndex} // Disable if no index is selected
            />
          </div>
          
          {/* Submit Button */}
          <div>
            <button
              type="submit"
              disabled={loading || configLoading || !selectedIndex || !provider || !model || !prompt.trim()}
              className={`px-4 py-2 rounded-md text-white ${
                loading || configLoading || !selectedIndex || !provider || !model || !prompt.trim()
                  ? 'bg-purple-400 cursor-not-allowed'
                  : 'bg-purple-600 hover:bg-purple-700'
              }`}
            >
              {loading ? t('processing') : t('generateText')}
            </button>
          </div>
        </form>
      </div>
      
      {/* Generation Result Display */}
      {generationResult && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold mb-4">{t('generationResults')}</h2>
          <div className="bg-gray-50 p-4 rounded-md">
            <p className="text-gray-800 whitespace-pre-wrap">{generationResult.generated_text}</p>
            <div className="text-xs text-gray-500 mt-2">
              {t('modelUsed')}: {generationResult.model} ({getProviderDisplayName(generationResult.provider)})
            </div>
          </div>
        </div>
      )}
      
      {/* Placeholder messages */}
      {!generationResult && !loading && !selectedIndex && (
        <div className="bg-gray-50 p-6 rounded-lg text-center text-gray-500">
          {t('selectIndexFirst')}
        </div>
      )}
      {!generationResult && !loading && selectedIndex && (
        <div className="bg-gray-50 p-6 rounded-lg text-center text-gray-500">
          {t('noGenerationYet')}
        </div>
      )}
    </div>
  );
}

export default GenerationModule;

