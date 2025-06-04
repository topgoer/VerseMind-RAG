import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import { useLanguage } from './contexts/LanguageContext';
import { loadConfig } from './utils/configLoader';

// 检查字符串是否为十六进制ID
const isHexIdString = (str) => {
  const hexPattern1 = /^[a-f0-9]{8,}$/i;
  const hexPattern2 = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
  return hexPattern1.exec(str) || hexPattern2.exec(str);
};

// 从索引对象获取文档名称
const getNameFromIndex = (idx) => {
  if (idx.collection_name) {
    return `Collection: ${idx.collection_name}`;
  } else if (idx.document_filename) {
    return idx.document_filename;
  } else if (idx.name) {
    return idx.name;
  }
  return null;
};

// 从rawSearchData尝试获取文档名称
const getNameFromRawSearchData = (rawSearchData) => {
  if (rawSearchData?.documentFilename) {
    return rawSearchData.documentFilename;
  }
  if (rawSearchData?.collectionName) {
    return `Collection: ${rawSearchData.collectionName}`;
  }
  return null;
};

// 从索引信息获取文档名称
const getNameFromIndexInfo = (indexInfo) => {
  if (!indexInfo) return null;
  
  if (indexInfo.collection_name) {
    return `Collection: ${indexInfo.collection_name}`;
  }
  if (indexInfo.document_filename) {
    return indexInfo.document_filename;
  }
  if (indexInfo.name) {
    return indexInfo.name;
  }
  return null;
};

// 从原始文档ID提取干净的名称
const getCleanedDocumentId = (documentId) => {
  if (!documentId) return null;
  
  const timestampHashPattern = /(_\d{8}_\d{6}_[a-f0-9]+)$/;
  let cleanId = documentId.replace(timestampHashPattern, '');
  
  const timestampPattern = /_\d{8}$/;
  if (timestampPattern.test(cleanId)) {
    cleanId = cleanId.replace(timestampPattern, '');
  }
  
  return (cleanId && cleanId !== documentId) ? cleanId : null;
};

// 从全局索引匹配检查
// 检查是否可以获取索引数据
const canAccessIndices = () => {
  return typeof window !== 'undefined' && Array.isArray(window.verseMindIndices);
};

// 通过完全匹配查找索引
const findExactMatchIndex = (indexId) => {
  return window.verseMindIndices.find(idx => 
    idx.index_id === indexId || idx.id === indexId
  );
};

// 通过部分匹配查找索引
const findPartialMatchIndex = (indexId) => {
  for (const idx of window.verseMindIndices) {
    if ((idx.index_id?.includes(indexId)) || (idx.id?.includes(indexId))) {
      const name = getNameFromIndex(idx);
      if (name) return name;
    }
  }
  return null;
};

// 从全局索引匹配检查 - 将复杂逻辑拆分为更小的函数
const getNameFromGlobalIndices = (indexId) => {
  // 基础验证
  if (!indexId || !canAccessIndices()) {
    return null;
  }
  
  // 检查是否是索引ID
  if (!isHexIdString(indexId)) {
    return null;
  }
  
  // 尝试完全匹配
  const matchingIndex = findExactMatchIndex(indexId);
  if (matchingIndex) {
    return getNameFromIndex(matchingIndex);
  }
  
  // 尝试部分匹配
  return findPartialMatchIndex(indexId);
};

// 尝试从原始文档名获取名称（如果不是索引ID）
const tryGetNameFromDocumentName = (docContext) => {
  if (docContext.documentName && docContext.documentName !== 'Unknown') {
    if (!isHexIdString(docContext.documentName)) {
      return docContext.documentName;
    }
  }
  return null;
};

// 尝试从全局索引匹配获取名称
const tryGetNameFromGlobalMatch = (docContext) => {
  if (docContext.documentName && docContext.documentName !== 'Unknown') {
    try {
      return getNameFromGlobalIndices(docContext.documentName);
    } catch (err) {
      console.error("[processDocumentName] Error while trying to find matching index:", err);
    }
  }
  return null;
};

// 尝试从搜索ID生成名称
const getNameFromSearchId = (searchId) => {
  if (searchId) {
    return `Search: ${searchId.substring(0, 8)}`;
  }
  return null;
};

