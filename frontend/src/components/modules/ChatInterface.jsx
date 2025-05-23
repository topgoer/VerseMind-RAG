import React, { useState, useEffect, useRef } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';
import ReactMarkdown from 'react-markdown';
import { Paperclip, X } from 'lucide-react'; // Import icons
import StorageInfoPanel from './StorageInfoPanel'; // 导入StorageInfoPanel组件

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
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const chatEndRef = useRef(null);
  const imageInputRef = useRef(null); // Ref for hidden file input
  const textareaRef = useRef(null);

  // 复制功能状态
  const [copiedMsgId, setCopiedMsgId] = useState(null);
  const [copiedType, setCopiedType] = useState(null); // 'text' or 'md'

  // 复制内容到剪贴板
  const handleCopy = async (msg, type) => {
    let content = msg.text || '';
    if (type === 'md') {
      // 假设 message.text 已经是 markdown 格式，否则可自定义转换
      content = msg.text || '';
    } else {
      // 纯文本，去除 markdown 语法
      content = (msg.text || '').replace(/[`*_#>\-\[\]()>!]/g, '');
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
      // 可选：提示失败
    }
  };

  // Load config and set defaults
  useEffect(() => {
    const fetchConfig = async () => {
      setConfigLoading(true);
      const configData = await loadConfig();
      setConfig(configData);
      setConfigLoading(false);
      console.log("[LOG][ChatInterface] Config loaded, setting configLoading to false. New state:", false);
      
      if (configData && configData.model_groups) {
        const availableProviders = Object.keys(configData.model_groups);
        if (availableProviders.length > 0) {
          const defaultProvider = availableProviders[0];
          setSelectedProvider(defaultProvider);
          if (configData.model_groups[defaultProvider] && configData.model_groups[defaultProvider].length > 0) {
            setSelectedModel(configData.model_groups[defaultProvider][0].id);
          }
        }
      }
      
      // Set default search parameters from config if available
      if (configData && configData.search_params) {
        if (configData.search_params.similarity_threshold) {
          setSimilarityThreshold(configData.search_params.similarity_threshold);
        }
        if (configData.search_params.top_k) {
          setTopK(configData.search_params.top_k);
        }
      }
    };
    
    fetchConfig();
  }, []);

  // Scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

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
    
    if (config && config.model_groups && config.model_groups[newProvider] && config.model_groups[newProvider].length > 0) {
      setSelectedModel(config.model_groups[newProvider][0].id);
    } else {
      setSelectedModel(''); // Reset model if provider has no models
    }
  };

  // Handle image selection
  const handleImageSelect = (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
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

  // Handle send message
  const handleSendMessage = () => {
    // Allow sending only image, only text, or both
    if ((!inputMessage.trim() && !selectedImage) || !selectedModel) return;
    
    console.log('[ChatInterface][handleSendMessage] selectedIndex:', selectedIndex);
    
    if (typeof onSendMessage === 'function') {
      // 创建搜索参数对象
      const searchParams = {
        similarityThreshold: similarityThreshold,
        topK: topK
      };
      
      // Pass the necessary parameters to onSendMessage (which is handleSearchAndGenerate)
      // This will first search the index and then generate text based on the search results
      // If no index is selected, it will generate text without search context
      onSendMessage(selectedIndex || null, inputMessage, selectedModel, selectedProvider, selectedImage, searchParams);
    } else {
      console.error("CRITICAL ERROR: onSendMessage prop in ChatInterface is not a function!", {
        propType: typeof onSendMessage,
        propValue: onSendMessage
      });
      // Optionally, display an error to the user here
    }
    
    setInputMessage('');
    clearSelectedImage(); // Clear image after sending
    // 重置高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 添加存储信息功能
  const [showStorageInfo, setShowStorageInfo] = useState(false);
  
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
        <div className="flex flex-col">
          <label className="text-xs text-gray-500 mb-1">{t('selectIndex')}</label>
          <select
            className="min-w-[180px] px-2 py-1 border border-gray-300 rounded-md"
            value={selectedIndex}
            onChange={e => setSelectedIndex(e.target.value)}
            disabled={configLoading || loading}
          >
            <option value="">-- {t('selectIndex')} --</option>
            {Array.isArray(indices) && Array.isArray(documents) && indices.map((idx) => {
              if (typeof idx === 'object' && idx !== null) {
                // Find the associated document to get the filename
                const doc = documents.find(d => d.id === idx.document_id);
                const displayName = doc ? doc.filename : idx.document_id;
                // Get the index type name from config (like "FAISS" instead of "faiss")
                const indexTypeName = config?.vector_databases?.[idx.vector_db]?.name || idx.vector_db;
                
                return (
                  <option key={idx.index_id} value={idx.index_id}>
                    {displayName} ({t('indexType')}: {indexTypeName}, ID: {idx.index_id})
                  </option>
                );
              } else {
                const idValue = String(idx);
                return (
                  <option key={idValue} value={idValue}>
                    {idValue}
                  </option>
                );
              }
            })}
          </select>
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
            {config && config.model_groups && Object.keys(config.model_groups).map(provider => (
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
            {config && config.model_groups && config.model_groups[selectedProvider] && config.model_groups[selectedProvider].map(model => (
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
      {/* 聊天消息区 */}
      <div className="flex-1 overflow-y-auto px-0 py-4 w-full" style={{background:'#f7f7fa'}}>
        {Array.isArray(chatHistory) && chatHistory.map((message, index) => (
          <div key={message.id || index} className="w-full mb-2">
            {/* 新增：显示 sender 和时间戳 */}
            <div className="flex items-center text-xs text-gray-500 mb-1 px-5">
              <span className="font-semibold">
                {message.sender === 'user' ? t('user') : (message.model || t('assistant'))}
              </span>
              <span className="mx-2">·</span>
              <span>{formatTimestamp(message.timestamp)}</span>
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
              {message.text}
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
      </div>
      {/* 输入栏固定在底部 */}
      <div className="w-full bg-white border-t p-2 sticky bottom-0 left-0 z-10" style={{boxShadow:'0 -2px 8px rgba(0,0,0,0.03)'}}>
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
            <span role="img" aria-label="attach">📎</span>
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
          />
          <button
            onClick={handleSendMessage}
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

export default ChatInterface;

