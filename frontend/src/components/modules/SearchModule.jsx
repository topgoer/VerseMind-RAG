import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';
import { getLogger } from '../../utils/logger';

const logger = getLogger('SearchModule');

function SearchModule({ indices = [], documents = [], loading, error, onSearch }) { // Add documents prop
  const { t } = useLanguage();
  const [selectedIndex, setSelectedIndex] = useState('');
  const [selectedCollection, setSelectedCollection] = useState('');
  const [availableCollections, setAvailableCollections] = useState([]);
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
  
  // Extract and update available collections whenever indices change
  useEffect(() => {
    if (Array.isArray(indices) && indices.length > 0) {
      // Get unique collection names
      logger.debug('Processing indices for collections:', indices);
      
      // Debug raw values - make sure collection_name is actually present
      const rawValues = indices.map(idx => {
        return {
          index_id: idx.index_id,
          collection_name: idx.collection_name || 'undefined',
          hasCollectionName: !!idx.collection_name,
          document_id: idx.document_id
        }
      });
      logger.debug('Raw collection values in indices:', rawValues);
      
      // Debug additional info about collection structure
      logger.debug('Index keys:', indices.length > 0 ? Object.keys(indices[0]) : 'No indices');
      logger.debug('First few indices sample:', indices.slice(0, 3));
      
      // Filter non-empty collection names and create unique set
      const uniqueCollections = [...new Set(
        indices
          .map(idx => idx.collection_name)
          .filter(name => name && name.trim() !== '')
      )];
      
      logger.debug('Found collections:', uniqueCollections);
      setAvailableCollections(uniqueCollections);
    } else {
      logger.debug('No indices found or indices is not an array:', indices);
      setAvailableCollections([]);
    }
  }, [indices]);

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    if ((!selectedIndex && !selectedCollection) || !query.trim()) return;
    
    try {
      // If a collection is selected, pass both the index and collection
      // If not, just use the selected index
      let results;
      if (selectedCollection) {
        results = await onSearch(selectedIndex, query, topK, threshold, minChars, selectedCollection);
      } else {
        results = await onSearch(selectedIndex, query, topK, threshold, minChars);
      }
      setSearchResults(results);
    } catch (err) {
      // 错误已在 App.jsx 中处理
      logger.error("Search failed in module:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h2 className="text-xl font-semibold mb-4">{t('semanticSearch')}</h2>
        <p className="text-gray-600 mb-6">{t('searchDesc')}</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Always show the collection dropdown, even if empty */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('selectCollection')}
            </label>
            <select
              value={selectedCollection}
              onChange={(e) => {
                setSelectedCollection(e.target.value);
                // Reset index selection when collection changes
                setSelectedIndex('');
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
            >
              <option value="">{t('allIndices')}</option>
              {availableCollections.length > 0 ? (
                availableCollections.map(collection => (
                  <option key={collection} value={collection}>{collection}</option>
                ))
              ) : (
                <option value="" disabled>{t('noCollectionsAvailable', 'No collections available')}</option>
              )}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {availableCollections.length > 0 
                ? t('selectCollectionDescription', 'Select a collection to search across all its indices, or select a specific index below')
                : t('noCollectionsHint', 'No collections found. Create collections in the Vector Indexing module.')}
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {selectedCollection ? t('selectIndexFromCollection') : t('selectIndex')}
            </label>
            <select
              value={selectedIndex}
              onChange={(e) => setSelectedIndex(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              required={!selectedCollection}
              disabled={!Array.isArray(indices) || indices.length === 0}
            >
              <option value="">{!Array.isArray(indices) || indices.length === 0 ? t('noIndicesAvailable') : t('selectIndex')}</option>
              {/* Ensure indices and documents are arrays before mapping */}
              {Array.isArray(indices) && Array.isArray(documents) && 
                // If a collection is selected, filter indices by that collection
                indices
                  .filter(idx => !selectedCollection || idx.collection_name === selectedCollection)
                  .map((idx) => {
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
              disabled={loading || (!selectedIndex && !selectedCollection) || !query.trim()}
              className={`px-4 py-2 rounded-md text-white ${
                loading || (!selectedIndex && !selectedCollection) || !query.trim()
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
                <div 
                  key={`result-${result.id || result.chunk_id || result.text?.substring(0, 20) || Math.random().toString(36).substring(2, 10)}`} 
                  className="bg-gray-50 p-4 rounded-md"
                >
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

// Add PropTypes validation

SearchModule.propTypes = {
  indices: PropTypes.array,
  documents: PropTypes.array,
  loading: PropTypes.bool,
  error: PropTypes.string,
  onSearch: PropTypes.func.isRequired
};

SearchModule.defaultProps = {
  indices: [],
  documents: [],
  loading: false,
  error: null
};

export default SearchModule;

