import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { loadConfig } from '../../utils/configLoader';
import { getLogger } from '../../utils/logger';
import EmbeddingForm from './EmbeddingForm';
import EmbeddingTable from './EmbeddingTable';

const logger = getLogger('EmbeddingFileModule');

function EmbeddingFileModule({ documents, chunks = [], embeddings = [], loading, error, onCreateEmbeddings, onEmbeddingDelete, globalSelectedDocument, onLoadEmbeddings }) {
  const [selectedDocument, setSelectedDocument] = useState('');
  const [provider, setProvider] = useState('');
  const [model, setModel] = useState('');
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [filteredEmbeddings, setFilteredEmbeddings] = useState([]);
  const [chunkedDocuments, setChunkedDocuments] = useState([]);

  // Filter documents to show only those that have been parsed (required for embedding)
  useEffect(() => {
    if (!Array.isArray(chunks) || !Array.isArray(documents)) {
      setChunkedDocuments([]);
      return;
    }

    // Extract unique document IDs from chunks
    const chunkedDocumentIds = [...new Set(chunks.map(chunk => chunk.document_id))];
    
    // Filter the documents array to include only documents that have been chunked
    // Since we don't reliably have access to parsed_at timestamp in the frontend,
    // we'll just filter on chunked documents and let the backend handle validation
    // during the actual embedding creation process
    const filteredDocuments = documents.filter(doc => 
      chunkedDocumentIds.includes(doc.id) // Ensure document has chunks
    );
    
    logger.debug(`Filtered ${filteredDocuments.length} parsed documents out of ${documents.length} total documents`);
    setChunkedDocuments(filteredDocuments);
    
    // If the currently selected document is not in the filtered list, reset selection
    if (selectedDocument && !filteredDocuments.some(doc => doc.id === selectedDocument)) {
      setSelectedDocument('');
    }
  }, [chunks, documents, selectedDocument]);

  // 加载配置 - 使用缓存版本
  useEffect(() => {
    const fetchConfig = async () => {
      setConfigLoading(true);
      try {
        // 使用 loadConfig() 获取缓存的配置
        const configData = await loadConfig();
        setConfig(configData);
        
        // 设置默认值 - 使用 embedding_models
        if (configData?.embedding_models) {
          const availableProviders = Object.keys(configData.embedding_models);
          if (availableProviders.length > 0) {
            const defaultProvider = availableProviders[0];
            setProvider(defaultProvider);
            if (configData.embedding_models[defaultProvider]?.length > 0) {
              setModel(configData.embedding_models[defaultProvider][0].id);
            }
          }
        }
      } catch (err) {
        logger.error("Failed to load config:", err);
      } finally {
        setConfigLoading(false);
      }
    };
    
    fetchConfig();
  }, []);

  // Sync with global selected document if provided
  useEffect(() => {
    if (globalSelectedDocument?.id) {
      setSelectedDocument(globalSelectedDocument.id);
    }
  }, [globalSelectedDocument]);

  // Reload embeddings when document selection changes
  const isInitialMount = useRef(true);
  const lastSelectedDocument = useRef('');
  
  useEffect(() => {
    if (isInitialMount.current) {
      // Skip the first execution of this effect
      isInitialMount.current = false;
      lastSelectedDocument.current = selectedDocument;
      return;
    }
    
    // Only reload if the selected document has actually changed
    // This prevents the deadloop when empty embeddings are returned
    if (selectedDocument && 
        selectedDocument !== lastSelectedDocument.current && 
        onLoadEmbeddings) {
      // Update last selected document
      lastSelectedDocument.current = selectedDocument;
      
      // Reload embeddings when a document is selected to ensure we have the latest data
      logger.debug(`Loading embeddings for document ${selectedDocument}`);
      onLoadEmbeddings();
    }
  }, [selectedDocument, onLoadEmbeddings]);

  // Filter embeddings when selectedDocument or embeddings change
  useEffect(() => {
    try {
      // Safety check for embeddings array
      if (!Array.isArray(embeddings)) {
        logger.warn('Embeddings data is not an array');
        setFilteredEmbeddings([]);
        return;
      }
      
      if (embeddings.length > 0) {
        if (selectedDocument) {
          // Make sure we only filter on valid document_id and use proper type checking
          const filtered = embeddings.filter(embed => 
            embed && 
            typeof embed === 'object' && 
            embed.document_id === selectedDocument
          );
          setFilteredEmbeddings(filtered);
          logger.debug(`Filtered ${filtered.length} embeddings for document ID ${selectedDocument}`);
        } else {
          setFilteredEmbeddings(embeddings);
          logger.debug(`Showing all ${embeddings.length} embeddings - no document selected`);
        }
      } else {
        setFilteredEmbeddings([]);
        logger.debug('No embeddings available to filter (empty array)');
      }
    } catch (error) {
      logger.error('Error filtering embeddings:', error);
      setFilteredEmbeddings([]);
    }
  }, [selectedDocument, embeddings]);

  // Handle provider change
  const handleProviderChange = (e) => {
    const newProvider = e.target.value;
    setProvider(newProvider);
    
    // When provider changes, select its first embedding model
    if (config?.embedding_models?.[newProvider]?.length > 0) {
      setModel(config.embedding_models[newProvider][0].id);
    } else {
      setModel(''); // Reset model if provider has no models
    }
  };

  // Handle document selection change
  const handleDocumentChange = (e) => {
    setSelectedDocument(e.target.value);
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedDocument || !provider || !model) return;
    
    try {
      await onCreateEmbeddings(selectedDocument, provider, model);
    } catch (err) {
      logger.error("Embedding failed in module:", err);
    }
  };
  
  // Handle model change
  const handleModelChange = (e) => {
    setModel(e.target.value);
  };
  
  // Clear document filter
  const handleClearFilter = () => {
    setSelectedDocument('');
  };

  return (
    <div className="space-y-6">
      <EmbeddingForm
        chunkedDocuments={chunkedDocuments}
        selectedDocument={selectedDocument}
        onDocumentChange={handleDocumentChange}
        provider={provider}
        onProviderChange={handleProviderChange}
        model={model}
        onModelChange={handleModelChange}
        configLoading={configLoading}
        config={config}
        loading={loading}
        onSubmit={handleSubmit}
      />
      
      <EmbeddingTable
        filteredEmbeddings={filteredEmbeddings}
        documents={documents}
        selectedDocument={selectedDocument}
        onDocumentChange={handleDocumentChange}
        onClearFilter={handleClearFilter}
        loading={loading}
        onEmbeddingDelete={onEmbeddingDelete}
      />
    </div>
  );
}

EmbeddingFileModule.propTypes = {
  documents: PropTypes.array,
  chunks: PropTypes.array,
  embeddings: PropTypes.array,
  loading: PropTypes.bool,
  error: PropTypes.string,
  onCreateEmbeddings: PropTypes.func.isRequired,
  onEmbeddingDelete: PropTypes.func,
  globalSelectedDocument: PropTypes.object,
  onLoadEmbeddings: PropTypes.func
};

EmbeddingFileModule.defaultProps = {
  documents: [],
  chunks: [],
  embeddings: [],
  loading: false,
  error: null
};

export default EmbeddingFileModule;

