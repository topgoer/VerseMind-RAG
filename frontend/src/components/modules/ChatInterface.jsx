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
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Top config area */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('selectIndex')}
            </label>
            <select
              value={selectedIndex}
              onChange={(e) => setSelectedIndex(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 text-sm"
              required
              disabled={indices.length === 0}
            >
              <option value="">{indices.length === 0 ? t('noIndicesAvailable') : t('selectIndex')}</option>
              {Array.isArray(indices) && indices.map((idx) => (
                <option key={idx.index_id} value={idx.index_id}>
                  {idx.index_name || idx.index_id} ({config?.vector_databases?.[idx.vector_db]?.name || idx.vector_db})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('providerLabel')}
            </label>
            <select
              value={selectedProvider}
              onChange={handleProviderChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 text-sm"
              disabled={configLoading}
            >
              {configLoading ? (
                <option>{t('loadingConfig')}...</option>
              ) : config && config.model_groups ? (
                Object.keys(config.model_groups).map((providerId) => (
                  <option key={providerId} value={providerId}>
                    {providerId}
                  </option>
                ))
              ) : (
                <option value="">{t('noProvidersConfigured')}</option>
              )}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('modelLabel')}
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 text-sm"
              disabled={configLoading || !selectedProvider}
            >
              {configLoading ? (
                <option>{t('loadingConfig')}...</option>
              ) : config && config.model_groups && config.model_groups[selectedProvider] && config.model_groups[selectedProvider].length > 0 ? (
                config.model_groups[selectedProvider].map((modelInfo) => (
                  <option key={modelInfo.id} value={modelInfo.id}>
                    {modelInfo.name}
                  </option>
                ))
              ) : (
                <option value="">{selectedProvider ? t('noModelsForProvider') : t('selectProviderFirst')}</option>
              )}
            </select>
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {Array.isArray(chatHistory) && chatHistory.map((message, index) => (
          <div key={message.id || index} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-lg lg:max-w-xl px-4 py-2 rounded-lg shadow-sm ${message.sender === 'user' ? 'bg-purple-100 text-purple-900' : 'bg-gray-100 text-gray-900'}`}>
              {/* Display image if present and valid URL in user message */}
              {message.sender === 'user' && message.imageUrl && typeof message.imageUrl === 'string' && (message.imageUrl.startsWith('blob:') || message.imageUrl.startsWith('data:')) && (
                <img 
                  src={message.imageUrl} 
                  alt={t('userUploadAlt') || 'User upload'} // Add alt text translation
                  className="max-w-xs max-h-48 rounded mb-2"
                  onError={(e) => { 
                    console.error('Error loading image URL:', message.imageUrl, e); 
                    // Optionally hide the broken image element or show a placeholder
                    e.target.style.display = 'none'; 
                  }}
                />
              )}
              {message.sender === 'system' && message.taskInfo && (
                <div className="mb-2 p-2 bg-blue-50 border border-blue-200 rounded">
                  <p className="text-sm font-medium text-blue-700">{t('taskDetected')}: {t(message.taskInfo.type)}</p>
                  <p className="text-xs text-blue-600">{t('taskParams')}: {JSON.stringify(message.taskInfo.params)}</p>
                </div>
              )}
              {/* Only render text content */}
              {message.text && (
                message.isMarkdown ? (
                  <ReactMarkdown className="markdown-content">
                    {message.text}
                  </ReactMarkdown>
                ) : (
                  <pre style={{whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0, padding: 0, background: 'none', border: 0, fontFamily: 'inherit', fontSize: '1rem', color: 'inherit'}}>
                    {message.text}
                  </pre>
                )
              )}
              {message.sender === 'system' && message.sources && Array.isArray(message.sources) && message.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <h4 className="text-xs font-semibold text-gray-600 mb-1">{t('sources')}:</h4>
                  <ul className="space-y-1">
                    {message.sources.map((source, i) => (
                      <li key={i} className="text-xs text-gray-500 bg-gray-50 p-1 rounded">
                        {t('page')} {source.metadata?.page || 'N/A'} ({t('similarity')}: {source.similarity?.toFixed(3) || 'N/A'})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="text-xs text-gray-500 mt-1 text-right">
                {message.timestamp} {message.sender === 'system' && `(${message.model})`}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="max-w-lg lg:max-w-xl px-4 py-2 rounded-lg shadow-sm bg-gray-100 text-gray-900">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></div>
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse delay-75"></div>
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse delay-150"></div>
                <span className="text-sm">{t('processing')}...</span>
              </div>
            </div>
          </div>
        )}
        {currentTask && (
          <div className="flex justify-start">
            <div className="max-w-lg lg:max-w-xl px-4 py-2 rounded-lg shadow-sm bg-blue-100 text-blue-900">
              <p className="text-sm font-medium">{t('executingTask')}: {t(currentTask.type)}</p>
              <p className="text-xs">{taskProgress}</p>
            </div>
          </div>
        )}
        {error && (
          <div className="flex justify-start">
            <div className="max-w-lg lg:max-w-xl px-4 py-2 rounded-lg shadow-sm bg-red-100 text-red-900">
              <p className="text-sm font-medium">{t('error')}</p>
              <p className="text-xs">{error}</p>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        {/* Image preview */}
        {selectedImage && (
          <div className="mb-2 flex items-center space-x-2">
            <img 
              src={URL.createObjectURL(selectedImage)} 
              alt="Selected preview" 
              className="max-h-16 rounded border border-gray-300"
            />
            <span className="text-sm text-gray-600">{selectedImage.name}</span>
            <button 
              onClick={clearSelectedImage} 
              className="text-gray-500 hover:text-red-600"
              title={t('removeImage')}
            >
              <X size={16} />
            </button>
          </div>
        )}
        <div className="flex items-end space-x-2">
          {/* Image upload button */}
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
            <Paperclip size={20} /> Img {/* Temporary text label */}
          </button>
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={selectedIndex ? t('chatPlaceholder') : t('selectIndexFirst')}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 resize-none"
            rows={selectedImage ? 1 : 2} // Adjust rows based on image presence
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

