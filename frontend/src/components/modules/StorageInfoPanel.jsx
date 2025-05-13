import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';  // Helper function to process search results
const processSearchResults = (searchResults) => {
  let topResults = [];
  
  // Try to use the global object first for most accurate and consistent data
  try {
    if (typeof window !== 'undefined' && 
        window.verseMindCurrentSearchResults && 
        window.verseMindCurrentSearchResults.search_id === searchResults?.search_id) {
      console.log("Using global search results object for consistency", window.verseMindCurrentSearchResults);
      if (Array.isArray(window.verseMindCurrentSearchResults.results)) {
        topResults = window.verseMindCurrentSearchResults.results;
      }
    }
  } catch (err) {
    console.warn("Failed to access global search results object:", err);
  }
  
  // If we didn't get results from the global object, use the provided search results
  if (topResults.length === 0) {
    if (searchResults?.results) {
      if (Array.isArray(searchResults.results)) {
        // Results are directly in array format
        topResults = searchResults.results;
      } else if (typeof searchResults.results === 'object') {
        // Results might be in an object with numeric keys
        topResults = Object.values(searchResults.results);
      }
    } else if (searchResults?.query) {
      console.log("Search has query but no results array, checking for raw similarities data");
      // Try to parse similarities from raw search data - sometimes it's stored differently
      if (searchResults.similarities) {
        // Convert similarities array to results array
        topResults = Array.isArray(searchResults.similarities) ? 
          searchResults.similarities.map((similarity, idx) => ({
            text: searchResults.texts?.[idx] || `Result ${idx+1}`,
            similarity: similarity,
            id: `result-${idx}`
          })) : [];
        
        console.log("Reconstructed results from similarities:", topResults);
      }
    }
  }
  
  // Additional logging to help debug
  console.log("Results before processing:", {
    resultsAvailable: !!searchResults?.results,
    resultsType: searchResults?.results ? typeof searchResults.results : 'undefined',
    isArray: Array.isArray(searchResults?.results),
    rawResults: searchResults?.results,
    topResultsLength: topResults.length,
    usingGlobalObject: topResults === window?.verseMindCurrentSearchResults?.results
  });
  
  // Ensure each result has a numeric similarity value
  topResults = topResults.map(result => ({
    ...result,
    similarity: parseFloat(result.similarity || 0)
  }));
  
  // Sort by similarity score in descending order (highest first)
  return [...topResults].sort((a, b) => b.similarity - a.similarity);
};

// Helper function to determine the actual threshold value
const determineThreshold = (searchResults, storageInfo) => {
  let actualThreshold = 0.5; // Default value降低到0.5，避免过于严格的匹配要求
  
  // Helper to safely parse float values with fallback
  const safeParseFloat = (value, fallback) => {
    if (value === undefined || value === null) return fallback;
    
    try {
      const parsed = parseFloat(value);
      return isNaN(parsed) ? fallback : parsed;
    } catch (err) {
      console.warn("Failed to parse threshold value:", value, err);
      return fallback;
    }
  };
  
  // Try each potential source of threshold value in priority order
  if (searchResults?.similarity_threshold !== undefined) {
    actualThreshold = safeParseFloat(searchResults.similarity_threshold, actualThreshold);
  } else if (storageInfo?.current_threshold !== undefined) {
    actualThreshold = safeParseFloat(storageInfo.current_threshold, actualThreshold);
  } else if (storageInfo?.similarity_threshold !== undefined) {
    actualThreshold = safeParseFloat(storageInfo.similarity_threshold, actualThreshold);
  }
  
  // Log the result to help debug
  console.log("Threshold determined:", {
    result: actualThreshold,
    from_search_results: searchResults?.similarity_threshold,
    from_storage_current: storageInfo?.current_threshold,
    from_storage_similarity: storageInfo?.similarity_threshold
  });
  
  return actualThreshold;
};

