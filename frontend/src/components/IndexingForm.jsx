const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedEmbedding || !indexType) {
      console.log("Missing required fields:", { selectedEmbedding, indexType });
      return;
    }
    
    try {
      console.log("Starting index creation with:", { selectedEmbedding, indexType });
      // Find the document_id associated with the selected embedding_id
      const embeddingInfo = embeddings.find(emb => emb.embedding_id === selectedEmbedding);
      console.log("Found embedding info:", embeddingInfo);
      
      if (!embeddingInfo) {
        throw new Error("Selected embedding not found");
      }
      
      console.log("Calling onCreateIndex with:", {
        document_id: embeddingInfo.document_id,
        index_type: indexType,
        embedding_id: selectedEmbedding
      });
      
      const result = await onCreateIndex(embeddingInfo.document_id, indexType, selectedEmbedding);
      console.log("Index creation result:", result);
      setIndexResult(result);
    } catch (err) {
      // 错误已在 App.jsx 中处理
      console.error("Indexing failed in module:", err);
      console.error("Error details:", { 
        message: err.message, 
        stack: err.stack,
        response: err.response ? {
          status: err.response.status,
          data: err.response.data
        } : 'No response object'
      });
    }
  };