// 修正：添加一个强化版的文档名称处理函数 - 确保在语言切换和初始渲染时使用相同的逻辑
// 移除大量日志输出以提高性能和避免控制台垃圾信息
const processDocumentName = (docContext) => {
  // 输入验证
  if (!docContext) {
    return 'Unknown';
  }
  
  // 按优先级顺序尝试不同的方法获取文档名
  const nameResolvers = [
    // 1) rawSearchData中的原始文件名（最高优先级）
    () => getNameFromRawSearchData(docContext.rawSearchData),
    
    // 2) 使用已保存的文档名（如果不是索引ID）
    () => tryGetNameFromDocumentName(docContext),
    
    // 3) 从索引信息获取名称
    () => getNameFromIndexInfo(docContext.indexInfo),
    
    // 4) 从文档ID提取清理后的名称
    () => docContext.rawSearchData?.documentId 
          ? getCleanedDocumentId(docContext.rawSearchData.documentId)
          : null,
    
    // 5) 从全局索引信息匹配
    () => tryGetNameFromGlobalMatch(docContext),
    
    // 6) 使用搜索ID作为最后的备选方案
    () => getNameFromSearchId(docContext.searchId)
  ];
  
  // 尝试每种方法直到找到有效名称
  for (const resolver of nameResolvers) {
    const name = resolver();
    if (name) return name;
  }
  
  // 如果所有方法都失败，返回默认值
  return 'Unknown';
};

// 添加全局文档查找函数，确保文档名称在应用程序的不同部分保持一致
const addToGlobalLookup = (searchId, documentName, collectionName, indexId) => {
  // 确保文档信息可在全局范围内使用，便于不同组件访问
  try {
    if (typeof window !== 'undefined') {
      // 初始化查询结果查找表（如果尚未存在）
      if (!window.verseMindDocumentLookup) {
        window.verseMindDocumentLookup = {};
      }
      
      // 存储这个搜索ID对应的文档信息
      window.verseMindDocumentLookup[searchId] = {
        documentName: documentName,
        collectionName: collectionName,
        indexId: indexId,
        timestamp: new Date().toISOString()
      };
      
      // 最多保留最近的50条记录（防止内存泄漏）
      const keys = Object.keys(window.verseMindDocumentLookup);
      if (keys.length > 50) {
        // 获取所有项目并按时间戳排序
        const items = keys.map(key => ({
          key,
          timestamp: window.verseMindDocumentLookup[key].timestamp
        }));
        
        // 按时间戳排序（最早的在前）
        items.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // 移除最旧的项目
        for (let i = 0; i < items.length - 50; i++) {
          delete window.verseMindDocumentLookup[items[i].key];
        }
      }
      
      // console.log(`Added document info to global lookup for search ID ${searchId}: "${documentName}"`);
    }
  } catch (err) {
    console.error("Failed to add to global document lookup:", err);
  }
};