// Helper to create results array from similarities if needed
const processSimilitarityArrays = (searchResults) => {
  // Skip if there's no search results
  if (!searchResults) return searchResults;
  
  // Ensure document filename is proper utf-8 text
  if (searchResults.document_filename) {
    try {
      // Log the raw document filename for debugging
      console.log("Raw document filename:", searchResults.document_filename);
      
      // For Chinese/Japanese/Korean characters, make sure we handle them properly
      const originalFilename = searchResults.document_filename;
      searchResults.document_filename_original = originalFilename;
      
      // Don't try to encode/decode if it might corrupt CJK characters
      if (/[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]/.test(originalFilename)) {
        console.log("Document contains CJK characters, preserving original encoding");
      } else {
        // For non-CJK text, try to fix encoding issues
        try {
          searchResults.document_filename = decodeURIComponent(
            encodeURIComponent(searchResults.document_filename)
              .replace(/%[0-9A-F]{2}/g, match => match)
          );
        } catch (encErr) {
          console.warn("Encoding fix attempt failed, using original:", encErr);
        }
      }
    } catch (err) {
      console.error("Error processing document filename:", err);
    }
  }

  // Create results array from similarities and texts arrays if necessary
  if (searchResults.similarities && Array.isArray(searchResults.similarities) && 
      searchResults.texts && Array.isArray(searchResults.texts) && 
      (!searchResults.results || searchResults.results.length === 0)) {
    
    console.log("Creating results array from similarities and texts arrays");
    searchResults.results = searchResults.similarities.map((similarity, index) => ({
      similarity: similarity,
      text: searchResults.texts[index] || `Result ${index+1}`,
      id: `result-${index}`
    }));
  }
  
  // Make sure similarity threshold is a proper number
  if (searchResults.similarity_threshold !== undefined) {
    searchResults.similarity_threshold = parseFloat(searchResults.similarity_threshold);
  }
  
  return searchResults;
};

// Separate component for search results display
const SearchResultsList = ({ displayResults, resultsAboveThreshold, actualThreshold, t }) => {
  return (
    <ul className="mt-1 pl-4 list-disc text-xs">
      {displayResults.map((result, index) => (
        <li key={`result-${result.id || result.chunk_id || result.text?.substring(0, 20) || Math.random().toString(36).substring(2, 10)}`} 
            className={`text-gray-600 mb-2 ${result.similarity >= actualThreshold ? 'font-medium text-green-700' : ''}`}>
          #{index + 1}: {t('similarity')}: <span className="font-bold">{result.similarity.toFixed(4)}</span>
          {result.similarity >= actualThreshold && 
            <span className="ml-1 text-xs text-green-600"> (✓ {t('aboveThreshold')})</span>
          }
          <div className="ml-2 mt-1 text-xs text-gray-500 border-l-2 border-gray-200 pl-2">
            {result.text?.substring(0, 80)}{result.text?.length > 80 ? '...' : ''}
          </div>
          {result.chunk_id && (
            <div className="ml-2 mt-1 text-xs text-gray-400">
              ID: {result.chunk_id.substring(0, 8)}...
            </div>
          )}
        </li>
      ))}
    </ul>
  );
};

// Debug Info Panel Component
const DebugInfoPanel = ({ debugMode, searchResults, storageInfo, topResults, resultsAboveThreshold, actualThreshold }) => {
  return (
    <div className="mt-3 border border-yellow-300 bg-yellow-50 p-2 rounded">
      <button 
          className="text-xs font-medium text-yellow-800 cursor-pointer border-none bg-transparent p-0 w-full text-left"
          onClick={() => console.log("Full search results:", searchResults)}
          onKeyDown={(e) => e.key === 'Enter' && console.log("Full search results:", searchResults)}
          aria-label="Log debug information to console">
        Debug Information (click to log details to console):
      </button>
      {debugMode && (
        <pre className="mt-1 overflow-auto max-h-40 text-xs text-yellow-700 p-1 bg-yellow-100 rounded">
          {JSON.stringify({
            threshold: {
              search_results: searchResults?.similarity_threshold,
              raw_threshold_value: typeof searchResults?.similarity_threshold,
              storage_info: storageInfo?.similarity_threshold,
              current: storageInfo?.current_threshold,
              actual_used: actualThreshold
            },
            results_count: {
              total: topResults.length,
              above_threshold: resultsAboveThreshold.length,
              raw_result_keys: searchResults ? Object.keys(searchResults) : [],
              has_similarities_array: !!searchResults?.similarities,
              similarities_length: searchResults?.similarities?.length,
              has_results_array: !!searchResults?.results,
              results_length: searchResults?.results?.length
            },
            query: searchResults?.query,            document_info: {
              id: searchResults?.document_id,
              filename: searchResults?.document_filename,
              filename_original: searchResults?.document_filename_original,
              filename_from_search_info: searchResults?.search_info?.document_filename,
              search_id: searchResults?.search_id,
              timestamp: searchResults?.timestamp
            },
            result_file: searchResults?.result_file,
            search_info: searchResults?.search_info,
            results_preview: topResults.slice(0, 3).map(r => ({
              similarity: r.similarity,
              above_threshold: r.similarity >= actualThreshold,
              text_preview: r.text?.substring(0, 30)
            }))
          }, null, 2)}
        </pre>
      )}
      {!debugMode && (
        <div className="mt-1 text-xs text-yellow-700">
          Threshold: <b>{actualThreshold.toFixed(4)}</b> | 
          Results: <b>{topResults.length}</b> | 
          Above threshold: <b>{resultsAboveThreshold.length}</b>
          {topResults.length > 0 && (
            <div>Top similarity: <b>{topResults[0].similarity.toFixed(4)}</b></div>
          )}
        </div>
      )}
    </div>
  );
};

