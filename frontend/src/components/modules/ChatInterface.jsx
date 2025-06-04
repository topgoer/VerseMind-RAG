/* eslint-disable */
// @ts-nocheck
// Tell TypeScript to ignore this file completely
import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';
import StorageInfoPanel from './StorageInfoPanel'; // 导入StorageInfoPanel组件
import DocumentContextDisplay from './DocumentContextDisplay';

function ChatInterface({ 
  indices,
  documents,  // Add documents prop
  loading, 
  error, 
  onSendMessage, 
  chatHistory, 
  currentTask, 
  taskProgress 
}) {
  const { t } = useLanguage();
  const [inputMessage, setInputMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
    // States for custom dropdown
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [highlightedIndex] = useState(-1);
  const dropdownRef = useRef(null);
  
  // Helper function to determine index type label
  const getIndexTypeLabel = (indexVal, indicesArray) => {
    if (indicesArray.some(idx => idx.index_id === indexVal)) {
      return `(${t('usingIndexId')})`;
    }
    
    if (indicesArray.some(idx => idx.collection_name === indexVal)) {
      return `(${t('usingCollectionName')})`;
    }
    
    return '';
  };
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedIndex, setSelectedIndex] = useState('');
  const [selectedImage, setSelectedImage] = useState(null); // State for selected image
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);
  
  // Helper function to format timestamps safely
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    
    try {
      // Handle different timestamp formats
      if (typeof timestamp === 'string') {
        // If it's already a formatted date string (e.g. "5/16/2025, 10:30:45 AM")
        if (timestamp.includes('/') && timestamp.includes(':')) {
          return timestamp;
        }
        
        // Try to parse as date
        const date = new Date(timestamp);
        if (!isNaN(date.getTime())) {
          return date.toLocaleString();
        }
      }
      
      // If timestamp is a number (Unix timestamp)
      if (typeof timestamp === 'number') {
        return new Date(timestamp).toLocaleString();
      }
      
      // If we couldn't parse it, return as is
      return timestamp;
    } catch (error) {
      console.error('Error formatting timestamp:', error);
      return timestamp || '';
    }
  };
  // Add new states for search parameters
  const [similarityThreshold, setSimilarityThreshold] = useState(0.5);
  const [topK, setTopK] = useState(3);
  const [temperature] = useState(0.7); // Add temperature state with default 0.7
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
    // 全新的滚动相关状态和引用
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true); // 是否启用自动滚动
  const chatEndRef = useRef(null); // 聊天结束引用点
  const chatContainerRef = useRef(null); // 聊天容器引用
  const lastUserScrollTopRef = useRef(0); // 记录用户上次滚动位置
  const lockScrollUpdateRef = useRef(false); // 锁定滚动更新，防止程序滚动被检测为用户滚动
  
  const imageInputRef = useRef(null); // Ref for hidden file input
  const textareaRef = useRef(null);
  // 复制功能状态
  const [copiedMsgId, setCopiedMsgId] = useState(null);
  const [copiedType, setCopiedType] = useState(null); // 'text' or 'md'

  // 复制内容到剪贴板  
  const handleCopy = async (msg, type) => {
    let content;
    if (type === 'md') {
      // 假设 message.text 已经是 markdown 格式，否则可自定义转换
      content = msg.text || '';
    } else {
      // 纯文本，去除 markdown 语法
      content = (msg.text || '').replace(/[`*_#\-[\]()>!]/g, '');
    }
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMsgId(msg.id || msg.timestamp);
      setCopiedType(type);
      setTimeout(() => {
        setCopiedMsgId(null);
        setCopiedType(null);
      }, 2000);
    } catch (e) {
      console.error("Failed to copy to clipboard:", e);
      // Display error in UI (optional)
      // You could set a state variable here to show a short error toast/notification
      setCopiedMsgId(null);
      setCopiedType(null);
    }
  };

  // Load config and set defaults
  // Load config on component mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const configData = await loadConfig();
        // console.log("[ChatInterface] Config loaded:", configData);
        setConfig(configData);
        setConfigLoading(false);
        
        if (configData?.model_groups) {
          const availableProviders = Object.keys(configData.model_groups);
          if (availableProviders.length > 0) {
            const defaultProvider = availableProviders[0];
            setSelectedProvider(defaultProvider);
            if (configData.model_groups[defaultProvider]?.length > 0) {
              setSelectedModel(configData.model_groups[defaultProvider][0].id);
            }
          }
        }
        
        // Set default search parameters from config if available
        if (configData?.search_params?.similarity_threshold) {
          setSimilarityThreshold(configData.search_params.similarity_threshold);
        }
        if (configData?.search_params?.top_k) {
          setTopK(configData.search_params.top_k);
        }
      } catch (error) {
        console.error("[ChatInterface] Error loading config:", error);
        setConfigLoading(false);
      }
    };
    
    fetchConfig();
  }, []);
  
  // Monitor indices prop for changes
  useEffect(() => {
    // Only run this logic if indices changes and is valid
    if (!indices) {
      // console.warn("[ChatInterface] Indices prop is null or undefined");
      return;
    }
      if (!Array.isArray(indices)) {
      console.error("[ChatInterface] Indices prop is not an array:", typeof indices, indices);
      return;
    }
    
    // Process indices silently without logging
    
    if (indices.length === 0) {
      // console.warn("[ChatInterface] Indices array is empty");
      // If there are no indices, attempt to check if the backend API is available
      const checkBackendAvailability = async () => {
        try {
          const response = await fetch('/api/health');
          // console.log("[ChatInterface] Backend health check:", response.ok ? 'OK' : 'Not OK');
        } catch (err) {
          console.error("[ChatInterface] Backend may not be available:", err);
        }
      };
      checkBackendAvailability();
    }
  }, [indices]);

  // 监控聊天容器的滚动事件并处理自动滚动行为
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;
    
    const handleScroll = () => {
      // 如果滚动操作被锁定(程序触发的滚动)，则忽略此次事件
      if (lockScrollUpdateRef.current) return;
      
      const { scrollTop, scrollHeight, clientHeight } = container;
      
      // 更新用户上次滚动位置
      lastUserScrollTopRef.current = scrollTop;
      
      // 滚动到距离底部50px内视为"接近底部"
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
      
      // 更新自动滚动状态
      setAutoScrollEnabled(isNearBottom);
    };
    
    // 添加滚动事件监听
    container.addEventListener('scroll', handleScroll);
    
    // 清理函数
    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, []);
  // Manual scroll function - only scroll when explicitly called
  const scrollToBottom = () => {
    // Lock scroll monitoring to prevent this programmatic scroll from being detected as user scroll
    lockScrollUpdateRef.current = true;
    
    setTimeout(() => {
      try {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        
        // Unlock after scroll animation completes
        setTimeout(() => {
          lockScrollUpdateRef.current = false;
        }, 300);
      } catch (err) {
        console.error("Error scrolling to bottom:", err);
        lockScrollUpdateRef.current = false;
      }
    }, 100);
  };

  // 自动调整输入框高度
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    }
  }, [inputMessage]);

  // Handle provider change
  const handleProviderChange = (e) => {
    const newProvider = e.target.value;
    setSelectedProvider(newProvider);
    
    if (config?.model_groups?.[newProvider]?.length > 0) {
      setSelectedModel(config.model_groups[newProvider][0].id);
    } else {
      setSelectedModel(''); // Reset model if provider has no models
    }
  };

  // Handle image selection
  const handleImageSelect = (event) => {
    const file = event.target.files[0];
    if (file?.type.startsWith('image/')) {
      setSelectedImage(file);
    }
    // Reset file input value to allow selecting the same file again
    if (imageInputRef.current) {
      imageInputRef.current.value = null;
    }
  };

  // Clear selected image
  const clearSelectedImage = () => {
    setSelectedImage(null);
    if (imageInputRef.current) {
      imageInputRef.current.value = null;
    }
  };

  // Function to check if the input is an index ID or collection name
  const getInputType = (input) => {
    if (!input || !Array.isArray(indices)) return null;
    
    // Check if this matches any known index ID
    const isIndexId = indices.some(idx => idx.index_id === input);
    if (isIndexId) return 'index_id';
    
    // Check if this matches any known collection name
    const isCollectionName = indices.some(idx => idx.collection_name === input);
    if (isCollectionName) return 'collection_name';
    
    // If neither, assume it's a collection name as that's more common
    return 'collection_name';
  };
    // Get document filename by index ID or collection name
  const getDocumentFilenameByIndexId = (indexId) => {
    if (!indexId || !Array.isArray(indices)) return indexId;
    
    // Check if it's a collection name
    if (indices.some(idx => idx.collection_name === indexId)) {
      return `${t('collection')}: ${indexId}`;
    }
    
    // If it's an index ID, find the corresponding document
    const index = indices.find(idx => idx.index_id === indexId);
    if (!index) return indexId;
    
    // First priority: Try to find document filename from documents array
    if (Array.isArray(documents)) {
      const doc = documents.find(d => d.id === index.document_id);
      if (doc?.filename) {
        return doc.filename;
      }
    }
    
    // Second priority: Use document_filename if available
    if (index.document_filename) {
      return index.document_filename;
    }
      // Third priority: Use full document information
    if (index.collection_name) {
      // Get document identifier (use full document filename if available or truncated ID as backup)
      let displayDocName = '';
      
      if (index.document_filename) {
        displayDocName = index.document_filename;
      } else if (index.document_id) {
        displayDocName = `${t('document')} ${index.document_id.substring(0, 8)}`;
      }
      
      // Format as "Collection Name / Document Name" for clearer identification
      if (displayDocName) {
        return `${index.collection_name} / ${displayDocName}`;
      } else {
        return index.collection_name;
      }
    }
    
    // Last resort, make the index ID more user-friendly
    return `${t('document')} ${indexId.substring(0, 8)}`;
  };
    // Function to handle sending message with scroll
  const handleSendWithScroll = () => {
    handleSendMessage();
  // Scroll to bottom after sending
    setTimeout(() => scrollToBottom(), 100);
  };
  
  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }
    
    // Add event listener
    document.addEventListener('mousedown', handleClickOutside);
    
    // Clean up
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // Handle send message
  const handleSendMessage = () => {
    // Allow sending only image, only text, or both
    if ((!inputMessage.trim() && !selectedImage) || !selectedModel) return;
    
    const inputType = getInputType(selectedIndex);
    // console.log('[ChatInterface][handleSendMessage] selectedIndex:', selectedIndex, 'type:', inputType);
    
    if (typeof onSendMessage === 'function') {
      // Get all indices to search based on selection
      let indexInfo = {
        source: selectedIndex,
        isIndexId: inputType === 'index_id',
        type: inputType || 'collection_name',
        displayName: inputType === 'index_id' ? getDocumentFilenameByIndexId(selectedIndex) : selectedIndex
      };
      
      // If this is a collection name, we'll include this information to help the backend search all indices in this collection
      if (inputType === 'collection_name' && Array.isArray(indices)) {
        // Find all indices in this collection
        const collectionIndices = indices.filter(idx => idx.collection_name === selectedIndex);
        if (collectionIndices.length > 0) {
          indexInfo.collectionIndices = collectionIndices.map(idx => idx.index_id);
        }
      }
      
      // 创建搜索参数对象
      const searchParams = {
        similarityThreshold: similarityThreshold,
        topK: topK,
        temperature: temperature, // Include temperature parameter
        inputType: inputType, // Adding input type for better context
        // Add information about whether this is a collection or index ID
        searchInfo: selectedIndex ? indexInfo : null
      };
      
      // Pass the necessary parameters to onSendMessage (which is handleSearchAndGenerate)
      // This will first search the index and then generate text based on the search results
      // If no index is selected, it will generate text without search context
      onSendMessage(selectedIndex || null, inputMessage, selectedProvider, selectedModel, selectedImage, searchParams);
    } else {
      console.error("CRITICAL ERROR: onSendMessage prop in ChatInterface is not a function!", {
        propType: typeof onSendMessage,
        propValue: onSendMessage
      });
      // Optionally, display an error to the user here
    }
    
    setInputMessage('');
    clearSelectedImage(); // Clear image after sending
    
    // 确保发送消息后100%滚动到底部
    setTimeout(() => {
      lockScrollUpdateRef.current = true;
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      setTimeout(() => {
        lockScrollUpdateRef.current = false;
      }, 300);
    }, 100);
    
    // 重置高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };
  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendWithScroll();
    }
  };

  // 添加存储信息功能
  const [showStorageInfo, setShowStorageInfo] = useState(false);
  
  // No need to import DocumentContextDisplay here since we're importing it at the top
  
  return (
    <div className="flex flex-col h-full w-full bg-white">
      {/* 存储信息按钮 - 调整顶部位置与语言按钮对齐 */}
      <div className="absolute top-4 right-24 z-10">
        <button 
          onClick={() => setShowStorageInfo(!showStorageInfo)}
          className="text-xs px-2 py-1 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 flex items-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {showStorageInfo ? t('hideStorageInfo', '隐藏存储信息') : t('showStorageInfo', '显示存储信息')}
        </button>
      </div>
      
      {/* 显示存储信息面板 */}
      {showStorageInfo && (
        <div className="absolute top-12 right-2 z-20 w-96">
          <StorageInfoPanel 
            indexId={selectedIndex} 
            forceRefresh={true} 
            key={`storage-panel-${selectedIndex}-${chatHistory.length}`} // Force re-render when chat history changes or index changes
          />
        </div>
      )}
      
      {/* 选择区域 */}
      <div className="w-full flex flex-wrap items-center gap-4 px-6 py-3 bg-white border-b border-gray-200" style={{zIndex:2}}>
        {/* 索引选择 */}
        <div className="flex flex-col">          <label className="text-xs text-gray-500 mb-1 flex items-center">
            {t('selectCollection', '选择集合')} 
            <div className="ml-1 group relative">
              <span className="cursor-help text-gray-400 hover:text-blue-500">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </span>
              <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block bg-white shadow-lg rounded-md p-2 text-xs w-64 border border-gray-200 z-50">
                <p>{t('indexCollectionHelp')}</p>
              </div>
            </div>
          </label>          <div className="relative" ref={dropdownRef}>
            <div
              className={`min-w-[180px] px-2 py-1 pr-16 border rounded-md flex items-center cursor-pointer ${
                (() => {
                  if (!selectedIndex) return 'border-gray-300';
                  const isIndexId = indices && Array.isArray(indices) && indices.some(idx => idx.index_id === selectedIndex);
                  return isIndexId ? 'border-blue-400 bg-blue-50' : 'border-green-400 bg-green-50';
                })()
              }`}
              onClick={() => !configLoading && !loading && setIsDropdownOpen(prev => !prev)}
            >{selectedIndex ? (                <div 
                  className="text-sm overflow-hidden text-ellipsis whitespace-normal max-w-[450px]" 
                  title={getDocumentFilenameByIndexId(selectedIndex)}
                  style={{
                    wordBreak: 'break-word',
                    lineHeight: '1.4',
                    padding: '2px 0',
                    fontWeight: '500'
                  }}
                >
                  {getDocumentFilenameByIndexId(selectedIndex)}
                </div>
              ) : (
                <div className="text-gray-400 text-sm">{t('indexOrCollectionPlaceholder')}</div>
              )}
            </div>
            {selectedIndex && (
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center">
                {indices && Array.isArray(indices) && indices.some(idx => idx.index_id === selectedIndex) ?
                  <span className="text-blue-500 text-xs bg-blue-50 px-1 rounded mr-1" title={t('usingIndexId')}>ID</span> :
                  <span className="text-green-500 text-xs bg-green-50 px-1 rounded mr-1" title={t('usingCollectionName')}>COL</span>
                }
                <button 
                  className="text-gray-400 hover:text-gray-600"
                  title={t('clearSelection')}
                  onClick={() => setSelectedIndex('')}
                  disabled={configLoading || loading}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}            {/* 显示当前选择的文档名称 */}            {/* Removed redundant document name display since it's now in the main input field */}
          
            {/* Custom dropdown menu */}
            {isDropdownOpen && (
              <div 
                className="absolute mt-1 w-full min-w-[180px] max-w-4xl bg-white border border-gray-300 rounded-md shadow-lg z-50 max-h-[400px] overflow-y-auto"
                style={{ overflowX: 'hidden' }}
              >
                {/* Clear selection option */}
                <button 
                  type="button"
                  className="w-full text-left px-3 py-2 hover:bg-gray-100 font-semibold text-gray-600 border-b border-gray-200"
                  onClick={() => {
                    setSelectedIndex("");
                    setIsDropdownOpen(false);
                  }}
                >
                  --- {t('noSelection', 'No Selection')} ---
                </button>
                  {/* Collection name options with count information */}
                {Array.isArray(indices) && 
                  Object.entries(indices.reduce((collections, idx) => {
                    if (typeof idx === 'object' && idx !== null) {
                      const collName = idx.collection_name || t('default', 'default');
                      if (!collections[collName]) collections[collName] = [];
                      collections[collName].push(idx);
                    }
                    return collections;
                  }, {})).map(([collectionName, collIndices]) => (
                    <button
                      type="button"
                      key={`collection-${collectionName}`}
                      className="w-full text-left px-3 py-2 hover:bg-gray-100 font-semibold bg-green-50"                        
                      onClick={() => {
                        setSelectedIndex(collectionName);
                        setIsDropdownOpen(false);
                      }}
                    >
                      📁 {collectionName} ({collIndices.length} {t('indices', 'indices')})
                    </button>
                  ))
                }
              </div>
            )}
          </div>          {/* End of Collection dropdown */}
        </div>
        {/* 供应商选择 */}
        <div className="flex flex-col">
          <label className="text-xs text-gray-500 mb-1">{t('provider')}</label>
          <select
            className="min-w-[120px] px-2 py-1 border border-gray-300 rounded-md"
            value={selectedProvider}
            onChange={handleProviderChange}
            disabled={configLoading || loading}
          >
            {config?.model_groups && Object.keys(config.model_groups).map(provider => (
              <option key={provider} value={provider}>{provider}</option>
            ))}
          </select>
        </div>
        {/* 模型选择 */}
        <div className="flex flex-col">
          <label className="text-xs text-gray-500 mb-1">{t('model')}</label>
          <select
            className="min-w-[160px] px-2 py-1 border border-gray-300 rounded-md"
            value={selectedModel}
            onChange={e => setSelectedModel(e.target.value)}
            disabled={configLoading || loading || !selectedProvider}
          >
            {config?.model_groups?.[selectedProvider]?.map(model => (
              <option key={model.id} value={model.id}>{model.name}</option>
            ))}
          </select>
        </div>
        {/* 高级设置 */}
        <div className="flex flex-col">
          <label className="text-xs text-gray-500 mb-1">{t('advancedSettings')}</label>
          <button
            className="px-2 py-1 border border-gray-300 rounded-md"
            onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
          >
            {showAdvancedSettings ? t('hide') : t('show')}
          </button>
        </div>
        {showAdvancedSettings && (
          <div className="flex flex-wrap gap-4 mt-2">
            <div className="flex flex-col">
              <label className="text-xs text-gray-500 mb-1">{t('similarityThreshold')}</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={similarityThreshold}
                onChange={e => setSimilarityThreshold(parseFloat(e.target.value))}
                className="px-2 py-1 border border-gray-300 rounded-md"
              />
            </div>
            <div className="flex flex-col">
              <label className="text-xs text-gray-500 mb-1">{t('topK')}</label>
              <input
                type="number"
                min="1"
                value={topK}
                onChange={e => setTopK(parseInt(e.target.value, 10))}
                className="px-2 py-1 border border-gray-300 rounded-md"
              />
            </div>
          </div>
        )}
      </div>
      
      {/* 聊天消息区 - 添加可视化指示器，总是显示滚动状态 */}
      <div 
        ref={chatContainerRef} 
        className="flex-1 overflow-y-auto px-0 py-4 w-full relative" 
        style={{background:'#f7f7fa'}}
      >
        {/* 可选：添加可视化的自动滚动状态指示器 
        <div 
          className={`absolute top-2 right-2 px-2 py-1 text-xs rounded-full transition-opacity duration-300 ${
            autoScrollEnabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
          style={{opacity: 0.7, zIndex: 10}}
        >
          {autoScrollEnabled ? 'Auto-scroll on' : 'Auto-scroll off'}
        </div>
        */}
        
        {Array.isArray(chatHistory) && chatHistory.map((message, index) => (
          <div key={message.id || index} className="w-full mb-2">
            {/* 新增：显示 sender 和时间戳 */}
            <div className="flex items-center text-xs text-gray-500 mb-1 px-5">
              <span className="font-semibold">
                {message.sender === 'user' ? t('user') : (message.model || t('assistant'))}
              </span>
              <span className="mx-2">·</span>
              <span>{formatTimestamp(message.timestamp)}</span>
              
              {/* Show collection or index information for assistant messages */}
              {message.sender === 'assistant' && message.searchInfo && (
                <>
                  <span className="mx-2">·</span>
                  <span className="flex items-center">
                    {(() => {
                      // Handle index ID case
                      if (message.searchInfo.isIndexId) {
                        return (
                          <span className="text-xs bg-blue-50 text-blue-500 px-1 rounded" title={t('usingIndexId')}>
                            {message.searchInfo.displayName || t('indexSource', {id: message.searchInfo.source?.substring(0, 8) || ''})}
                          </span>
                        );
                      }
                      // Handle collection source case
                      else if (message.searchInfo.source) {
                        return (
                          <span className="text-xs bg-green-50 text-green-500 px-1 rounded" title={t('usingCollectionName')}>
                            {t('collectionSource', {name: message.searchInfo.source})}
                            {message.searchInfo.collectionIndices ? 
                              ` (${message.searchInfo.collectionIndices.length})` : ''}
                          </span>
                        );
                      }
                      // Default case
                      return null;
                    })()}
                  </span>
                </>
              )}
              
              {/* 复制按钮组 */}
              <span className="ml-auto flex gap-1">
                <button
                  className="px-1 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-200 transition"
                  title="Copy as text"
                  onClick={() => handleCopy(message, 'text')}
                  style={{minWidth:'28px'}}
                >
                  {copiedMsgId === (message.id || message.timestamp) && copiedType === 'text' ? '✔️' : 'TXT'}
                </button>
                <button
                  className="px-1 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-200 transition"
                  title="Copy as markdown"
                  onClick={() => handleCopy(message, 'md')}
                  style={{minWidth:'28px'}}
                >
                  {copiedMsgId === (message.id || message.timestamp) && copiedType === 'md' ? '✔️' : 'MD'}
                </button>
              </span>
            </div>
            <div
              className={`w-full max-w-full rounded-lg px-5 py-3 shadow-sm
                ${message.sender === 'user' ? 'bg-blue-50' : 'bg-gray-100'}
                text-gray-900 whitespace-pre-wrap break-words`}
              style={{marginLeft:0, marginRight:0}}
            >
              {message.image && (
                <div className="mb-3">
                  <img 
                    src={message.image} 
                    alt="Attached" 
                    className="max-w-full max-h-64 object-contain rounded"
                  />
                </div>
              )}
              {message.generatedImage && (
                <div className="mb-3">
                  <img 
                    src={message.generatedImage} 
                    alt="AI Generated" 
                    className="max-w-full max-h-64 object-contain rounded"
                  />
                </div>
              )}
              {/* 显示消息是对图像的回应的指示器 */}
              {message.respondsToImage && (
                <div className="text-xs text-gray-500 mb-2">
                  <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded-full flex items-center inline-block">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    {t('responseToImage')}
                  </span>
                </div>
              )}
              {/* 始终显示完整的消息文本 */}
              {message.text}
              
              {/* 只有在消息文本中没有文档上下文部分时才显示DocumentContextDisplay组件 */}
              {message.sender === 'ai' && message.documentContext && 
                !message.text.includes(`**[${t('usingDocumentContext')}]**`) && 
                !message.text.includes('**[Using Document Context]**') && 
                !message.text.includes('**[使用文档上下文]**') &&
                !message.text.includes('---') && (
                  <DocumentContextDisplay message={message} />
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="w-full mb-2">
            <div className="w-full max-w-full rounded-lg px-5 py-3 shadow-sm bg-gray-100 text-gray-900">
              <span className="text-sm">{t('processing')}...</span>
            </div>
          </div>
        )}
        {currentTask && (
          <div className="w-full mb-2">
            <div className="w-full max-w-full rounded-lg px-5 py-3 shadow-sm bg-blue-100 text-blue-900">
              <p className="text-sm font-medium">{t('executingTask')}: {t(currentTask.type)}</p>
              <p className="text-xs">{taskProgress}</p>
            </div>
          </div>
        )}
        {error && (
          <div className="w-full mb-2">
            <div className="w-full max-w-full rounded-lg px-5 py-3 shadow-sm bg-red-100 text-red-900">
              <p className="text-sm font-medium">{t('error')}</p>
              <p className="text-xs">{error}</p>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
        
        {/* 添加手动滚动控制按钮 */}
        {chatHistory.length > 3 && (
          <div className="fixed bottom-20 right-4">
            <button
              className={`w-10 h-10 rounded-full shadow-md flex items-center justify-center transition-colors ${
                autoScrollEnabled ? 'bg-blue-50 text-blue-500' : 'bg-gray-100 text-gray-500 hover:bg-blue-50 hover:text-blue-500'
              }`}
              onClick={() => {
                setAutoScrollEnabled(true);
                chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
              }}
              title={autoScrollEnabled ? t('autoScrollEnabled') : t('scrollToBottom')}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            </button>
          </div>
        )}
      </div>
      
      {/* 输入栏固定在底部 */}
      <div className="w-full bg-white border-t p-2 sticky bottom-0 left-0 z-10" style={{boxShadow:'0 -2px 8px rgba(0,0,0,0.03)'}}>
        {/* 显示已选择的图片 */}
        {selectedImage && (
          <div className="mb-2 relative inline-block">
            <div className="border border-gray-300 rounded-md p-1 relative">
              <img 
                src={URL.createObjectURL(selectedImage)} 
                alt="Selected" 
                className="h-20 object-contain rounded"
              />
              <button
                onClick={clearSelectedImage}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center"
                title={t('removeImage', '移除图片')}
              >
                <span>×</span>
              </button>
            </div>
          </div>
        )}
        <div className="flex items-end space-x-2">
          <input
            type="file"
            ref={imageInputRef}
            onChange={handleImageSelect}
            accept="image/png, image/jpeg, image/webp, image/gif"
            className="hidden"
          />
          <button
            onClick={() => imageInputRef.current?.click()}
            className="p-2 text-gray-500 hover:text-purple-600 border border-gray-300 rounded-md bg-white"
            title={t('attachImage')}
            disabled={loading || configLoading}
          >
            <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48'%3E%3C/path%3E%3C/svg%3E" 
                 alt="Attach" 
                 className="w-5 h-5" />
          </button>
          <textarea
            ref={textareaRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onInput={e => {
              e.target.style.height = 'auto';
              e.target.style.height = e.target.scrollHeight + 'px';
            }}
            onKeyPress={handleKeyPress}
            placeholder={t('chatPlaceholder')}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 resize-none"
            rows={2}
            style={{minHeight:'32px', maxHeight:'216px', overflowY:'auto'}}
            disabled={loading || configLoading}
          />          <button
            onClick={handleSendWithScroll}
            disabled={(!inputMessage.trim() && !selectedImage) || loading || configLoading}
            className={`px-4 py-2 rounded-md text-white self-stretch flex items-center justify-center ${
              (!inputMessage.trim() && !selectedImage) || loading || configLoading
                ? 'bg-purple-400 cursor-not-allowed'
                : 'bg-purple-600 hover:bg-purple-700'
            }`}
          >
            {t('send')}
          </button>
        </div>
      </div>
    </div>
  );
}

// Add PropTypes validation for component props
ChatInterface.propTypes = {
  indices: PropTypes.arrayOf(
    PropTypes.shape({
      index_id: PropTypes.string,
      collection_name: PropTypes.string,
      document_id: PropTypes.string,
      document_filename: PropTypes.string
    })
  ),
  documents: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      filename: PropTypes.string
    })
  ),
  loading: PropTypes.bool,
  error: PropTypes.string,
  onSendMessage: PropTypes.func.isRequired,
  chatHistory: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      sender: PropTypes.string.isRequired,
      text: PropTypes.string,
      timestamp: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      image: PropTypes.any,
      documentContext: PropTypes.object
    })
  ),
  currentTask: PropTypes.object,
  taskProgress: PropTypes.string
};

// Add default props
ChatInterface.defaultProps = {
  indices: [],
  documents: [],
  loading: false,
  error: null,
  chatHistory: [],
  currentTask: null,
  taskProgress: ''
};

export default ChatInterface;
