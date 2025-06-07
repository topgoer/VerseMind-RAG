import React from 'react';
import PropTypes from 'prop-types';
import { useLanguage } from '../../contexts/LanguageContext';

function EmbeddingForm({ 
  chunkedDocuments, 
  selectedDocument, 
  onDocumentChange, 
  provider, 
  onProviderChange, 
  model, 
  onModelChange,
  configLoading, 
  config, 
  loading, 
  onSubmit 
}) {
  const { t } = useLanguage();
  // Get provider display name
  const getProviderDisplayName = (providerId) => {
    switch(providerId) {
      case 'ollama': return 'Ollama (本地)';
      case 'openai': return 'OpenAI';
      case 'deepseek': return 'DeepSeek';
      default: return providerId;
    }
  };
  
  // Render provider options based on configuration
  const renderProviderOptions = () => {
    if (configLoading) {
      return <option>{t('loadingConfig')}...</option>;
    }      if (config?.embedding_models) {
      return Object.keys(config?.embedding_models).map((providerId) => (
        <option key={providerId} value={providerId}>
          {getProviderDisplayName(providerId)}
        </option>
      ));
    }
    
    return <option value="">{t('noProvidersConfigured')}</option>;
  };
  
  // Render model options based on selected provider
  const renderModelOptions = () => {
    if (configLoading) {
      return <option>{t('loadingConfig')}...</option>;
    }
    
    if (config?.embedding_models?.[provider]?.length > 0) {
      return config.embedding_models[provider].map((modelInfo) => (
        <option key={modelInfo.id} value={modelInfo.id}>
          {modelInfo.name} ({modelInfo.dimensions} {t('dimensions')})
        </option>
      ));
    }
    
    return <option value="">{provider ? t('noModelsForProvider') : t('selectProviderFirst')}</option>;
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h2 className="text-xl font-semibold mb-4">{t('vectorEmbedding')}</h2>
      <p className="text-gray-600 mb-6">{t('embeddingDesc')}</p>      {chunkedDocuments.length === 0 && (
        <div className="p-4 mb-4 text-sm text-amber-700 bg-amber-100 rounded-lg" role="alert">
          <span className="font-medium">{t('info') || 'Info'}:</span> {t('noChunkedDocumentsAlert') || 'Document processing workflow: 1) Load documents 2) Chunk documents 3) Parse documents (this happens automatically) 4) Create embeddings. You need to complete the document chunking step first.'}
        </div>
      )}
      
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('selectDocument')}
          </label>
          <select
            value={selectedDocument}
            onChange={onDocumentChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
            required
            disabled={chunkedDocuments.length === 0}
          >
            <option value="">{chunkedDocuments.length === 0 ? t('noParsedDocuments') || 'No parsed documents available. Please parse your documents first.' : t('selectDocument')}</option>
            {chunkedDocuments.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename} {doc.title ? `(${doc.title})` : ''}
              </option>
            ))}
          </select>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('embeddingProvider')}
            </label>            <select
              value={provider}
              onChange={onProviderChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              disabled={configLoading}
            >
              {renderProviderOptions()}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('embeddingModel')}
            </label>            <select
              value={model}
              onChange={onModelChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
              disabled={configLoading || !provider}
            >
              {renderModelOptions()}
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
  );
}

EmbeddingForm.propTypes = {
  chunkedDocuments: PropTypes.array.isRequired,
  selectedDocument: PropTypes.string.isRequired,
  onDocumentChange: PropTypes.func.isRequired,
  provider: PropTypes.string.isRequired,
  onProviderChange: PropTypes.func.isRequired,
  model: PropTypes.string.isRequired,
  onModelChange: PropTypes.func.isRequired,
  configLoading: PropTypes.bool.isRequired,
  config: PropTypes.object,
  loading: PropTypes.bool.isRequired,
  onSubmit: PropTypes.func.isRequired
};

export default EmbeddingForm;
