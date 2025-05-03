import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import { useLanguage } from './contexts/LanguageContext';
import { loadConfig } from './utils/configLoader';

function App() {
  const { t, language } = useLanguage();
  const [activeModule, setActiveModule] = useState('chat');
  const [documents, setDocuments] = useState([
    { id: 'doc1', filename: 'sample_report.pdf', file_type: 'pdf', file_size: 1024576, upload_time: '20250412_090000', title: '季度财务报告', pages: 15 },
    { id: 'doc2', filename: 'product_manual.docx', file_type: 'docx', file_size: 512000, upload_time: '20250412_091500', title: '产品使用手册', pages: 28 },
    { id: 'doc3', filename: 'research_paper.pdf', file_type: 'pdf', file_size: 2048000, upload_time: '20250412_093000', title: '人工智能研究论文', pages: 42 }
  ]);
  const [chunks, setChunks] = useState([
    { id: 'chunk1', document_id: 'doc1', strategy: 'paragraph', chunk_size: 1000, overlap: 200, total_chunks: 25 },
    { id: 'chunk2', document_id: 'doc2', strategy: 'character', chunk_size: 1500, overlap: 150, total_chunks: 18 }
  ]);
  const [embeddings, setEmbeddings] = useState([
    { document_id: 'doc1', embedding_id: 'emb1', provider: 'ollama', model: 'bge-large', dimensions: 1024, total_embeddings: 25 },
    { document_id: 'doc2', embedding_id: 'emb2', provider: 'openai', model: 'text-embedding-3-small', dimensions: 1536, total_embeddings: 18 }
  ]);
  const [indices, setIndices] = useState([
    { document_id: 'doc1', index_id: 'idx1', vector_db: 'faiss', collection_name: 'finance', index_name: 'quarterly_reports', version: '1.0', total_vectors: 25 },
    { document_id: 'doc2', index_id: 'idx2', vector_db: 'chroma', collection_name: 'manuals', index_name: 'product_guides', version: '1.0', total_vectors: 18 }
  ]);
  const [searchResults, setSearchResults] = useState({
    search_id: 'search1',
    query: '第一季度的销售额是多少？',
    index_id: 'idx1',
    results: [
      { id: 'res1', text: '2025年第一季度销售额达到1,250万元，比去年同期增长15%。这一增长主要得益于新产品线的推出和东南亚市场的扩张。', similarity: 0.92, source: '文档 doc1' },
      { id: 'res2', text: '各地区销售情况：北美地区：420万元（+8%）；欧洲地区：380万元（+12%）；亚太地区：450万元（+25%）。', similarity: 0.85, source: '文档 doc1' },
      { id: 'res3', text: '第一季度营销支出为210万元，占销售额的16.8%，比计划低2个百分点，同时实现了更高的销售转化率。', similarity: 0.78, source: '文档 doc1' }
    ]
  });
  const [generatedText, setGeneratedText] = useState({
    generation_id: 'gen1',
    prompt: '总结第一季度的销售情况',
    provider: 'ollama',
    model: 'llama3',
    generated_text: '根据文档内容，2025年第一季度销售表现强劲，总销售额达到1,250万元，比去年同期增长15%。这一增长主要归功于两个因素：新产品线的成功推出以及东南亚市场的战略扩张。\n\n从地区分布来看，亚太地区表现最为突出，销售额达450万元，同比增长25%，成为增长最快的区域。欧洲地区销售额为380万元，增长12%，表现也很稳健。北美地区贡献了420万元的销售额，增长8%，虽然增速相对较低，但仍保持了正向增长。\n\n值得注意的是，公司在营销效率方面也取得了显著成效。第一季度营销支出为210万元，仅占销售额的16.8%，比原计划低2个百分点，同时实现了更高的销售转化率，表明营销策略优化取得了良好效果。'
  });
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
  const [pendingApiCall, setPendingApiCall] = useState(null);
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);

  useEffect(() => {
    loadConfig().then(cfg => {
      setConfig(cfg);
      setConfigLoading(false);
    });
  }, []);

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

  const simulateApiCall = (data, delay = 1000) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(data);
      }, delay);
    });
  };

  useEffect(() => {
    if (!pendingApiCall) return;

    const { indexId, prompt, provider, model, temperature, maxTokens, imageFile } = pendingApiCall;
    const executeApiCall = async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = {
          index_id: indexId,
          prompt,
          provider,
          model,
          temperature: parseFloat(temperature || 0.7),
          ...(maxTokens ? { max_tokens: parseInt(maxTokens) } : {})
        };
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
        const res = await fetch(`${apiBase}/api/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        const result = await res.json();
        setGeneratedText(result);
        if (activeModule === 'chat') {
          const aiTimestamp = new Date().toLocaleString();
          setChatHistory(prev => [
            ...prev,
            {
              sender: 'ai',
              text: result.generated_text || result.response || '',
              timestamp: aiTimestamp,
              model: model,
              id: `ai-${Date.now()}`
            }
          ]);
        }
      } catch (error) {
        setError(t('generationFailed') + ": " + error.message);
        if (activeModule === 'chat') {
          const errorTimestamp = new Date().toLocaleString();
          setChatHistory(prev => [
            ...prev,
            {
              sender: 'system',
              text: `${t('error')}: ${t('generationFailed')}`,
              timestamp: errorTimestamp,
              model: 'System',
              id: `error-${Date.now()}`
            }
          ]);
        }
      } finally {
        setLoading(false);
        setPendingApiCall(null);
      }
    };
    executeApiCall();
  }, [pendingApiCall, t, activeModule]);

  const handleModuleChange = (moduleName) => {
    setActiveModule(moduleName);
  };

  const handleDocumentUpload = async (formData) => {
    try {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const newDoc = {
        id: `doc${documents.length + 1}`,
        filename: formData.get('file').name,
        file_type: formData.get('file').name.split('.').pop(),
        file_size: Math.floor(Math.random() * 1000000) + 500000,
        upload_time: new Date().toISOString().replace(/[-:]/g, '').substring(0, 13),
        title: formData.get('file').name.split('.')[0],
        pages: Math.floor(Math.random() * 30) + 5
      };
      
      setDocuments([...documents, newDoc]);
      setLoading(false);
      return newDoc;
    } catch (error) {
      setError(t('uploadFailed') + ": " + error.message);
      setLoading(false);
      throw error;
    }
  };

  const handleDocumentDelete = async (documentId) => {
    try {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 500)); 
      
      setDocuments(prevDocs => prevDocs.filter(doc => doc.id !== documentId));
      setChunks(prevChunks => prevChunks.filter(chunk => chunk.document_id !== documentId));
      setEmbeddings(prevEmbeddings => prevEmbeddings.filter(emb => emb.document_id !== documentId));
      setIndices(prevIndices => prevIndices.filter(idx => idx.document_id !== documentId));
      
      setLoading(false);
      setError("Document deleted successfully");
      setTimeout(() => setError(null), 3000);
    } catch (error) {
      setError(t('deleteFailed') + ": " + error.message);
      setLoading(false);
      throw error;
    }
  };

  const handleChunkDocument = async (documentId, strategy, chunkSize, overlap) => {
    try {
      const result = await simulateApiCall({
        id: `chunk${chunks.length + 1}`,
        document_id: documentId,
        strategy,
        chunk_size: parseInt(chunkSize),
        overlap: parseInt(overlap),
        total_chunks: Math.floor(Math.random() * 30) + 10
      }, 2000);
      
      setChunks([...chunks, result]);
      return result;
    } catch (error) {
      setError(t('chunkingFailed') + ": " + error.message);
      throw error;
    }
  };

  const handleChunkDelete = async (chunkId) => {
    try {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 500)); 
      
      setChunks(prevChunks => prevChunks.filter(chunk => chunk.id !== chunkId));
      
      setLoading(false);
      setError("Chunk deleted successfully");
      setTimeout(() => setError(null), 3000);
    } catch (error) {
      setError(t('deleteFailed') + ": " + error.message);
      setLoading(false);
      throw error;
    }
  };

  const handleParseDocument = async (documentId, strategy, extractTables, extractImages) => {
    try {
      return await simulateApiCall({
        document_id: documentId,
        parse_id: `parse${Math.floor(Math.random() * 1000)}`,
        strategy,
        extract_tables: extractTables,
        extract_images: extractImages,
        total_sections: Math.floor(Math.random() * 10) + 5,
        total_paragraphs: Math.floor(Math.random() * 50) + 20,
        total_tables: extractTables ? Math.floor(Math.random() * 5) : 0,
        total_images: extractImages ? Math.floor(Math.random() * 8) : 0
      }, 2500);
    } catch (error) {
      setError(t('parsingFailed') + ": " + error.message);
      throw error;
    }
  };

  const handleCreateEmbeddings = async (documentId, provider, model) => {
    try {
      const dimensions = provider === 'openai' ? 1536 : 1024;
      const result = await simulateApiCall({
        document_id: documentId,
        embedding_id: `emb${embeddings.length + 1}`,
        provider,
        model,
        dimensions,
        total_embeddings: Math.floor(Math.random() * 40) + 15
      }, 3000);
      
      setEmbeddings([...embeddings, result]);
      return result;
    } catch (error) {
      setError(t('embeddingFailed') + ": " + error.message);
      throw error;
    }
  };

  const handleEmbeddingDelete = async (embeddingId) => {
    try {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 500)); 
      
      const deletedEmbedding = embeddings.find(emb => emb.embedding_id === embeddingId);
      const documentId = deletedEmbedding ? deletedEmbedding.document_id : null;
      
      setEmbeddings(prevEmbeddings => prevEmbeddings.filter(emb => emb.embedding_id !== embeddingId));
      
      if (documentId) {
        setIndices(prevIndices => prevIndices.filter(idx => idx.document_id !== documentId));
      }
      
      setLoading(false);
      setError("Embedding deleted successfully");
      setTimeout(() => setError(null), 3000);
    } catch (error) {
      setError(t('deleteFailed') + ": " + error.message);
      setLoading(false);
      throw error;
    }
  };

  const handleCreateIndex = async (documentId, vectorDb, collectionName, indexName) => {
    try {
      const result = await simulateApiCall({
        document_id: documentId,
        index_id: `idx${indices.length + 1}`,
        vector_db: vectorDb,
        collection_name: collectionName,
        index_name: indexName,
        version: '1.0',
        total_vectors: Math.floor(Math.random() * 40) + 15
      }, 2500);
      
      setIndices([...indices, result]);
      return result;
    } catch (error) {
      setError(t('indexingFailed') + ": " + error.message);
      throw error;
    }
  };

  const handleIndexDelete = async (indexId) => {
    try {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 500)); 
      
      setIndices(prevIndices => prevIndices.filter(idx => idx.index_id !== indexId));
      
      setLoading(false);
      setError("Index deleted successfully");
      setTimeout(() => setError(null), 3000);
    } catch (error) {
      setError(t('deleteFailed') + ": " + error.message);
      setLoading(false);
      throw error;
    }
  };

  const handleSearch = async (indexId, query, topK, similarityThreshold, minChars) => {
    try {
      const results = [];
      const result = await simulateApiCall({
        search_id: `search${Math.floor(Math.random() * 1000)}`,
        query,
        index_id: indexId,
        top_k: parseInt(topK || 3),
        similarity_threshold: parseFloat(similarityThreshold || 0.7),
        min_chars: parseInt(minChars || 100),
        results
      }, 2000);
      
      setSearchResults(result);
      return result;
    } catch (error) {
      setError(t('searchFailed') + ": " + error.message);
      throw error;
    }
  };

  const handleGenerateText = async (indexId, prompt, provider, model, temperature, maxTokens, imageFile) => {
    try {
      if (activeModule === 'chat') {
        const userTimestamp = new Date().toLocaleString();
        const messageId = `user-${Date.now()}`;
        const userMessage = {
          sender: 'user',
          text: prompt,
          timestamp: userTimestamp,
          id: messageId,
          image: imageFile ? 'loading' : null
        };
        setChatHistory(prev => [...prev, userMessage]);
        if (imageFile) {
          const reader = new FileReader();
          reader.onloadend = () => {
            setChatHistory(prev =>
              prev.map(msg =>
                msg.id === messageId ? { ...msg, image: reader.result } : msg
              )
            );
          };
          reader.onerror = (error) => {
            setChatHistory(prev =>
              prev.map(msg =>
                msg.id === messageId ? { ...msg, image: 'error' } : msg
              )
            );
          };
          reader.readAsDataURL(imageFile);
        }
        setPendingApiCall({ indexId, prompt, provider, model, temperature, maxTokens, imageFile });
      } else {
        setLoading(true);
        setError(null);
        try {
          const payload = {
            index_id: indexId,
            prompt,
            provider,
            model,
            temperature: parseFloat(temperature || 0.7),
            ...(maxTokens ? { max_tokens: parseInt(maxTokens) } : {})
          };
          const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
          const res = await fetch(`${apiBase}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (!res.ok) throw new Error(await res.text());
          const result = await res.json();
          setGeneratedText(result);
        } catch (err) {
          setError(t("generationFailed") + ": " + err.message);
        } finally {
          setLoading(false);
        }
      }
    } catch (error) {
      setError(t("generationFailed") + ": " + error.message);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar 
          activeModule={activeModule} 
          onModuleChange={handleModuleChange} 
        />
        <MainContent 
          activeModule={activeModule}
          documents={documents}
          embeddings={embeddings}
          chunks={chunks}
          indices={indices}
          searchResults={searchResults}
          generatedText={generatedText}
          loading={loading}
          error={error}
          onDocumentUpload={handleDocumentUpload}
          onChunkDocument={handleChunkDocument}
          onParseDocument={handleParseDocument}
          onCreateEmbeddings={handleCreateEmbeddings}
          onCreateIndex={handleCreateIndex}
          onSearch={handleSearch}
          onGenerateText={handleGenerateText}
          onRefreshDocuments={() => setDocuments([...documents])}
          onRefreshIndices={() => setIndices([...indices])}
          onDocumentDelete={handleDocumentDelete}
          onChunkDelete={handleChunkDelete}
          onEmbeddingDelete={handleEmbeddingDelete}
          onIndexDelete={handleIndexDelete}
          chatHistory={chatHistory}
          config={config}
          configLoading={configLoading}
        />
      </div>
    </div>
  );
}

export default App;
