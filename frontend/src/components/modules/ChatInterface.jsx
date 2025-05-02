import React, { useState, useEffect, useRef } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { loadConfig } from '../../utils/configLoader';
import ReactMarkdown from 'react-markdown';
import { Paperclip, X } from 'lucide-react'; // Import icons

function ChatInterface({ 
  indices, 
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
  const chatEndRef = useRef(null);
  const imageInputRef = useRef(null); // Ref for hidden file input

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
    };
    
    fetchConfig();
  }, []);

  // Scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

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
    if ((!inputMessage.trim() && !selectedImage) || !selectedIndex || !selectedModel) return;
    
    // Pass image file along with other data
    onSendMessage(inputMessage, selectedIndex, selectedProvider, selectedModel, selectedImage);
    setInputMessage('');
    clearSelectedImage(); // Clear image after sending
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-white">
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
            {indices && indices.map(idx => {
              if (typeof idx === 'object' && idx !== null) {
                return (
                  <option key={idx.id || idx.index_id || JSON.stringify(idx)} value={idx.id || idx.index_id || JSON.stringify(idx)}>
                    {idx.name || idx.index_name || idx.id || idx.index_id || '[Unnamed Index]'}
                  </option>
                );
              } else {
                return (
                  <option key={idx} value={idx}>{String(idx)}</option>
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
      </div>
      {/* 聊天消息区 */}
      <div className="flex-1 overflow-y-auto px-0 py-4 w-full" style={{background:'#f7f7fa'}}>
        {Array.isArray(chatHistory) && chatHistory.map((message, index) => (
          <div key={message.id || index} className="w-full mb-2">
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
            disabled={!selectedIndex || loading || configLoading}
          >
            <span role="img" aria-label="attach">📎</span>
          </button>
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={selectedIndex ? t('chatPlaceholder') : t('selectIndexFirst')}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 resize-none"
            rows={selectedImage ? 2 : 4}
            style={{minHeight:'48px', maxHeight:'120px'}}
            disabled={!selectedIndex || loading || configLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={(!inputMessage.trim() && !selectedImage) || !selectedIndex || !selectedModel || loading || configLoading}
            className={`px-4 py-2 rounded-md text-white self-stretch flex items-center justify-center ${
              (!inputMessage.trim() && !selectedImage) || !selectedIndex || !selectedModel || loading || configLoading
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

