import React, { useState, useEffect } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';

function SearchModule({ indices = [], documents = [], loading, error, onSearch }) { // Add documents prop
  const { t } = useLanguage();
  const [selectedIndex, setSelectedIndex] = useState('');
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.5);
  const [minChars, setMinChars] = useState(100); // Add minChars state
  const [searchResults, setSearchResults] = useState(null);
  const [config, setConfig] = useState(null);

  // 加载配置
  useEffect(() => {
    const fetchConfig = async () => {
      const configData = await loadConfig();
      setConfig(configData);
    };
    
    fetchConfig();
  }, []);

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedIndex || !query.trim()) return;
    
    try {
      // Pass similarity_threshold parameter (not threshold) and min_chars parameter to match the backend API
      const results = await onSearch(selectedIndex, query, topK, threshold, minChars);
      setSearchResults(results);
    } catch (err) {
      // 错误已在 App.jsx 中处理
      console.error("Search failed in module:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">{t('semanticSearch')}</h2>
        <p className="text-gray-600 mb-6">{t('searchDesc')}</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
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
              {/* Ensure indices and documents are arrays before mapping */}
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
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('searchQuery')}
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('searchQueryPlaceholder')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              rows={3}
              required
            />
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('topK')}
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('similarityThreshold')}
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm font-medium">{threshold.toFixed(2)}</span>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('minChars') || 'Min Chars'}
              </label>
              <input
                type="number"
                min="10"
                max="1000"
                value={minChars}
                onChange={(e) => setMinChars(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
          </div>
          
          <div>
            <button
              type="submit"
              disabled={loading || !selectedIndex || !query.trim()}
              className={`px-4 py-2 rounded-md text-white ${
                loading || !selectedIndex || !query.trim()
                  ? 'bg-purple-400 cursor-not-allowed'
                  : 'bg-purple-600 hover:bg-purple-700'
              }`}
            >
              {loading ? t('processing') : t('search')}
            </button>
          </div>
        </form>
      </div>
      
      {searchResults && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold mb-4">{t('searchResults')}</h2>
          
          <div className="mb-4">
            <h3 className="font-medium text-gray-700 mb-2">{t('searchInfo')}</h3>
            <div className="bg-gray-50 p-4 rounded-md text-sm">
              <p className="mb-1">
                <span className="font-medium">{t('searchId')}:</span> {searchResults.search_id}
              </p>
              <p className="mb-1">
                <span className="font-medium">{t('indexId')}:</span> {searchResults.index_id}
              </p>
              <p className="mb-1">
                <span className="font-medium">{t('query')}:</span> {searchResults.query}
              </p>
              <p className="mb-1">
                <span className="font-medium">{t('timestamp')}:</span> {new Date().toLocaleString()}
              </p>
            </div>
          </div>
          
          <div>
            <h3 className="font-medium text-gray-700 mb-2">
              {t('foundResults')} {searchResults.results.length} {t('relevantResults')}
            </h3>
            
            <div className="space-y-4">
              {searchResults.results.map((result, index) => (
                <div key={index} className="bg-gray-50 p-4 rounded-md">
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-medium text-purple-700">#{index + 1}</span>
                    <span className="text-sm bg-purple-100 text-purple-800 px-2 py-1 rounded">
                      {t('similarity')}: {result.similarity.toFixed(4)}
                    </span>
                  </div>
                  
                  <div className="mb-2">
                    <span className="text-xs text-gray-500">
                      {t('chunkId')}: {result.chunk_id || result.id || 'N/A'} | {t('page')}: {result.metadata?.page || 'N/A'}
                    </span>
                  </div>
                  
                  <div className="text-gray-800 whitespace-pre-wrap">
                    {result.text}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {!searchResults && !loading && (
        <div className="bg-gray-50 p-6 rounded-lg text-center text-gray-500">
          {t('noSearchResults')}
        </div>
      )}
    </div>
  );
}

export default SearchModule;

