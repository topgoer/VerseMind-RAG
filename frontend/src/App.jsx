import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import { useLanguage } from './contexts/LanguageContext';
import { loadConfig } from './utils/configLoader';

// 从文档ID中提取文件名
function extractFilenameFromDocId(documentId) {
  if (!documentId || typeof documentId !== 'string') return null;
  
  try {
    // 尝试解析格式如 "article_name_20250511_141012_b00ecba1" 的文档ID
    const parts = documentId.split('_');
    if (parts.length >= 3) {
      // 寻找日期部分（通常是数字部分开始的位置）
      let datePartIndex = -1;
      for (let i = 0; i < parts.length; i++) {
        if (/^\d{8}$/.test(parts[i])) {
          datePartIndex = i;
          break;
        }
      }
      
      if (datePartIndex > 0) {
        // 提取日期前的所有部分作为文件名
        return parts.slice(0, datePartIndex).join('_');
      }
    }
  } catch (e) {
    console.error("Error extracting filename from document ID:", e);
  }
  return null;
}

function App() {
  const { t, language } = useLanguage();
  const [activeModule, setActiveModule] = useState('chat');
  
  // Expose setActiveModule to window object for cross-component navigation
  useEffect(() => {
    window.setActiveModule = (moduleName) => {
      console.log(`[App] Setting active module to: ${moduleName}`);
      setActiveModule(moduleName);
    };
    
    // Cleanup
    return () => {
      window.setActiveModule = undefined;
    };
  }, []);

  const [documents, setDocuments] = useState([]);
  const [chunks, setChunks] = useState([]);
  const [chunksLoading, setChunksLoading] = useState(false); // New state for chunks loading
  const [selectedDocumentId, setSelectedDocumentId] = useState(null); // Added for demonstration
  // Removing unused state variables for parsed document content and loading
  const [embeddings, setEmbeddings] = useState([]);
  const [indices, setIndices] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [currentSearchResult, setCurrentSearchResult] = useState(null); // Store current search result with document info
  const [generatedText, setGeneratedText] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chatHistory, setChatHistory] = useState([
    { 
      sender: 'system', 
      text: 'Welcome to VerseMind-RAG! Select an index and ask questions about your documents. You can also request tasks like "extract page 5 and generate a summary".',
      timestamp: new Date().toLocaleString(), 
      model: 'System',
      id: 'system-welcome-en'
    }
  ]);
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [notification, setNotification] = useState({ type: '', message: '' });
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [currentTask, setCurrentTask] = useState(null);
  const [taskProgress, setTaskProgress] = useState('');
  // Removed unused notificationRef

  useEffect(() => {
    loadConfig().then(cfg => {
      setConfig(cfg);
      setConfigLoading(false);
    });
  }, []);

  // Define fetchChunks using useCallback
  const fetchChunks = useCallback(async (documentId) => {
    if (!documentId) {
      setChunks([]); // Clear chunks if no documentId
      return;
    }
    setChunksLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      // Use the correct API endpoint path - /api/chunks/{document_id}
      const response = await fetch(`${apiBase}/api/chunks/${documentId}`);
      
      // Handle non-200 responses
      if (!response.ok) {
        let errorDetail = '';
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || JSON.stringify(errorData);
        } catch (e) {
          console.warn('Failed to parse error response as JSON:', e.message);
          
          try {
            const text = await response.text();
            errorDetail = text || `Server error: ${response.status} (empty response)`;
            // Truncate long error messages
            if (errorDetail.length > 200) {
              errorDetail = errorDetail.substring(0, 200) + '... [content truncated]';
            }
          } catch (textErr) {
            console.error('Failed to read error response as text:', textErr.message);
            errorDetail = `Server error: ${response.status} (cannot read response text)`;
          }
        }
        console.error('Failed to fetch chunks:', response.status, errorDetail);
        throw new Error(`Failed to fetch chunks for document ${documentId}. Status: ${response.status}`);
      }
      
      // Try to parse JSON response
      const data = await response.json();
      console.log(`Fetched ${Array.isArray(data) ? data.length : 0} chunks for document ${documentId}`);
      setChunks(Array.isArray(data) ? data : []); // Ensure data is an array
    } catch (err) {
      console.error('Error fetching chunks:', err);
      setError(err.message || 'An unknown error occurred while fetching chunks.');
      setChunks([]); // Clear chunks on error
    } finally {
      setChunksLoading(false);
    }
  }, [setChunks, setChunksLoading, setError]); // Dependencies for useCallback

  // Define fetchParsed using useCallback
  const fetchParsed = useCallback(async (documentId) => {
    if (!documentId) {
      return null; // Return null if no documentId
    }
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      // Use the correct API endpoint path with proper API base URL
      const response = await fetch(`${apiBase}/api/parse/${documentId}`);
      
      // Handle non-200 responses
      if (!response.ok) {
        let errorDetail = '';
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || JSON.stringify(errorData);
        } catch (e) {
          console.warn('Failed to parse error response as JSON:', e.message);
          try {
            const text = await response.text();
            errorDetail = text || `Server error: ${response.status} (empty response)`;
            // Truncate long error messages
            if (errorDetail.length > 200) {
              errorDetail = errorDetail.substring(0, 200) + '... [content truncated]';
            }
          } catch (textErr) {
            console.error('Failed to read error response as text:', textErr.message);
            errorDetail = `Server error: ${response.status} (cannot read response text)`;
          }
        }
        console.error('Failed to fetch parsed document content:', response.status, errorDetail);
        throw new Error(`Failed to fetch parsed document content for document ${documentId}. Status: ${response.status}`);
      }
      
      // Try to parse JSON response
      const data = await response.json();
      console.log(`Fetched parsed content for document ${documentId}`);
      return data; // Return the data directly
    } catch (err) {
      console.error('Error fetching parsed document content:', err);
      setError(err.message || 'An unknown error occurred while fetching parsed document content.');
      return null; // Return null on error
    } finally {
      setLoading(false);
    }
  }, [setError, setLoading]); // Dependencies for useCallback

  // Define fetchEmbeddings using useCallback
  const fetchEmbeddings = useCallback(async (documentId) => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      // Use the correct endpoint with query parameter instead of path parameter
      const url = documentId 
        ? `${apiBase}/api/embeddings/list?document_id=${encodeURIComponent(documentId)}`
        : `${apiBase}/api/embeddings/list`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        let errorText;
        try {
          const errorData = await response.json();
          errorText = JSON.stringify(errorData);
        } catch (e) {
          // Handle the exception more explicitly
          try {
            errorText = await response.text();
          } catch (textError) {
            errorText = `Failed to read error response: ${textError.message}`;
            console.error('Failed to parse error response as text:', textError);
          }
        }
        console.error('Failed to fetch embeddings:', response.status, errorText);
        throw new Error(`Failed to fetch embeddings${documentId ? ` for document ${documentId}` : ''}. Status: ${response.status}`);
      }
      
      const data = await response.json();
      setEmbeddings(Array.isArray(data) ? data : []); // Ensure data is an array
    } catch (err) {
      console.error('Error fetching embeddings:', err);
      setError(err.message || 'An unknown error occurred while fetching embeddings.');
      setEmbeddings([]); // Clear embeddings on error
    } finally {
      setLoading(false);
    }
  }, [setEmbeddings, setLoading, setError]); // Dependencies for useCallback

  // Define fetchIndices using useCallback
  const fetchIndices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/indices/list`);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to fetch indices:', response.status, errorText);
        throw new Error(`Failed to fetch indices. Status: ${response.status}`);
      }
      const data = await response.json();
      setIndices(Array.isArray(data) ? data : []); // Ensure data is an array
    } catch (err) {
      console.error('Error fetching indices:', err);
      setError(err.message || 'An unknown error occurred while fetching indices.');
      setIndices([]); // Clear indices on error
    } finally {
      setLoading(false);
    }
  }, [setIndices, setLoading, setError]); // Dependencies for useCallback

  // useEffect to call fetchChunks when selectedDocumentId changes
  useEffect(() => {
    if (selectedDocumentId) {
      fetchChunks(selectedDocumentId);
    } else {
      setChunks([]); // Clear chunks if no document is selected
    }
  }, [selectedDocumentId, fetchChunks]);

  useEffect(() => {
    setChatHistory(prevMessages => {
      const welcomeMessage = {
        id: `system-welcome-${language}`,
        sender: 'system',
        text: t('welcomeMessage'),
        timestamp: new Date().toLocaleString(),
        model: 'System'
      };
      
      if (prevMessages.length > 0 && prevMessages[0].sender === 'system' && 
          (prevMessages[0].id?.startsWith('system-welcome-') || prevMessages[0].text.includes('Welcome to VerseMind-RAG'))) {
        return [welcomeMessage, ...prevMessages.slice(1)];
      }
      
      return [welcomeMessage, ...prevMessages];
    });
  }, [language, t]);

  const triggerNotification = (message, type = 'success') => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification({ type: '', message: '' });
    }, 3000);
  };

  const fetchDocuments = useCallback(async () => {
    console.log('[App.jsx fetchDocuments] Starting to fetch documents...');
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/documents/list`);

      if (!response.ok) {
        let errorDetail = `Failed to fetch documents. Status: ${response.status}`;
        try {
          const errorData = await response.json(); 
          errorDetail = errorData.detail || JSON.stringify(errorData);
        } catch (e) {
          console.warn('Failed to parse error response as JSON:', e.message);
          try {
            const text = await response.text();
            errorDetail = text || `Server error: ${response.status} (empty response)`;
          } catch (textErr) {
            console.error('Failed to read error response as text:', textErr.message);
            errorDetail = `Server error: ${response.status} (cannot read response text)`;
          }
        }
        console.error('[App.jsx fetchDocuments] Error response from API. Status:', response.status, 'Details:', errorDetail);
        throw new Error(errorDetail);
      }

      const data = await response.json();
      console.log('[App.jsx fetchDocuments] Received data from API /api/documents/list:', data);

      const sanitizedDocs = Array.isArray(data) ? data.map(doc => ({
        id: String(doc.id ?? doc.filename ?? `generated_${Math.random().toString(36).substr(2, 9)}`),
        filename: String(doc.filename ?? t('unknownFilename')),
        file_type: String(doc.file_type ?? 'unknown').toLowerCase(),
        size: Number(doc.size ?? 0),
        upload_time: String(doc.upload_time ?? ''),
        page_count: Number(doc.page_count ?? 0),
        description: String(doc.description ?? ''),
        preview: String(doc.preview ?? ''),
        metadata: doc.metadata && typeof doc.metadata === 'object' ? doc.metadata : {},
        saved_as: String(doc.saved_as ?? ''),
        path: String(doc.path ?? ''),
        text: String(doc.text ?? ''),
        page_map: Array.isArray(doc.page_map) ? doc.page_map : [],
      })) : [];

      if (!Array.isArray(data)) {
        console.warn('[App.jsx fetchDocuments] API /api/documents/list did not return an array. Received:', data, 'Setting documents to empty array.');
        setError(t('error.fetchDocsUnexpectedFormat') || 'Error: Document list from server was not in the expected format.');
        setDocuments([]);
      } else {
        console.log('[App.jsx fetchDocuments] Setting sanitized documents. Count:', sanitizedDocs.length);
        setDocuments(sanitizedDocs);
        setError(null); 
      }

    } catch (err) {
      console.error('[App.jsx fetchDocuments] Error caught during fetchDocuments:', err);
      const errorMessage = err.message || t('error.fetchDocsFailed') || 'Failed to fetch documents due to an unexpected error.';
      setError(errorMessage); 
      setDocuments([]); 
      triggerNotification(errorMessage, 'error');
    } finally {
      console.log('[App.jsx fetchDocuments] Fetch documents process finished.');
      setLoading(false);
    }
  }, [setLoading, setError, setDocuments, t]);

  const handleDocumentUpload = useCallback(async (formData) => {
    setLoading(true);
    setError(null);
    triggerNotification('', ''); 

    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      });
      
      // Clone the response to be able to use both text and json parsing if needed
      const responseClone = response.clone();
      
      // First try to parse as JSON, which is the expected format
      try {
        const responseData = await response.json();
        
        if (!response.ok) {
          const detailMessage = (typeof responseData === 'object' && responseData !== null && responseData.detail) 
                                ? String(responseData.detail) 
                                : `Failed upload status: ${response.status}`;
          throw new Error(`Failed to upload document. Status: ${response.status}. Detail: ${detailMessage}`);
        }
        
        // On success, trigger notification and return the data
        console.log('[App.jsx handleDocumentUpload] Document upload successful. Status:', response.status);
        
        // Only log a truncated version of the response to avoid huge logs
        const summaryData = {
          id: responseData.id,
          filename: responseData.filename,
          size: responseData.size,
          status: 'success'
        };
        console.log('Response summary:', JSON.stringify(summaryData));
        
        triggerNotification('Document uploaded successfully!');
        await fetchDocuments(); // Refresh the document list
        return responseData;
      } catch (jsonError) {
        console.error('[App.jsx handleDocumentUpload] JSON parsing error:', jsonError.message);
        // If JSON parsing fails, try to get text content for debugging
        let errorTextContent = 'Failed to retrieve response content';
        try {
          errorTextContent = await responseClone.text();
          // Truncate long error messages to avoid flooding the console
          if (errorTextContent && errorTextContent.length > 200) {
            errorTextContent = errorTextContent.substring(0, 200) + '... [content truncated]';
          }
        } catch (textErr) {
          console.warn('[App.jsx handleDocumentUpload] Error reading response text:', textErr.message);
        }
        
        console.error(
          '[App.jsx handleDocumentUpload] Error parsing JSON response. Status:', response.status, 
          'Error:', String(jsonError), 
          'Response text preview:', errorTextContent
        );
        
        if (!response.ok) {
          throw new Error(`Server error during upload: ${response.status}. Details: [API Error]`);
        }
        throw new Error(`Error handling server response (status ${response.status}). Details: [JSON Parse Error]`);
      }
    } catch (err) {
      const originalErrorMessage = (typeof err === 'object' && err !== null && err.message) ? String(err.message) : String(err);
      console.error('[App.jsx handleDocumentUpload] Error caught during document upload:', originalErrorMessage);
      
      let displayMessage;
      try {
        displayMessage = originalErrorMessage || (typeof t === 'function' ? t('error.uploadFailed') : 'An unexpected error occurred during document upload.');
      } catch (tError) {
        displayMessage = originalErrorMessage || 'An unexpected error occurred during document upload.';
      }

      triggerNotification(displayMessage, 'error');
      setError(displayMessage);
      throw err;
    } finally {
      setLoading(false); 
    }
  }, [setLoading, setError, t, fetchDocuments]);

  const handleDocumentDelete = useCallback(async (documentId) => {
    setLoading(true);
    triggerNotification('', ''); 
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/documents/${documentId}`, {
        method: 'DELETE',
      });
      const responseData = await response.json();
      if (!response.ok) {
        throw new Error(responseData.detail || `Failed to delete document. Status: ${response.status}`);
      }
      triggerNotification(responseData.message || 'Document deleted successfully!');
      await fetchDocuments(); 
      return responseData;
    } catch (err) {
      console.error('Error deleting document in App.jsx:', err);
      triggerNotification(err.message || 'An unexpected error occurred during document deletion.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchDocuments, setLoading, t]);

  const handleSelectDocument = useCallback((docId) => {
    if (!docId) {
      setSelectedDocument(null);
      setSelectedDocumentId(null);
      return;
    }
    const doc = documents.find(d => d.id === docId);
    setSelectedDocument(doc || null);
    setSelectedDocumentId(docId);
  }, [documents]);

  const handleParseDocument = useCallback(async (documentId, strategy, extractTables = false, extractImages = false) => {
    setLoading(true);
    triggerNotification('', ''); 

    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/parse/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          strategy: strategy,
          extract_tables: extractTables,
          extract_images: extractImages
        }),
      });

      const responseData = await response.json();

      if (!response.ok) {
        throw new Error(responseData.detail || `Failed to parse document. Status: ${response.status}`);
      }

      triggerNotification(responseData.message || 'Document parsed successfully!');
      return responseData;

    } catch (err) {
      console.error('Error parsing document in App.jsx:', err);
      triggerNotification(err.message || 'An unexpected error occurred during parsing.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [t]);

  const handleChunkDocument = useCallback(async (documentId, strategy, chunkSize, overlap) => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      // Format the request body exactly as expected by the backend API
      const response = await fetch(`${apiBase}/api/chunks/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: documentId,
          strategy: strategy,
          chunk_size: parseInt(chunkSize, 10) || 1000,
          overlap: parseInt(overlap, 10) || 200
        }),
      });
      
      // Check for error status code before parsing response
      if (!response.ok) {
        const errorResponse = await response.json().catch(() => ({ 
          detail: `Error ${response.status}: Failed to parse error response` 
        }));
        const errorDetail = errorResponse.detail || `Failed to chunk document. Status: ${response.status}`;
        throw new Error(errorDetail);
      }
      
      const data = await response.json();
      console.log('Document successfully chunked:', data);
      triggerNotification('Document chunked successfully!');
      await fetchChunks(documentId); // Refresh the chunks
      return data;
    } catch (err) {
      console.error('Error chunking document:', err);
      setError(err.message || 'An unknown error occurred while chunking the document.');
      triggerNotification(err.message || 'Failed to chunk document.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchChunks]);

  const handleChunkDelete = useCallback(async (chunkId) => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      // Use the correct API endpoint path - /api/chunks/{chunk_id} (plural)
      const response = await fetch(`${apiBase}/api/chunks/${chunkId}`, {
        method: 'DELETE',
      });
      
      // Check for error status code before parsing response
      if (!response.ok) {
        const errorResponse = await response.json().catch(() => ({ 
          detail: `Error ${response.status}: Failed to parse error response` 
        }));
        const errorDetail = errorResponse.detail || `Failed to delete chunk. Status: ${response.status}`;
        throw new Error(errorDetail);
      }
      
      const data = await response.json();
      console.log('Chunk successfully deleted:', data);
      triggerNotification('Chunk deleted successfully!');
      if (selectedDocumentId) {
        await fetchChunks(selectedDocumentId); // Refresh the chunks list
      }
      return data;
    } catch (err) {
      console.error('Error deleting chunk:', err);
      setError(err.message || 'An unknown error occurred while deleting the chunk.');
      triggerNotification(err.message || 'Failed to delete chunk.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchChunks, selectedDocumentId]);

  const handleCreateEmbeddings = useCallback(async (documentId, provider, model) => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/embeddings/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: documentId,
          provider: provider,
          model: model
        }),
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `Failed to create embeddings. Status: ${response.status}`);
      }
      triggerNotification('Embeddings created successfully!');
      await fetchEmbeddings(documentId); // Refresh the embeddings
      return data;
    } catch (err) {
      console.error('Error creating embeddings:', err);
      setError(err.message || 'An unknown error occurred while creating embeddings.');
      triggerNotification(err.message || 'Failed to create embeddings.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchEmbeddings]);

  const handleEmbeddingDelete = useCallback(async (embeddingId) => {
    setLoading(true);
    setError(null);
    try {
      // Ensure embedding ID is properly trimmed to avoid whitespace issues
      const trimmedId = embeddingId.trim();
      console.log(`Attempting to delete embedding with ID: ${trimmedId}`);
      
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/embeddings/${trimmedId}`, {
        method: 'DELETE',
      });
      
      // First try to parse the response as JSON
      let data;
      let errorDetail = '';
      try {
        data = await response.json();
      } catch (e) {
        // If response is not valid JSON, get text content
        errorDetail = await response.text();
        console.error('Failed to parse delete embedding response as JSON:', errorDetail);
      }
      
      if (!response.ok) {
        const detail = data?.detail || errorDetail || `Failed to delete embedding. Status: ${response.status}`;
        console.error(`Error response when deleting embedding ${trimmedId}:`, detail);
        throw new Error(detail);
      }
      
      console.log(`Successfully deleted embedding ${trimmedId}:`, data);
      triggerNotification('Embedding deleted successfully!');
      
      // Refresh the embeddings list
      await fetchEmbeddings(selectedDocumentId);
      return data;
    } catch (err) {
      console.error('Error deleting embedding:', err);
      setError(err.message || 'An unknown error occurred while deleting the embedding.');
      triggerNotification(err.message || 'Failed to delete embedding.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchEmbeddings, selectedDocumentId]);

  const handleCreateIndex = useCallback(async (documentId, vectorDb, embeddingId) => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      
      // Generate index and collection names based on document ID and embedding ID
      const collectionName = `col_${documentId.substring(0, 10)}`;
      const indexName = `idx_${embeddingId.substring(0, 8)}`;
      
      console.log(`Creating index with params: documentId=${documentId}, vectorDb=${vectorDb}, embeddingId=${embeddingId}`);
      
      const response = await fetch(`${apiBase}/api/indices/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: documentId,
          vector_db: vectorDb,
          collection_name: collectionName,
          index_name: indexName,
          embedding_id: embeddingId
        }),
      });
      
      // Check for error response before parsing JSON
      if (!response.ok) {
        let errorDetail = '';
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || JSON.stringify(errorData);
        } catch (e) {
          // Properly handle the exception when JSON parsing fails
          try {
            errorDetail = await response.text() || `Failed to parse error response: ${e.message}`;
          } catch (textError) {
            errorDetail = `Failed to read error response: ${textError.message}`;
            console.error('Error reading response text:', textError);
          }
        }
        throw new Error(errorDetail || `Failed to create index. Status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Index created successfully:', data);
      triggerNotification('Index created successfully!');
      await fetchIndices(); // Refresh the indices list
      return data;
    } catch (err) {
      console.error('Error creating index:', err);
      setError(err.message || 'An unknown error occurred while creating the index.');
      triggerNotification(err.message || 'Failed to create index.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchIndices]);

  const handleIndexDelete = useCallback(async (indexId) => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/indices/${indexId}`, {
        method: 'DELETE',
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `Failed to delete index. Status: ${response.status}`);
      }
      triggerNotification('Index deleted successfully!');
      await fetchIndices(); // Refresh the indices list
      return data;
    } catch (err) {
      console.error('Error deleting index:', err);
      setError(err.message || 'An unknown error occurred while deleting the index.');
      triggerNotification(err.message || 'Failed to delete index.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchIndices]);

  const handleSearch = useCallback(async (indexId, query, topK = 5, similarityThreshold = 0.5, minChars = 100) => {
    setLoading(true);
    setError(null);
    setSearchResults(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      console.log(`Making search request with: indexId=${indexId}, query=${query}, topK=${topK}, similarityThreshold=${similarityThreshold}, minChars=${minChars}`);
      
      const response = await fetch(`${apiBase}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          index_id: indexId,
          query: query,
          top_k: topK,
          similarity_threshold: similarityThreshold,
          min_chars: minChars
        }),
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `Failed to perform search. Status: ${response.status}`);
      }
      
      // DEBUG: Log search results to verify similarity pattern
      console.log('Search result data:', data);
      
      // Make sure all similarity scores are consistently formatted as numbers
      if (data && data.results && Array.isArray(data.results)) {
        data.results = data.results.map(result => ({
          ...result,
          similarity: typeof result.similarity === 'string' ? parseFloat(result.similarity) : result.similarity
        }));
      }
      
      // Analyze similarity scores if results are available
      if (data && data.results && Array.isArray(data.results) && data.results.length > 0) {
        console.log('--- Similarity Score Analysis ---');
        
        // Check for hardcoded pattern (0.95, 0.90, 0.85...)
        const hardcodedPattern = data.results.map((item, index) => ({
          position: index + 1,
          score: item.similarity,
          expected: 0.95 - (index * 0.05),
          difference: item.similarity - (0.95 - (index * 0.05))
        }));
        console.table(hardcodedPattern);
        
        // Check if scores follow the exact pattern of 0.95 - (i * 0.05)
        const isHardcodedPattern = hardcodedPattern.every(item => Math.abs(item.difference) < 0.0001);
        
        // Check if some results are marked as low confidence
        const hasLowConfidenceResults = data.results.some(item => 
          item.metadata && item.metadata.low_confidence === true
        );
        
        // Get real vector flag
        const hasRealVectors = data.results.some(item => 
          item.metadata && item.metadata.real_vectors === true
        );
        
        console.log(`Similarity scores match hardcoded pattern (0.95, 0.90...): ${isHardcodedPattern ? 'YES (FAKE SCORES)' : 'NO (REAL SCORES)'}`);
        console.log(`Results contain low confidence matches: ${hasLowConfidenceResults ? 'YES' : 'NO'}`);
        console.log(`Results contain real vector similarity: ${hasRealVectors ? 'YES' : 'NO'}`);
        
        // Additional statistical analysis
        const scores = data.results.map(item => item.similarity);
        const min = Math.min(...scores);
        const max = Math.max(...scores);
        const avg = scores.reduce((sum, score) => sum + score, 0) / scores.length;
        const isDescending = scores.every((score, i) => i === 0 || score <= scores[i-1]);
        
        // Calculate variance to check for randomness
        const variance = scores.reduce((sum, score) => sum + Math.pow(score - avg, 2), 0) / scores.length;
        
        console.log('--- Score Statistics ---');
        console.log(`Min: ${min.toFixed(4)}, Max: ${max.toFixed(4)}, Avg: ${avg.toFixed(4)}`);
        console.log(`Perfectly descending order: ${isDescending ? 'YES' : 'NO'}`);
        console.log(`Score variance: ${variance.toFixed(6)} (Higher variance suggests more randomness, real scores typically have higher variance)`);
        
        // Add to search results data for display
        if (data.search_info) {
          console.log('--- Search Info ---');
          console.log('Vector dimensions:', data.search_info.vector_dimensions);
          console.log('Timing:', data.search_info.timing);
          console.log('Status:', data.search_info.status);
        }
        
        // Look for signs of real vector search
        const realSearchIndicators = [
          !isHardcodedPattern,           // Not following the exact hardcoded pattern
          variance > 0.001,              // Some variance in scores
          !isDescending,                 // Not in perfect descending order
          hasRealVectors,                // Results explicitly marked as real
          data.search_info?.vector_dimensions !== undefined // Has detailed search info
        ];
        
        // Weight the indicators, with explicit real_vectors flag having more weight
        const weights = [0.2, 0.15, 0.15, 0.4, 0.1]; // weights sum to 1.0
        let weightedConfidence = 0;
        
        realSearchIndicators.forEach((indicator, idx) => {
          if (indicator) {
            weightedConfidence += weights[idx];
          }
        });
        
        // If there are no results, we can't really determine if they're real or fake
        const realSearchConfidence = data.results.length === 0 ? 0 : weightedConfidence;
        console.log(`Real vector search confidence: ${(realSearchConfidence * 100).toFixed(1)}%`);
        
        // Mark low confidence results
        if (data.results.some(r => r.metadata?.low_confidence)) {
          console.log("⚠️ Results include low confidence matches below the original threshold");
        }
      } else {
        console.log('No search results to analyze');
      }
      
      // Process the document filename from search results here to ensure consistency
      const processDocumentName = () => {
        // Try immediate document_filename if available
        if (data.document_filename) {
          return data.document_filename;
        }
        
        // Try to extract from document_id
        if (data.document_id) {
          const docId = data.document_id;
          const timestampHashPattern = /(_\d{8}_\d{6}_[a-f0-9]+)$/;
          let cleanId = docId.replace(timestampHashPattern, '');
          
          const timestampPattern = /_\d{8}$/;
          if (timestampPattern.test(cleanId)) {
            cleanId = cleanId.replace(timestampPattern, '');
          }
          return cleanId;
        }
        
        // Try search info
        if (data.search_info?.document_filename) {
          return data.search_info.document_filename;
        }
        
        // Try to get document name from index
        if (data.index_id) {
          const currentIndex = indices.find(idx => idx.index_id === data.index_id || idx.id === data.index_id);
          if (currentIndex) {
            if (currentIndex.name) return currentIndex.name;
            if (currentIndex.documents && currentIndex.documents.length > 0) {
              return currentIndex.documents[0].filename || null;
            }
          }
          return indexId ? `Document from index ${indexId}` : null;
        }
        
        return null;
      };
      
      // Add document filename to search results if possible
      const documentName = processDocumentName();
      if (documentName) {
        data.document_filename = documentName;
      }
      
      // Update both search results and currentSearchResult state
      setSearchResults(data);
      setCurrentSearchResult(data); // Store current search result with document info
      return data;
    } catch (err) {
      console.error('Error during search:', err);
      setError(err.message || 'An unknown error occurred during search.');
      triggerNotification(err.message || 'Search failed.', 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setSearchResults]);

  const handleGenerateText = useCallback(async (searchId, userPrompt, provider, model, image = null) => {
    setLoading(true);
    setError(null);
    setGeneratedText(null); 

    // Use default values if not provided
    const actualProvider = provider || (config?.llm?.default_provider || 'openai');
    const actualModel = model || (config?.llm?.default_model || 'gpt-3.5-turbo');

    // Create request body with all required fields
    const requestBody = {
      prompt: userPrompt,
      provider: actualProvider,
      model: actualModel,
      temperature: 0.7,  // Add default temperature
      max_tokens: 1000,  // Add reasonable max tokens
      top_p: 1,          // Add default top_p
      stream: false,     // Disable streaming for now
    };

    // Only add search_id if it's not null/undefined
    if (searchId) {
      requestBody.search_id = searchId;
    }

    if (image) {
      const reader = new FileReader();
      reader.readAsDataURL(image);
      await new Promise((resolve, reject) => {
        reader.onload = () => {
          requestBody.image_data = reader.result.split(',')[1]; 
          resolve();
        };
        reader.onerror = error => reject(error);
      });
    }
    
    const userMessageId = `user-msg-${Date.now()}`;
    
    // Only add user message if not in chatHistory already
    // This prevents duplicate messages when called from handleSearchAndGenerate
    const existingUserMessages = chatHistory.filter(msg => 
      msg.sender === 'user' && msg.text === userPrompt && 
      // Compare within the last minute to avoid filtering out old identical messages
      (new Date().getTime() - new Date(msg.timestamp).getTime() < 60000)
    );
    
    if (existingUserMessages.length === 0) {
      setChatHistory(prev => [...prev, { 
        id: userMessageId,
        sender: 'user', 
        text: userPrompt, 
        timestamp: new Date().toLocaleString(),
        image: image ? URL.createObjectURL(image) : null 
      }]);
    }

    const thinkingMessageId = `system-thinking-${Date.now()}`;
    setChatHistory(prev => [...prev, {
      id: thinkingMessageId,
      sender: 'system',
      text: t('thinking'),
      timestamp: new Date().toLocaleString(),
      model: actualModel,
      type: 'thinking'
    }]);

    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
      const endpoint = searchId ? '/api/generate/from_search' : '/api/generate/text';
      
      console.log(`Making ${endpoint} request with:`, JSON.stringify(requestBody));
      const response = await fetch(`${apiBase}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });
      
      if (!response.ok) {
        const errorResponse = await response.json().catch(e => ({ 
          detail: `Error ${response.status}: Failed to parse error response` 
        }));
        console.error(`API error (${response.status}):`, errorResponse);
        throw new Error(errorResponse.detail || `Failed to generate text. Status: ${response.status}`);
      }

      const data = await response.json();
      setGeneratedText(data);
      triggerNotification('Text generated successfully.');

      // Include search information in the AI response if available
      let additionalInfo = '';
      if (searchId) {
        // Get the search result details if available
        const searchResultDetails = searchResults || currentSearchResult || data.search_results;
        const indexId = searchResultDetails?.index_id;
        
        // Ensure we're using the same results that are stored in the global object for consistency
        let resultsToUse = searchResultDetails?.results || [];
        
        // Check if we have a global object with potentially more accurate data
        if (typeof window !== 'undefined' && window.verseMindCurrentSearchResults && 
            window.verseMindCurrentSearchResults.search_id === searchId) {
          resultsToUse = window.verseMindCurrentSearchResults.results || resultsToUse;
          console.log("Using similarity scores from global search results object for consistency");
        }
        
        // Get similarity scores if available - use the same format as in StorageInfoPanel
        const topSimilarities = resultsToUse.slice(0, 3).map(r => r.similarity.toFixed(4)) || [];
        const similarityInfo = topSimilarities.length > 0 
          ? `\n${t('similarity')}: ${topSimilarities.join(', ')}` 
          : '';
        
        // Get the appropriate labels based on the current language
        const usingContextLabel = t('usingDocumentContext');
        const docFilenameLabel = t('documentFilename');
        const searchIdLabel = t('searchIdLabel');
        
        // 使用更强大的文档名称提取逻辑
        const getDocumentName = () => {
          // 0. 首先尝试从全局对象获取文档名 (新增此步骤)
          try {
            if (typeof window !== 'undefined' && 
                window.verseMindCurrentSearchResults && 
                window.verseMindCurrentSearchResults.search_id === searchId &&
                window.verseMindCurrentSearchResults.document_filename) {
              return window.verseMindCurrentSearchResults.document_filename;
            }
          } catch (err) {
            console.warn("Failed to access global search results object:", err);
          }
          
          // 1. 尝试从currentSearchResult获取文档名
          if (currentSearchResult?.search_id === searchId && currentSearchResult?.document_filename) {
            return currentSearchResult.document_filename;
          }
          
          // 2. 尝试从API响应获取文档名
          if (data.search_results?.document_filename) {
            return data.search_results.document_filename;
          }
          
          // 3. 尝试从searchResultDetails获取文档名
          if (searchResultDetails?.document_filename) {
            return searchResultDetails.document_filename;
          }
          
          // 4. 尝试从文档ID提取文件名
          if (searchResultDetails?.document_id) {
            const docId = searchResultDetails.document_id;
            // 尝试移除时间戳和哈希部分
            const timestampHashPattern = /(_\d{8}_\d{6}_[a-f0-9]+)$/;
            let cleanId = docId.replace(timestampHashPattern, '');
            
            // 检查是否有其他时间戳模式需要清理
            const timestampPattern = /_\d{8}$/;
            if (timestampPattern.test(cleanId)) {
              cleanId = cleanId.replace(timestampPattern, '');
            }
            
            return cleanId;
          }
          
          // 5. 尝试使用索引信息
          if (indexId) {
            const indexInfo = indices.find(idx => idx.index_id === indexId || idx.id === indexId);
            if (indexInfo?.name) {
              return `Index: ${indexInfo.name}`;
            }
            if (indexInfo?.documents && indexInfo.documents.length > 0) {
              return indexInfo.documents[0].filename || `Document from index ${indexId}`;
            }
            return `Document from index ${indexId}`;
          }
          
          // 6. 最后的备选方案 - 使用搜索ID
          return `Search: ${searchId.substring(0, 8)}`;
        };
        
        // 获取文档名称
        const documentName = getDocumentName();
        console.log(`[handleGenerateText] Using document name: "${documentName}" for search ID: ${searchId}`);
        
        // 始终显示文档名称与搜索ID和相似度信息
        additionalInfo = language === 'zh'
          ? `\n\n---\n**[${usingContextLabel}]** ${docFilenameLabel} "${documentName}" (${searchIdLabel}: ${searchId})${similarityInfo}`
          : `\n\n---\n**[${usingContextLabel}]** ${docFilenameLabel} "${documentName}" (${searchIdLabel}: ${searchId})${similarityInfo}`;
      } else {
        // Clearly indicate when no document context was used
        const noContextLabel = t('noDocumentContext');
        additionalInfo = `\n\n---\n**[${noContextLabel}]** ${language === 'zh' ? 
          '此回答生成未使用任何文档索引或搜索上下文。' : 
          'This response was generated without using any document index or search context.'}`;
      }

      setChatHistory(prev => prev.filter(msg => msg.id !== thinkingMessageId));
      setChatHistory(prev => [...prev, { 
        id: data.generation_id || `ai-msg-${Date.now()}`,
        sender: 'ai', 
        text: data.generated_text + additionalInfo, 
        timestamp: new Date().toLocaleString(),
        model: actualModel, 
        references: data.references || [],
        search_id: searchId, // Store the search_id to indicate this was based on document search
        using_index: !!searchId // Explicitly store whether an index was used
      }]);
      return data;
    } catch (err) {
      console.error("Error in handleGenerateText:", err);
      setError(err.message);
      triggerNotification(`Generation failed: ${err.message}`, 'error');
      setChatHistory(prev => prev.filter(msg => msg.id !== thinkingMessageId));
      setChatHistory(prev => [...prev, {
        id: `gen-error-${Date.now()}`,
        sender: 'system',
        text: `Error during generation: ${err.message}`,
        timestamp: new Date().toLocaleString(),
        type: 'error'
      }]);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [t, language, chatHistory, indices, documents, searchResults, currentSearchResult]);

  const handleSearchAndGenerate = useCallback(async (indexId, query, model, provider = 'default', uploadedImage = null, searchParams = {}) => {
    try {
      // If indexId is provided, perform the search then generate 
      if (indexId) {
        // First, perform the search with custom search parameters
        const { similarityThreshold = 0.5, topK = 3 } = searchParams;
        console.log(`Searching with params: similarityThreshold=${similarityThreshold}, topK=${topK}`);
        
        const searchResult = await handleSearch(indexId, query, topK, similarityThreshold, 100);
        // Fix: Check for search_id (from backend) instead of id
        const searchId = searchResult.search_id || null;
        
        // Extract document filename from search result with improved fallback logic
        // This implements a more robust getDocumentName function similar to StorageInfoPanel
        const getDocumentName = () => {
          // First try to use the document_filename if available
          if (searchResult?.document_filename) {
            // Try to clean up the document name by removing timestamps and hashes
            const filename = searchResult.document_filename;
            
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
          else if (searchResult?.document_id) {
            const docId = searchResult.document_id;
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
          // Try extracting from search info
          else if (searchResult.search_info?.document_filename) {
            const filename = searchResult.search_info.document_filename;
            let cleanName = filename;
            
            // Clean any timestamp patterns
            const timestampPattern = /_\d{8}$/;
            if (timestampPattern.test(cleanName)) {
              cleanName = cleanName.replace(timestampPattern, '');
            }
            
            return cleanName;
          }
          // Try index name as a fallback
          else if (searchResult?.index_id) {
            return `Index: ${searchResult.index_id}`;
          }
          // If we still have no name, check the indices list
          else {
            const currentIndex = indices.find(idx => idx.index_id === indexId || idx.id === indexId);
            if (currentIndex) {
              if (currentIndex.name) {
                return currentIndex.name;
              } else if (currentIndex.documents && currentIndex.documents.length > 0) {
                return currentIndex.documents[0].filename || `Document from index ${indexId}`;
              }
            }
            // Final fallback
            return `Document from index ${indexId}`;
          }
        };
        
        const documentFilename = getDocumentName();
        
        // Log search result with document information for better debugging
        const searchCompletedLabel = t('searchCompleted');
        const docFilenameLabel = t('documentFilename');
        const searchIdLabel = t('searchIdLabel');
        
        if (documentFilename) {
          console.log(`${searchCompletedLabel} - ${docFilenameLabel} "${documentFilename}" (${searchIdLabel}: ${searchId})`);
          // Store the document name for use in chat messages and update currentSearchResult
          searchResult.document_filename = documentFilename;
          
          // Important - also update currentSearchResult with the document filename and search_id
          const updatedSearchResult = {
            ...searchResult,
            document_filename: documentFilename,
            search_id: searchId, // Ensure search_id is consistently stored
            timestamp: new Date().toISOString(), // Add timestamp for sorting in StorageInfoPanel
            // Ensure all similarity scores are properly formatted for consistent display
            results: searchResult.results?.map(result => ({
              ...result,
              similarity: typeof result.similarity === 'string' ? parseFloat(result.similarity) : result.similarity
            })) || []
          };
          
          // Store in global object to allow StorageInfoPanel to access it
          try {
            // Only set if we're in a browser environment
            if (typeof window !== 'undefined') {
              window.verseMindCurrentSearchResults = updatedSearchResult;
              console.log("Updated global search results object with document name and normalized similarity scores:", documentFilename);
            }
          } catch (err) {
            console.warn("Failed to update global search results object:", err);
          }
          
          // Update both state variables to ensure consistency
          setCurrentSearchResult(updatedSearchResult);
          setSearchResults(updatedSearchResult);
        } else {
          console.log(`${searchCompletedLabel} (${searchIdLabel}: ${searchId})`);
        }
        
        if (!searchId) {
          console.warn('Search completed but no search_id was returned. Falling back to direct generation.');
          // Fall back to direct generation
          return await handleGenerateText(null, query, provider, model);
        }
        
        // Generate text based on search results, passing document filename as metadata in the searchResult
        return await handleGenerateText(searchId, query, provider, model, uploadedImage);
      } else {
        // No index provided, directly generate text without search
        console.log('No index selected, generating text directly without search context');
        return await handleGenerateText(null, query, provider, model, uploadedImage);
      }
    } catch (err) {
      console.error('Error in search and generate workflow:', err);
      setError(err.message || 'An unknown error occurred during the search and generate process.');
      triggerNotification(err.message || 'Search and generate failed.', 'error');
      
      // Even if search fails, try direct generation as fallback
      try {
        console.log('Search failed, falling back to direct generation without context');
        return await handleGenerateText(null, query, provider, model);
      } catch (genErr) {
        console.error('Fallback generation also failed:', genErr);
        throw genErr;
      }
    }
  }, [handleSearch, handleGenerateText, setError, t]);

  useEffect(() => {
    if (selectedDocument && selectedDocument.id) {
      if (activeModule === 'chunk') {
        fetchChunks(selectedDocument.id);
      } else if (activeModule === 'parse') {
        // Call fetchParsed but don't need to store the result in state anymore
        fetchParsed(selectedDocument.id).then(result => {
          if (result) {
            console.log('Parsed document content fetched successfully');
          }
        }).catch(err => {
          console.error('Failed to fetch parsed document:', err);
        });
      } else if (activeModule === 'embed') {
        fetchEmbeddings(selectedDocument.id);
      }
    } else if (activeModule === 'embed') {
      fetchEmbeddings();
    }
  }, [selectedDocument, activeModule, fetchChunks, fetchParsed, fetchEmbeddings]);

  useEffect(() => {
    fetchDocuments();
    fetchIndices();
  }, [fetchDocuments, fetchIndices]);

  const handleModuleChange = (moduleName) => {
    setActiveModule(moduleName);
  };

  return (
    <div className="flex flex-col h-screen">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar 
          activeModule={activeModule} 
          onModuleChange={handleModuleChange} 
        />
        {notification.message && (
          <div className={`notification ${notification.type === 'error' ? 'bg-red-500' : 'bg-green-500'} text-white p-3 rounded-md fixed top-5 right-5 z-50`}>
            {notification.message}
          </div>
        )}
        <MainContent 
          activeModule={activeModule}
          documents={documents}
          chunks={chunks} // Pass chunks
          chunksLoading={chunksLoading} // Pass chunksLoading
          embeddings={embeddings}
          indices={indices}
          searchResults={searchResults}
          generatedText={generatedText}
          loading={loading}
          error={error}
          onDocumentUpload={handleDocumentUpload} 
          onChunkDocument={handleChunkDocument}
          onChunkDelete={handleChunkDelete}
          onParseDocument={handleParseDocument}
          onCreateEmbeddings={handleCreateEmbeddings}
          onEmbeddingDelete={handleEmbeddingDelete}
          onLoadEmbeddings={fetchEmbeddings}
          onCreateIndex={handleCreateIndex}
          onRefreshIndices={fetchIndices}
          onIndexDelete={handleIndexDelete}
          onDocumentDelete={handleDocumentDelete} 
          onSearch={handleSearch} 
          onGenerateText={handleGenerateText} 
          onSendMessage={handleSearchAndGenerate} 
          selectedDocumentObject={selectedDocument}
          onDocumentSelect={handleSelectDocument}
          selectedDocumentId={selectedDocumentId} // Pass selectedDocumentId
          chatHistory={chatHistory}
          currentTask={currentTask} 
          taskProgress={taskProgress} 
          config={config}
          configLoading={configLoading}
        />
      </div>
    </div>
  );
}

export default App;