// SearchInfoSection component
const SearchInfoSection = ({ 
  indexId, 
  actualThreshold, 
  searchResults, 
  topResults, 
  displayResults, 
  resultsAboveThreshold, 
  debugMode, 
  t, 
  storageInfo,
  refreshing,
  lastRefreshed
}) => {
  if (!indexId) return null;
  // Make sure to get the clean document name for display
  const getDocumentName = () => {
    // First try to use the document_filename if available
    if (searchResults?.document_filename) {
      // Try to clean up the document name by removing timestamps and hashes
      const filename = searchResults.document_filename;
      
      // Remove any timestamp pattern like _YYYYMMDD at the end
      let cleanName = filename;
      const timestampPattern = /_\d{8}$/;
      if (timestampPattern.test(cleanName)) {
        cleanName = cleanName.replace(timestampPattern, '');
      }
      
      // Limit length for display
      if (cleanName.length > 80) {
        return cleanName.substring(0, 77) + '...';
      }
      
      return cleanName;
    } 
    // Fall back to document_id if no filename is available
    else if (searchResults?.document_id) {
      const docId = searchResults.document_id;
      // Try to remove timestamp and hash portions (e.g., _20250511_164327_e7081f26)
      const timestampHashPattern = /(_\d{8}_\d{6}_[a-f0-9]+)$/;
      let cleanId = docId.replace(timestampHashPattern, '');
      
      // Check if there's another timestamp pattern that needs to be cleaned
      const timestampPattern = /_\d{8}$/;
      if (timestampPattern.test(cleanId)) {
        cleanId = cleanId.replace(timestampPattern, '');
      }
      
      // Limit length for display
      if (cleanId.length > 80) {
        return cleanId.substring(0, 77) + '...';
      }
      
      return cleanId;
    }
    // Try storageInfo for document name
    else if (storageInfo?.document_filename) {
      const filename = storageInfo.document_filename;
      let cleanName = filename;
      
      // Clean any timestamp patterns
      const timestampPattern = /_\d{8}$/;
      if (timestampPattern.test(cleanName)) {
        cleanName = cleanName.replace(timestampPattern, '');
      }
      
      // Limit length
      if (cleanName.length > 80) {
        return cleanName.substring(0, 77) + '...';
      }
      
      return cleanName;
    }
    // Try index name as a fallback
    else if (searchResults?.index_id) {
      return `Index: ${searchResults.index_id}`;
    }
    // If we still have no name, use the indexId from props
    else if (indexId) {
      return `Index: ${indexId}`;
    }
    
    return 'Unknown';
  };
  
  return (
    <div className="mb-4 border-b border-gray-200 pb-3">
      <h3 className="font-medium text-purple-700">{t('currentSearch')}:</h3>
      <div className="mt-2">
        <p className="text-sm">
          <span className="font-medium">{t('indexId')}:</span> {indexId}
        </p>
        <p className="mt-1 text-xs text-gray-600">
          {t('similarityThreshold')}: {actualThreshold.toFixed(4)} 
          <span className="text-xs text-gray-500 ml-1">({t('higherForPrecision')})</span>
        </p>        {/* Display document filename - always show something meaningful */}
        <p className="mt-1 text-xs font-medium text-gray-700">
          {t('documentFilename')}: {getDocumentName()}
          {refreshing && (
            <span className="ml-2 inline-block animate-pulse text-blue-500">
              ⟳ {t('refreshing')}...
            </span>
          )}
          {lastRefreshed && !refreshing && (
            <span className="ml-2 text-gray-500 text-xs">
              {t('lastUpdated')}: {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
        </p>
        
        {/* Display top search results if available */}
        {(searchResults?.query || searchResults?.similarities) && displayResults.length > 0 && (
          <div className="mt-3 bg-blue-50 p-2 rounded">
            <p className="text-xs font-medium text-blue-700">
              {t('topResults')} ({displayResults.length}/{topResults.length}):
              {resultsAboveThreshold.length > 0 && 
                <span className="text-green-600 ml-1">
                  ({resultsAboveThreshold.length} {t('aboveThreshold')})
                </span>
              }
            </p>
            <SearchResultsList 
              displayResults={displayResults} 
              resultsAboveThreshold={resultsAboveThreshold}
              actualThreshold={actualThreshold}
              t={t}
            />
          </div>
        )}
        
        {/* If there are search results but none above threshold */}
        {(resultsAboveThreshold.length === 0 && displayResults.length > 0) && (
          <div className="mt-2 bg-yellow-50 p-2 rounded border border-yellow-200">
            <p className="text-xs text-yellow-800">
              {t('noResultsAboveThreshold')} ({actualThreshold.toFixed(4)})
              {topResults.length > 0 ? ` - ${topResults.length} ${t('resultsFound')} ${t('belowThreshold')}.` : ''}
            </p>
          </div>
        )}
        
        {/* Debug section */}
        {(debugMode || topResults.length > 0) && searchResults && (
          <DebugInfoPanel 
            debugMode={debugMode}
            searchResults={searchResults}
            storageInfo={storageInfo}
            topResults={topResults}
            resultsAboveThreshold={resultsAboveThreshold}
            actualThreshold={actualThreshold}
          />
        )}
      </div>
    </div>
  );
};

// Main component
function StorageInfoPanel({ indexId, forceRefresh = false }) {
  const { t } = useLanguage();
  const [storageInfo, setStorageInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false); // For tracking refresh operations
  const [lastRefreshed, setLastRefreshed] = useState(null); // To show when last refreshed
  const [error, setError] = useState(null);
  const [searchResults, setSearchResults] = useState(null);
  const [debugMode, setDebugMode] = useState(false); // Move debugMode state to top level
    // Add a ref to store the current search results from the parent component
  const appSearchResultsRef = React.useRef(null);
  
  // Safety function to access global search results
  const safeGetGlobalSearchResults = () => {
    try {
      if (typeof window !== 'undefined' && window.verseMindCurrentSearchResults) {
        return window.verseMindCurrentSearchResults;
      }
    } catch (err) {
      console.warn("Error accessing global search results:", err);
    }
    return null;
  };
    // Add keyboard shortcut for debug mode  // Effect to safely access and store the global search results
  useEffect(() => {
    // Use our safety function to get global search results
    const globalSearchResults = safeGetGlobalSearchResults();
    
    if (globalSearchResults) {
      // Only update our ref if the search result matches our index ID
      if (globalSearchResults.index_id === indexId || 
          (globalSearchResults.search_info && globalSearchResults.search_info.index_id === indexId)) {
        console.log("StorageInfoPanel: Found matching global search results", globalSearchResults);
        appSearchResultsRef.current = globalSearchResults;
      }
    }
  }, [indexId, forceRefresh]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl+Alt+D to toggle debug mode
      if (e.ctrlKey && e.altKey && e.key === 'd') {
        setDebugMode(prev => !prev);
        console.log('Debug mode:', !debugMode);
      }
      
      // Ctrl+Alt+R to refresh results
      if (e.ctrlKey && e.altKey && e.key === 'r') {
        console.log('Manually refreshing search results...');
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
        fetchSearchResults(indexId, apiBase, storageInfo);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [debugMode, indexId, storageInfo]);
    // Add auto-refresh for search results
  useEffect(() => {
    if (!indexId) return;
    
    const refreshInterval = 5000; // 5 seconds
    console.log(`Setting up refresh interval (${refreshInterval}ms) for search results...`);
    
    const intervalId = setInterval(() => {
      if (document.hidden) {
        // Don't refresh if the tab is hidden
        return;
      }
      
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      fetchSearchResults(indexId, apiBase, storageInfo);
    }, refreshInterval);
    
    return () => clearInterval(intervalId);
  }, [indexId, storageInfo]);
  // Handle forceRefresh prop by refreshing the search results immediately when it changes
  const forceRefreshRef = React.useRef(forceRefresh);
  
  useEffect(() => {
    // Only trigger a refresh when forceRefresh prop actually changes
    if (!indexId) return;
    
    if (forceRefresh !== forceRefreshRef.current) {
      console.log("StorageInfoPanel: forceRefresh prop changed, refreshing search results...");
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      fetchSearchResults(indexId, apiBase, storageInfo);
      forceRefreshRef.current = forceRefresh;
    }
  }, [forceRefresh, indexId, storageInfo]);
  // Fetch storage info and search results
  useEffect(() => {
    const fetchStorageInfo = async () => {
      setLoading(true);
      setError(null);
      try {
        // First check if we have valid search results in our ref that can be applied directly
        const cachedResults = appSearchResultsRef.current;
        if (cachedResults && cachedResults.index_id === indexId && cachedResults.document_filename) {
          console.log("Using cached search results from App.jsx:", cachedResults);
        }
        
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
        const response = await fetch(`${apiBase}/api/debug/storage-info`);
        if (!response.ok) {
          throw new Error(`Failed to fetch storage info. Status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Always try to get the latest search file for the current index
        if (indexId && indexId === data.search_info?.index_id) {
          console.log("Found matching index ID in storage info:", indexId);
          // Use the most recent search file instead of the one from storage_info
          if (data.recent_search) {
            console.log("Using recent search from storage info:", data.recent_search);
          }
        } else {
          console.log("Index ID mismatch or not found:", indexId, "vs", data.search_info?.index_id);
        }
        
        setStorageInfo(data);
        
        // Fetch search results if indexId is provided
        await fetchSearchResults(indexId, apiBase, data);
      } catch (err) {
        console.error('Error fetching storage info:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStorageInfo();
  }, [indexId]);
  // Helper to create minimal search results structure
  const createMinimalSearchResults = (data, indexId, message) => {
    return {
      similarity_threshold: data?.similarity_threshold,
      document_id: indexId,
      results: [],
      query: message
    };
  };
  
  // Helper to extract data from search results
  const processSearchData = (searchData) => {
    // Make sure we have similarities array if results are present
    if (searchData.results && Array.isArray(searchData.results) && searchData.results.length > 0) {
      // Extract similarities and texts if they're not already present
      if (!searchData.similarities) {
        searchData.similarities = searchData.results.map(r => r.similarity);
      }
      if (!searchData.texts) {
        searchData.texts = searchData.results.map(r => r.text);
      }
    }
    return searchData;
  };
  // Function to fetch search results
  const fetchSearchResults = async (indexId, apiBase, data) => {
    if (!indexId) return;
    
    // Only show loading indicator for initial load, not refreshes
    if (!searchResults) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    
    console.log("Note: Using storage info to determine search results for index ID:", indexId);
    
    try {
      // First, get a list of all search files from the server
      const searchFilesResponse = await fetch(`${apiBase}/api/debug/search-files?index_id=${indexId}`);
      if (searchFilesResponse.ok) {
        const searchFiles = await searchFilesResponse.json();
        console.log("Found search files for index:", searchFiles);
        
        if (Array.isArray(searchFiles) && searchFiles.length > 0) {
          // Sort by timestamp (newest first) and get the most recent file
          const latestSearchFile = searchFiles[0]; // Assuming API returns already sorted
          console.log("Using latest search file:", latestSearchFile);
          
          // Now fetch the actual search results
          const searchResultsResponse = await fetch(`${apiBase}/api/debug/search-results/${latestSearchFile}`);
          
          if (searchResultsResponse.ok) {
            const searchData = await searchResultsResponse.json();
            console.log("Search results loaded:", searchData);
              // Make sure this file matches our index_id
            if (searchData.index_id === indexId) {
              console.log("✅ Search file matches current index ID:", indexId);
                // If there's document_filename in App.jsx's currentSearchResult, use it for consistency
              try {
                // Use our safely stored ref instead of directly accessing window
                const appSearchResult = appSearchResultsRef.current;
                if (searchData.search_id && appSearchResult && 
                    appSearchResult.search_id === searchData.search_id && 
                    appSearchResult.document_filename) {
                  console.log("Using document filename from App.jsx for consistency:", appSearchResult.document_filename);
                  searchData.document_filename = appSearchResult.document_filename;
                }
              } catch (err) {
                console.warn("Error accessing stored search results:", err);
              }
              
              setSearchResults(processSearchData(searchData));
              return;
            }else {
              console.warn("Latest search file has different index ID:", searchData.index_id, "vs", indexId);
            }
          }
        }
      }
      
      // Fallback: If we couldn't get the latest search file or it didn't match,
      // try using the one from storage_info
      if (data?.recent_search) {
        console.log("Fallback: Using recent search from storage info:", data.recent_search);
        const searchResultsResponse = await fetch(`${apiBase}/api/debug/search-results/${data.recent_search}`);
        
        if (searchResultsResponse.ok) {
          const searchData = await searchResultsResponse.json();
          console.log("Search results loaded (from storage info):", searchData);
          setSearchResults(processSearchData(searchData));
        } else {
          console.log("Could not fetch search results file, using basic info");
          setSearchResults(createMinimalSearchResults(data, indexId, "Search results not available"));
        }
      } else {
        // No search files found
        console.log("No search files found for this index");
        setSearchResults(createMinimalSearchResults(data, indexId, "No recent search data available"));
      }    } catch (searchErr) {
      console.error("Error fetching search results file:", searchErr);
      setSearchResults(createMinimalSearchResults(
        data, 
        indexId, 
        "Error loading search results"
      ));
    } finally {
      // Update refresh state regardless of success/failure
      setLoading(false);
      setRefreshing(false);
      setLastRefreshed(new Date());
    }
  };

  if (loading) {
    return (
      <div className="bg-white p-4 rounded-lg shadow-sm mb-4">
        <h2 className="text-lg font-medium mb-2">{t('storageInfo')}</h2>
        <p className="text-gray-500">{t('loading')}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white p-4 rounded-lg shadow-sm mb-4">
        <h2 className="text-lg font-medium mb-2">{t('storageInfo')}</h2>
        <p className="text-red-500">{error}</p>
      </div>
    );
  }
  
  if (!storageInfo) {
    return null;
  }
    // Process searchResults to handle similarities and texts arrays
  const processedResults = processSimilitarityArrays(searchResults);
  
  // Get the actual threshold
  const actualThreshold = determineThreshold(processedResults, storageInfo);
    // Log the threshold to help debug
  console.log("Threshold values:", {
    search_results_threshold: processedResults?.similarity_threshold,
    raw_threshold: processedResults?.similarity_threshold,
    threshold_type: typeof processedResults?.similarity_threshold,
    current_threshold: storageInfo?.current_threshold,
    storage_info_threshold: storageInfo?.similarity_threshold,
    actual_threshold_used: actualThreshold,
    document_filename: processedResults?.document_filename || processedResults?.document_id,
    document_filename_type: typeof processedResults?.document_filename,
    document_filename_length: processedResults?.document_filename?.length,
    search_id: processedResults?.search_id,
    has_search_info: !!processedResults?.search_info,
    search_info_doc_filename: processedResults?.search_info?.document_filename
  });// Process search results
  const topResults = processSearchResults(processedResults);
  
  console.log("Processed top results:", topResults);
  
  // Always show at least the top 5 results regardless of threshold
  const displayResults = topResults.slice(0, 5);
  
  // Separate results above threshold for special handling
  const resultsAboveThreshold = topResults.filter(r => r.similarity >= actualThreshold);

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm mb-4">
      <h2 className="text-lg font-medium mb-2">{t('storageInfo')}</h2>
      
      <div className="text-sm">
        {/* Search Information Section */}      <SearchInfoSection 
          indexId={indexId}
          actualThreshold={actualThreshold}
          searchResults={processedResults}
          topResults={topResults}
          displayResults={displayResults}
          resultsAboveThreshold={resultsAboveThreshold}
          debugMode={debugMode}
          t={t}
          storageInfo={storageInfo}
          refreshing={refreshing}
          lastRefreshed={lastRefreshed}
        />

        {/* Vector Database Location */}
        <div className="mb-2">
          <h3 className="font-medium">{t('vectorDatabaseLocation')}:</h3>
          <div className="bg-gray-50 p-2 rounded mt-1 font-mono text-xs">
            {storageInfo.indices_dir}
          </div>
        </div>
        
        {/* Embeddings Location */}
        <div className="mb-2">
          <h3 className="font-medium">{t('embeddingsLocation')}:</h3>
          <div className="bg-gray-50 p-2 rounded mt-1 font-mono text-xs">
            {storageInfo.embeddings_dir}
          </div>
        </div>
        
        {/* Active Vector Databases */}
        {storageInfo.vector_db_paths && (
          <div className="mb-2">
            <h3 className="font-medium">{t('activeVectorDatabases')}:</h3>
            <ul className="list-disc list-inside mt-1">
              {Object.entries(storageInfo.vector_db_paths).map(([dbName, dbPath]) => (
                <li key={dbName} className="mt-1">
                  <span className="font-medium">{dbName}: </span>
                  <span className="font-mono text-xs bg-gray-50 p-1 rounded">{dbPath}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Statistics Section */}
        <div className="mt-3 pt-2 border-t border-gray-100">
          <h3 className="font-medium text-gray-700">{t('statistics')}:</h3>
          <div className="mt-1 grid grid-cols-2 gap-2">
            {storageInfo.total_indices && (
              <div className="bg-blue-50 p-2 rounded">
                <p className="text-xs font-medium text-blue-800">
                  {t('totalIndices')}
                </p>
                <p className="text-lg font-bold text-blue-700">
                  {storageInfo.total_indices}
                </p>
              </div>
            )}
            
            {/* Embeddings Files */}
            {storageInfo.total_embeddings && (
              <div className="bg-purple-50 p-2 rounded">
                <p className="text-xs font-medium text-purple-800">
                  {t('embeddingFiles')}
                </p>
                <p className="text-lg font-bold text-purple-700">
                  {storageInfo.total_embeddings}
                </p>
              </div>
            )}
            
            {/* Similarity Range */}
            {indexId && (
              <div className="col-span-2 mt-2 bg-gray-50 p-2 rounded">
                <p className="text-xs font-medium text-gray-700">
                  {t('similarityRange')}
                </p>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-gray-500">0</span>
                  <div className="w-full mx-2 h-3 bg-gray-200 rounded relative">
                    <div className="absolute top-0 left-0 h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded" 
                         style={{width: '100%'}}>
                    </div>                    
                    <div className="absolute top-0 left-0 h-full w-px bg-black" 
                         style={{left: `${Math.max(actualThreshold, 0) * 100}%`}}>
                      <div className="relative top-3 -ml-1 text-xs">↑</div>                    
                      <div className="relative top-4 -ml-6 text-xs">{actualThreshold.toFixed(4)}</div>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500">1</span>
                </div>
                <p className="text-xs text-center mt-3 text-gray-600">
                  {t('thresholdExplanation')}
                </p>
              </div>
            )}
          </div>
        </div>
        
        {/* Recent Searches */}
        {storageInfo.recent_search && (
          <div className="mt-4 pt-3 border-t border-gray-200">
            <h3 className="font-medium text-gray-700">{t('recentSearches')}:</h3>
            <div className="bg-gray-50 p-2 rounded mt-1">
              <p className="text-xs text-gray-600 break-all">
                {storageInfo.recent_search}
              </p>
            </div>
            <p className="mt-2 text-xs text-gray-500">
              {t('similarityExplanation')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Define prop types
SearchResultsList.propTypes = {
  displayResults: PropTypes.array.isRequired,
  resultsAboveThreshold: PropTypes.array.isRequired,
  actualThreshold: PropTypes.number.isRequired,
  t: PropTypes.func.isRequired,
};

DebugInfoPanel.propTypes = {
  debugMode: PropTypes.bool.isRequired,
  searchResults: PropTypes.object,
  storageInfo: PropTypes.object.isRequired,
  topResults: PropTypes.array.isRequired,
  resultsAboveThreshold: PropTypes.array.isRequired,
  actualThreshold: PropTypes.number.isRequired,
};

SearchInfoSection.propTypes = {
  indexId: PropTypes.string,
  actualThreshold: PropTypes.number.isRequired,
  searchResults: PropTypes.object,
  topResults: PropTypes.array.isRequired,
  displayResults: PropTypes.array.isRequired,
  resultsAboveThreshold: PropTypes.array.isRequired,
  debugMode: PropTypes.bool.isRequired,
  t: PropTypes.func.isRequired,
  storageInfo: PropTypes.object.isRequired,
  refreshing: PropTypes.bool,
  lastRefreshed: PropTypes.instanceOf(Date)
};

StorageInfoPanel.propTypes = {
  indexId: PropTypes.string,
  forceRefresh: PropTypes.bool
};

// Define default props
StorageInfoPanel.defaultProps = {
  indexId: null,
  forceRefresh: false
};

export default StorageInfoPanel;
