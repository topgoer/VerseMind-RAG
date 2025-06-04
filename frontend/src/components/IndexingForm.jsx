const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedEmbedding || !indexType) {
      // console.log("Missing required fields:", { selectedEmbedding, indexType });
      return;
    }
    
    try {
      // console.log("Starting index creation with:", { selectedEmbedding, indexType });
      // Find the document_id associated with the selected embedding_id
      const embeddingInfo = embeddings.find(emb => emb.embedding_id === selectedEmbedding);
      // console.log("Found embedding info:", embeddingInfo);
      
      if (!embeddingInfo) {
        throw new Error("Selected embedding not found");
      }      // Use a default collection name based on the document ID
      // Note: In a complete implementation, we would have a collectionName state/prop
      const collectionName = ''; // This should be state variable in a complete component
        // console.log("Calling onCreateIndex with:", {
      //   document_id: embeddingInfo.document_id,
      //   index_type: indexType,
      //   embedding_id: selectedEmbedding,
      //   collection_name: collectionName || `col_${embeddingInfo.document_id.substring(0, 10)}`
      // });
      
      const finalCollectionName = collectionName || `col_${embeddingInfo.document_id.substring(0, 10)}`;
      const result = await onCreateIndex(embeddingInfo.document_id, indexType, selectedEmbedding, finalCollectionName);
      // console.log("Index creation result:", result);
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