function App() {
  const { t, language } = useLanguage();
  const [activeModule, setActiveModule] = useState('chat');
  
  // Expose setActiveModule to window object for cross-component navigation
  useEffect(() => {
    window.setActiveModule = (moduleName) => {
      // console.log(`[App] Setting active module to: ${moduleName}`);
      setActiveModule(moduleName);
    };
    
    // Cleanup
    return () => {
      window.setActiveModule = undefined;
    };
  }, []);
  
  // Clean up object URLs to prevent memory leaks
  useEffect(() => {
    // No operation on mount
    
    // Only in cleanup function
    return () => {
      // We need to use a function form of setChatHistory to get the latest value
      // and clean up URLs without using chatHistory directly in the cleanup function
      setChatHistory(currentChatHistory => {
        // When component unmounts, clean up any object URLs
        if (currentChatHistory) {
          currentChatHistory.forEach(message => {
            // Clean up user uploaded images
            if (message?.image?.startsWith('blob:')) {
              URL.revokeObjectURL(message.image);
            }
            
            // Clean up AI generated images if they're blob URLs
            if (message?.generatedImage?.startsWith('blob:')) {
              URL.revokeObjectURL(message.generatedImage);
            }
          });
        }
        return currentChatHistory; // Return unchanged to avoid re-render
      });
    };
  }, []);
  
  // 处理模块切换
  const handleModuleChange = (moduleName) => {
    // console.log(`[App] Changing module to: ${moduleName} (via sidebar)`);
    setActiveModule(moduleName);
  };
  
  // 处理文档上传
  const handleDocumentUpload = async (formData) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log('[App] Uploading document...');
      
      // 发送POST请求到后端API
      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.message || 'Failed to upload document');
      }
      
      const result = await response.json();
      // console.log('[App] Document uploaded successfully:', result);
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: `${t('documentUploaded')}: ${result.filename || 'Unknown'}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // 刷新文档列表
      // console.log(`[App] Refreshing document list after upload...`);
      await fetchDocuments();
      
      setLoading(false);
      return result;
    } catch (err) {
      console.error('[App] Document upload error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('uploadError')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // 处理文档分块
  const handleChunkDocument = async (documentId, strategy, chunkSize, overlap) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Chunking document ${documentId} with strategy ${strategy}...`);
      
      // Additional validation
      if (!documentId) {
        throw new Error('No document ID provided for chunking');
      }
      
      // Check if document exists in our documents list
      const documentExists = documents.some(doc => doc.id === documentId);
      if (!documentExists) {
        console.warn(`[App] Warning: Attempting to chunk document ${documentId} that is not in the documents list`);
        // console.log('[App] Available documents:', documents.map(doc => ({ id: doc.id, filename: doc.filename })));
      }
      
      // 发送POST请求到后端API
      const response = await fetch('/api/chunks/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          strategy,
          chunk_size: parseInt(chunkSize),
          overlap: parseInt(overlap)
        }),
      });
      
      if (!response.ok) {
        let errorMessage = 'Failed to chunk document';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
          console.error('[App] Server returned error:', errorData);
        } catch (e) {
          console.error('[App] Could not parse error response:', e);
        }
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      // console.log('[App] Document chunking successful:', result);
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: `${t('documentChunked')}: ${result.total_chunks || 0} ${t('chunks')}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // 刷新分块列表
      // console.log('[App] Refreshing chunks list after chunking');
      await fetchChunks();
      
      setLoading(false);
      return result;
    } catch (err) {
      console.error('[App] Document chunking error:', err);
      
      // Enhanced error logging
      console.error(`[App] Chunking details - Document ID: ${documentId}, Strategy: ${strategy}, ChunkSize: ${chunkSize}, Overlap: ${overlap}`);
      
      // Try to parse more detailed error information if available
      let errorMessage = err.message || 'Failed to chunk document';
      try {
        if (err.message && err.message.includes('{')) {
          const jsonStart = err.message.indexOf('{');
          const errorData = JSON.parse(err.message.substring(jsonStart));
          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        }
      } catch (parseErr) {
        console.warn('[App] Failed to parse error details:', parseErr);
      }
      
      setError(errorMessage);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('chunkingFailed')}: ${errorMessage}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };

  // 处理分块删除
  const handleChunkDelete = async (chunkId) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Deleting chunk ${chunkId}...`);
      
      // 发送DELETE请求到后端API
      const response = await fetch(`/api/chunks/${chunkId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete chunk');
      }
      
      // console.log('[App] Chunk deletion successful');
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: t('chunkDeleted')
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // 更新本地状态
      setChunks(prevChunks => prevChunks.filter(chunk => chunk.id !== chunkId));
      
      setLoading(false);
    } catch (err) {
      console.error('[App] Chunk deletion error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('deleteFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };

  // 处理文档解析
  const handleParseDocument = async (documentId, strategy, extractTables, extractImages) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Parsing document ${documentId}...`);
      
      // 发送POST请求到后端API
      const response = await fetch('/api/parse/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          strategy,
          extract_tables: extractTables,
          extract_images: extractImages
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to parse document');
      }
      
      const result = await response.json();
      // console.log('[App] Document parsing successful:', result);
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: `${t('documentParsed')}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      setLoading(false);
      return result;
    } catch (err) {
      console.error('[App] Document parsing error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('parsingFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // 处理向量嵌入
  const handleCreateEmbeddings = async (documentId, provider, model) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Creating embeddings for document ${documentId}...`);
      
      // 发送POST请求到后端API
      const API_URL = '/api/embeddings/create';
      // console.log(`[App] Sending POST to ${API_URL} with provider=${provider}, model=${model}`);
      
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          provider,
          model
        }),
      });
      
      if (!response.ok) {
        let errorMessage = 'Failed to create embeddings';
        
        // Handle specific error codes
        if (response.status === 404) {
          errorMessage = 'API endpoint not found. Check that the backend is running correctly.';
          console.error(`[App] API endpoint not found (404): ${API_URL}`);
        }
        
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (parseError) {
          console.error('[App] Error parsing error response:', parseError);
        }
        
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      // console.log('[App] Embeddings creation successful:', result);
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: `${t('embeddingsCreated')}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // 刷新嵌入列表
      await fetchEmbeddings();
      
      setLoading(false);
      return result;
    } catch (err) {
      console.error('[App] Embeddings creation error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('embeddingFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // 处理嵌入删除
  const handleEmbeddingDelete = async (embeddingId) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Deleting embedding ${embeddingId}...`);
      
      // 发送DELETE请求到后端API
      const response = await fetch(`/api/embeddings/${embeddingId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete embedding');
      }
      
      // console.log('[App] Embedding deletion successful');
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: t('embeddingDeleted')
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // 更新本地状态
      setEmbeddings(prevEmbeddings => 
        prevEmbeddings.filter(emb => emb.embedding_id !== embeddingId)
      );
      
      setLoading(false);
    } catch (err) {
      console.error('[App] Embedding deletion error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('deleteFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // 获取嵌入列表
  const fetchEmbeddings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log('[App] Fetching embeddings...');
      
      // 发送GET请求到后端API
      const response = await fetch('/api/embeddings/list');
      
      if (!response.ok) {
        // Don't treat 404 (not found) as an error for empty embedding folder
        if (response.status === 404) {
          // console.log('[App] No embeddings found (404)');
          setEmbeddings([]);
          setLoading(false);
          return [];
        }
        
        let errorMessage = 'Failed to fetch embeddings';
        try {
          const errorData = await response.json();
          errorMessage = errorData.message || errorMessage;
        } catch (parseError) {
          console.error('[App] Error parsing error response:', parseError);
        }
        throw new Error(errorMessage);
      }
      
      let result;
      try {
        result = await response.json();
        // Validate that result is an array
        if (!Array.isArray(result)) {
          console.warn('[App] Embeddings result is not an array:', result);
          result = [];
        }
      } catch (parseError) {
        console.error('[App] Error parsing embeddings response:', parseError);
        result = [];
      }
      
      // console.log('[App] Fetched embeddings:', result.length);
      
      setEmbeddings(result);
      setLoading(false);
      return result;
    } catch (err) {
      console.error('[App] Fetch embeddings error:', err);
      setError(err.message);
      setLoading(false);
      // Return empty array instead of throwing to prevent component errors
      return [];
    }
  };
  
  // 处理索引创建
  const handleCreateIndex = async (documentId, vectorDb, embeddingId, collectionName, indexName) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Creating index for document ${documentId} with embedding ${embeddingId}...`);
      
      // 发送POST请求到后端API
      const response = await fetch('/api/indices/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          embedding_id: embeddingId,
          vector_db: vectorDb,
          collection_name: collectionName,
          index_name: indexName
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to create index');
      }
      
      const result = await response.json();
      // console.log('[App] Index creation successful:', result);
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: `${t('indexCreated')}: ${indexName || collectionName}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // 刷新索引列表
      await fetchIndices();
      
      setLoading(false);
      return result;
    } catch (err) {
      console.error('[App] Index creation error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('indexingFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // 获取索引列表
  const fetchIndices = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log('[App] Fetching indices...');
      
      // 发送GET请求到后端API
      const response = await fetch('/api/indices/list', {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      });
      
      // console.log('[App] API response status:', response.status);
      
      if (!response.ok) {
        let errorMessage = 'Failed to fetch indices';
        try {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.detail || errorMessage;
        } catch (jsonError) {
          console.error('[App] Error parsing error response:', jsonError);
          errorMessage = `Server responded with status ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      // console.log('[App] Fetched indices:', result);
      
      // Debug: Log collection names from the response
      if (Array.isArray(result)) {
        const collections = [...new Set(result
          .filter(idx => idx?.collection_name)
          .map(idx => idx.collection_name))];
        // console.log('[App] Collection names found in API response:', collections);
        // console.log('[App] Total indices found:', result.length);
        
        // Log the first index to see its structure
        if (result.length > 0) {
          // console.log('[App] First index structure:', result[0]);
        } else {
          console.warn('[App] No indices found in the API response');
        }
      } else {
        console.error('[App] API response is not an array:', result);
      }
      
      // 将索引信息保存到全局变量，以供文档名称解析使用
      if (typeof window !== 'undefined') {
        window.verseMindIndices = result;
      }
      
      setIndices(result);
      setLoading(false);
      return result;
    } catch (err) {
      console.error('[App] Fetch indices error:', err);
      setError(`Failed to fetch indices: ${err.message}`);
      
      // Set indices to an empty array to prevent undefined errors
      setIndices([]);
      setLoading(false);
      throw err;
    }
  };
  
  // 获取文档列表
  const fetchDocuments = async () => {
    try {
      // console.log('[App] Fetching documents list...');
      const response = await fetch('/api/documents/list');
      
      if (!response.ok) {
        throw new Error(`Failed to fetch documents: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      // console.log(`[App] Fetched ${data.length} documents`);
      setDocuments(data);
      return data;
    } catch (err) {
      console.error('[App] Error fetching documents:', err);
      // Don't override existing errors from other operations
      if (!error) {
        setError(err.message);
      }
      return [];
    }
  };
  
  // 处理索引删除
  const handleIndexDelete = async (indexId) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Deleting index ${indexId}...`);
      
      // 发送DELETE请求到后端API
      const response = await fetch(`/api/indices/${indexId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to delete index');
      }
      
      // console.log('[App] Index deletion successful');
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: t('indexDeleted')
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // 更新本地状态
      setIndices(prevIndices => 
        prevIndices.filter(idx => idx.index_id !== indexId)
      );
      
      setLoading(false);
    } catch (err) {
      console.error('[App] Index deletion error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('deleteFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // Get list of document IDs that have been chunked
  const getChunkedDocumentIds = () => {
    if (!Array.isArray(chunks)) return [];
    
    // Extract unique document IDs from chunks
    const docIds = [...new Set(chunks.map(chunk => chunk.document_id))];
    // console.log(`[App] Found ${docIds.length} chunked document IDs`);
    return docIds;
  };
  
  // 处理文档删除
  const handleDocumentDelete = async (documentId) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Deleting document ${documentId}...`);
      // console.log(`[App] Current documents before deletion:`, documents.length);
      
      // 发送DELETE请求到后端API
      const response = await fetch(`/api/documents/${documentId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[App] Document deletion API error (${response.status}):`, errorText);
        try {
          const errorData = JSON.parse(errorText);
          throw new Error(errorData.detail || errorData.message || 'Failed to delete document');
        } catch (parseError) {
          throw new Error(`Failed to delete document: ${response.status} ${errorText || response.statusText}`);
        }
      }
      
      // console.log('[App] Document deletion successful');
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: t('documentDeleted')
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // Update local status - remove document and related resources
      setDocuments(prevDocs => 
        prevDocs.filter(doc => doc.id !== documentId)
      );
      setChunks(prevChunks => 
        prevChunks.filter(chunk => chunk.document_id !== documentId)
      );
      setEmbeddings(prevEmbeddings => 
        prevEmbeddings.filter(emb => emb.document_id !== documentId)
      );
      setIndices(prevIndices => 
        prevIndices.filter(idx => idx.document_id !== documentId)
      );
      
      // Refresh document list to ensure UI is up to date
      // console.log(`[App] Refreshing document list after deletion...`);
      await fetchDocuments();
      
      setLoading(false);
    } catch (err) {
      console.error('[App] Document deletion error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('deleteFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // 处理文档搜索
  const handleSearch = async (indexId, query, topK = 5, threshold = 0.7, minChars = 100, collectionName = null) => {
    try {
      setLoading(true);
      setError(null);
      
      // If a collection was specified, modify the search logic
      if (collectionName) {
        // console.log(`[App] Searching collection ${collectionName} for "${query}"...`);
        
        // Get indices belonging to this collection
        const collectionIndices = indices.filter(idx => idx.collection_name === collectionName);
        
        if (!collectionIndices || collectionIndices.length === 0) {
          throw new Error(`No indices found in collection: ${collectionName}`);
        }
        
        // Use the first index as a starting point (or the selected index if provided)
        const targetIndexId = indexId || collectionIndices[0].index_id;
        
        // Send POST request with the collection name as the index_id_or_collection parameter
        const response = await fetch('/api/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            index_id_or_collection: collectionName, // Use collection name directly
            query,
            top_k: topK,
            similarity_threshold: threshold,
            min_chars: minChars
          }),
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || 'Failed to search collection');
        }
        
        const result = await response.json();
        // console.log('[App] Collection search successful:', result);
        
        // Add collection name to the result for UI display
        result.collectionName = collectionName;
        
        // 添加消息通知
        const resultCount = result.results?.length || 0;
        setNotification({
          type: 'success',
          message: `${t('searchCompleted')}: ${resultCount} ${t('resultsFound')} ${t('inCollection')}: ${collectionName}`
        });
        
        // 清除通知
        setTimeout(() => setNotification({ type: '', message: '' }), 3000);
        
        // 保存搜索结果
        setSearchResults(result);
        setCurrentSearchResult(result);
        
        setLoading(false);
        return result;
      } else {
        // Original single-index search logic
        // console.log(`[App] Searching index ${indexId} for "${query}"...`);
        
        // 发送POST请求到后端API
        const response = await fetch('/api/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            index_id_or_collection: indexId, // Use consistent parameter name
            query,
            top_k: topK,
            similarity_threshold: threshold,
            min_chars: minChars
          }),
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || 'Failed to search index');
        }
        
        const result = await response.json();
        // console.log('[App] Search successful:', result);
        
        // 添加消息通知
        const resultCount = result.results?.length || 0;
        setNotification({
          type: 'success',
          message: `${t('searchCompleted')}: ${resultCount} ${t('resultsFound')}`
        });
        
        // 清除通知
        setTimeout(() => setNotification({ type: '', message: '' }), 3000);
        
        // 保存搜索结果
        setSearchResults(result);
        setCurrentSearchResult(result);
        
        setLoading(false);
        return result;
      }
    } catch (err) {
      console.error('[App] Search error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('searchFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // 处理文本生成
  const handleGenerateText = async (searchId, prompt, provider, model, temperature = 0.7, maxTokens = null) => {
    try {
      setLoading(true);
      setError(null);
      
      // console.log(`[App] Generating text for search ${searchId} with model ${model}...`);
      
      // 发送POST请求到后端API
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          search_id: searchId,
          prompt,
          provider,
          model,
          temperature,
          max_tokens: maxTokens
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to generate text');
      }
      
      const result = await response.json();
      // console.log('[App] Text generation successful:', result);
      
      // 添加消息通知
      setNotification({
        type: 'success',
        message: `${t('textGenerated')}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 3000);
      
      // 保存生成结果
      setGeneratedText(result);
      
      setLoading(false);
      return result;
    } catch (err) {
      console.error('[App] Text generation error:', err);
      setError(err.message);
      setLoading(false);
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('generationFailed')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };
  
  // 处理选择文档
  const handleSelectDocument = (documentOrId) => {
    // If a string (document ID) is passed, find the document in the documents array
    if (typeof documentOrId === 'string') {
      const document = documents.find(doc => doc.id === documentOrId);
      if (document) {
        setSelectedDocument(document);
        setSelectedDocumentId(document.id);
        // console.log(`[App] Selected document by ID: ${document.id} (${document.filename})`);
      } else {
        console.error(`[App] Could not find document with ID: ${documentOrId}`);
      }
    } else {
      // Handle document object directly
      setSelectedDocument(documentOrId);
      setSelectedDocumentId(documentOrId?.id || null);
      // console.log(`[App] Selected document: ${documentOrId?.id || 'none'}`);
    }
  };
  
  // 处理搜索和生成（聊天模式）
  const handleSearchAndGenerate = async (indexId, message, provider, model, selectedImage = null, searchParams = {}) => {
    try {
      setLoading(true);
      setError(null);
      
      // Default temperature value if not provided in searchParams
      const temperature = searchParams?.temperature || 0.7;
      
      // console.log(`[App] Processing chat message: "${message}" with index ${indexId}`);
      
      // 添加用户消息到聊天历史
      const userMessage = {
        sender: 'user',
        text: message,
        timestamp: new Date().toLocaleString(),
        id: `user-${Date.now()}`
      };
      
      // If there's an image, create an object URL and add it to the message
      if (selectedImage) {
        userMessage.image = URL.createObjectURL(selectedImage);
      }
      
      setChatHistory(prev => [...prev, userMessage]);
      
      // 步骤1：搜索
      let searchResult = null;
      let documentContext = null;
      
      if (indexId) {
        // Get search parameters from searchParams or use defaults
        const topK = searchParams.topK || 5;
        const similarityThreshold = searchParams.similarityThreshold || 0.7;
        const inputType = searchParams.inputType || 'index_id';
        
        // console.log(`[App] Searching with ${inputType === 'collection_name' ? 'collection' : 'index'} ${indexId} for relevant information...`);
        
        // 发送POST请求到后端API
        const searchResponse = await fetch('/api/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            index_id_or_collection: indexId, // Use consistent parameter name
            query: message,
            top_k: topK,
            similarity_threshold: similarityThreshold
          }),
        });
        
        if (!searchResponse.ok) {
          const errorData = await searchResponse.json();
          throw new Error(errorData.message || 'Failed to search index');
        }
        
        searchResult = await searchResponse.json();
        setCurrentSearchResult(searchResult);
        
        // 准备文档上下文信息
        if (searchResult) {
          // 获取索引信息
          const indexInfo = indices.find(idx => idx.index_id === indexId);
          
          // 构建文档上下文
          documentContext = {
            searchId: searchResult.search_id,
            documentName: indexInfo?.document_filename || indexInfo?.collection_name || indexId,
            indexInfo: indexInfo,
            rawSearchData: searchResult,
            similarities: searchResult.results?.map(r => r.similarity).filter(Boolean)
          };
        }
      }
      
      // 步骤2：生成文本
      // console.log(`[App] Generating AI response with model ${model}...`);
      
      const generateBody = {
        prompt: message,
        provider,
        model,
        temperature
      };
      
      // 如果有搜索结果，使用搜索ID
      if (searchResult?.search_id) {
        generateBody.search_id = searchResult.search_id;
      }
      
      // If there's an image, convert it to base64 and add it to the request
      if (selectedImage) {
        try {
          // Convert the image to base64
          const reader = new FileReader();
          // Use a promise to handle the async FileReader
          const imageData = await new Promise((resolve, reject) => {
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error('Failed to read image file'));
            reader.readAsDataURL(selectedImage);
          });
          
          // Extract just the base64 part without the data:image prefix
          const base64Data = imageData.split(',')[1];
          generateBody.image_data = base64Data;
        } catch (imgErr) {
          console.error('[App] Error processing image:', imgErr);
          // Continue without the image if processing fails
        }
      }
      
      // Send the generation request
      const generateResponse = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(generateBody),
      });
      
      if (!generateResponse.ok) {
        const errorData = await generateResponse.json();
        throw new Error(errorData.message || 'Failed to generate response');
      }
      
      const generateResult = await generateResponse.json();
      // console.log('[App] Generation successful:', generateResult);
      
      // 添加AI回复到聊天历史
      const aiMessage = {
        sender: 'ai',
        text: generateResult.generated_text,
        originalContent: generateResult.generated_text, // 保存原始LLM响应，避免被后续处理破坏
        timestamp: new Date().toLocaleString(),
        model: generateResult.model,
        id: `ai-${Date.now()}`,
        search_id: searchResult?.search_id,
        documentContext: documentContext
      };
      
      // Only include generated images from the model, not the uploaded image
      // This prevents duplicate images in the chat (following test-image-display.ps1 guidance)
      
      // If the model returned an image (for models that can generate images)
      if (generateResult.generated_image) {
        aiMessage.generatedImage = generateResult.generated_image;
      }
      
      // Add a reference that this message was in response to an image
      if (selectedImage) {
        aiMessage.respondsToImage = true;
      }
      
      setChatHistory(prev => [...prev, aiMessage]);
      
      // 如果有搜索ID和文档名，添加到全局查找表
      if (searchResult?.search_id && documentContext?.documentName) {
        addToGlobalLookup(
          searchResult.search_id, 
          documentContext.documentName,
          documentContext.indexInfo?.collection_name,
          indexId
        );
      }
      
      setLoading(false);
      return aiMessage;
    } catch (err) {
      console.error('[App] Chat processing error:', err);
      setError(err.message);
      setLoading(false);
      
      
      // 添加错误通知
      setNotification({
        type: 'error',
        message: `${t('chatError')}: ${err.message}`
      });
      
      // 清除通知
      setTimeout(() => setNotification({ type: '', message: '' }), 5000);
      
      throw err;
    }
  };

  const [documents, setDocuments] = useState([]);
  const [chunks, setChunks] = useState([]);
  const [chunksLoading, setChunksLoading] = useState(false); // New state for chunks loading
  const [chunksError, setChunksError] = useState(null); // New state for chunks error
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
      text: t('welcomeMessage'),
      timestamp: new Date().toLocaleString(), 
      model: 'System',
      id: 'system-welcome'
    }
  ]);
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [notification, setNotification] = useState({ type: '', message: '' });
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [currentTask, setCurrentTask] = useState(null);
  const [taskProgress, setTaskProgress] = useState('');
  // Removed unused notificationRef

  // Load config and initial data
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Load configuration
        const cfg = await loadConfig();
        setConfig(cfg);
        setConfigLoading(false);
        
        // Load indices data for collections
        // console.log('[App] Initial load - fetching indices data...');
        const indicesData = await fetchIndices();
        
        // Add diagnostic info after loading indices
        // console.log('[App] Initialization completed - indices loaded:', 
        //   Array.isArray(indicesData) ? indicesData.length : 'none',
        //   'collections:', 
        //   Array.isArray(indicesData) 
        //     ? [...new Set(indicesData.filter(i => i.collection_name).map(i => i.collection_name))]
        //     : 'none'
        // );
        
        // Load document list
        await fetchDocuments();
        // Optionally load embeddings
        // await fetchEmbeddings();
      } catch (err) {
        console.error('[App] Error during app initialization:', err);
        setError('Failed to initialize application data');
      }
    };
    
    initializeApp();
  }, []);
  
  // Function to fetch chunks
  const fetchChunks = async () => {
    // console.log('[App] Fetching chunks list');
    setChunksLoading(true); // Set loading state
    try {
      const response = await fetch('/api/chunks/list');
      if (!response.ok) {
        throw new Error(`Failed to fetch chunks: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      // console.log(`[App] Fetched ${data.length} chunks`);
      setChunks(data);
    } catch (err) {
      console.error('[App] Error fetching chunks list:', err);
      setChunksError(err.message);
    } finally {
      setChunksLoading(false);
    }
  };

  // Add effect to load documents when entering the document-related modules
  useEffect(() => {
    if (activeModule === 'load' || activeModule === 'chunk' || activeModule === 'parse' || activeModule === 'embedding') {
      // console.log(`[App] Loading documents for ${activeModule} module`);
      fetchDocuments().catch(err => {
        console.error(`[App] Error loading documents for ${activeModule} module:`, err);
      });
      
      // Fetch chunks list for several modules that need to work with chunks
      if (activeModule === 'chunk' || activeModule === 'parse' || activeModule === 'embedding') {
        // console.log(`[App] Fetching chunks for ${activeModule} module`);
        fetchChunks();
      }
    }
  }, [activeModule]);
  
  // Add a new useEffect to update message translations when language changes
  // 添加处理标记，避免过度重新渲染和重复处理文档名称
  useEffect(() => {
    if (chatHistory.length === 0) return;

    // 创建语言+索引数据的缓存键，用于确定是否需要重新处理消息
    const cacheKey = `${language}-${indices ? indices.length : 0}`;
    
    setChatHistory(prevChatHistory => prevChatHistory.map(msg => {
      if (msg.sender !== 'ai' || !msg.text) {
        return msg;
      }
      
      // 如果消息已经用当前语言处理过，无需再次处理
      if (msg.processedWithLanguage === cacheKey) {
        return msg;
      }

      const mainContentSeparator = '\n\n---\n';
      let mainContent = msg.text;
      let existingFooter = '';
      const hasExistingSeparator = msg.text.includes(mainContentSeparator);

      if (hasExistingSeparator) {
        const parts = msg.text.split(mainContentSeparator);
        mainContent = parts[0]; // Content before the first separator
        existingFooter = parts.slice(1).join(mainContentSeparator); // In case there are multiple separators, rejoin them
      }
      // If no separator, mainContent remains msg.text, existingFooter remains empty.

      // 存储原始AI响应内容，以便在需要重新处理（如语言切换）时使用
      // 如果尚未保存，则使用当前mainContent
      const originalContent = msg.originalContent || mainContent;

      // Logic for messages with structured documentContext (from search results)
      if (msg.documentContext) {
        const usingContextLabel = t('usingDocumentContext');
        const docFilenameLabel = t('documentFilename');
        const searchIdLabel = t('searchIdLabel');
        const similarityLabel = t('similarity');

        const documentName = processDocumentName(msg.documentContext);
        const searchId = msg.documentContext.searchId || 'Unknown';
        let similarityInfo = '';

        if (msg.documentContext.similarities && msg.documentContext.similarities.length > 0) {
          const topSimilarity = msg.documentContext.similarities[0];
          // Format similarity showing exactly 4 decimal places to match StorageInfoPanel display
          // 使用固定的格式显示相似度，确保与StorageInfoPanel保持一致
          const formattedSimilarity = (Math.round(parseFloat(topSimilarity) * 10000) / 10000).toFixed(4);
          similarityInfo = ` ${similarityLabel}:: ${formattedSimilarity}`;
        }

        const newFooter = `**[${usingContextLabel}]** ${docFilenameLabel}: "${documentName}" (${searchIdLabel}: ${searchId})${similarityInfo}`;
        
        // Always reconstruct the text with originalContent + separator + newFooter
        // 修复: 使用保存的原始内容，而不是可能已经包含页脚的mainContent
        return { 
          ...msg, 
          text: `${originalContent}${mainContentSeparator}${newFooter}`,
          originalContent: originalContent, // 保存原始内容以便将来重新处理
          processedWithLanguage: cacheKey // 标记为已处理，避免重复处理
        };
      }
      // Logic for messages that indicate "No Document Context"
      else if (msg.text.includes('**[No Document Context]**') || msg.text.includes('**[无文档上下文]**')) {
        // This part handles translation of the "No Document Context" footer.
        const noContextLabel = t('noDocumentContext');
        
        // 直接使用原始内容加新的翻译后标签，而不是尝试替换旧标签
        return { 
          ...msg, 
          text: `${originalContent}${mainContentSeparator}**[${noContextLabel}]**`,
          originalContent: originalContent,
          processedWithLanguage: cacheKey
        };
      }
      
      // If none of the above, mark as processed but don't change content
      return {
        ...msg,
        processedWithLanguage: cacheKey
      };
    }));
  }, [chatHistory, language, t, processDocumentName, indices]);

  // Effect to update the welcome message when language changes
  useEffect(() => {
    if (chatHistory.length === 0) return;
    
    // Check if the first message is the welcome message
    const firstMessage = chatHistory[0];
    if (firstMessage.id === 'system-welcome') {
      setChatHistory(prevHistory => {
        const updatedHistory = [...prevHistory];
        updatedHistory[0] = {
          ...updatedHistory[0],
          text: t('welcomeMessage')
        };
        return updatedHistory;
      });
    }
  }, [language, t]);
  
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
          chunks={chunks}
          chunksLoading={chunksLoading}
          chunksError={chunksError}
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
          onRefreshDocuments={fetchDocuments}
          onIndexDelete={handleIndexDelete}
          onDocumentDelete={handleDocumentDelete}
          onSearch={handleSearch}
          onGenerateText={handleGenerateText}
          onSendMessage={handleSearchAndGenerate}
          selectedDocumentObject={selectedDocument}
          onDocumentSelect={handleSelectDocument}
          selectedDocumentId={selectedDocumentId}
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
