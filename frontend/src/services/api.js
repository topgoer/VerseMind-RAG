// API service functions for direct API access
// This allows components to directly access the backend API without relying on parent component state

/**
 * Fetch embeddings directly from the backend API
 * @param {string} documentId - Optional document ID to filter embeddings
 * @returns {Promise<Array>} - Array of embeddings
 */
export async function fetchEmbeddingsDirectly(documentId = null) {
  try {    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
    const url = documentId 
      ? `${apiBase}/api/embeddings/list?document_id=${encodeURIComponent(documentId)}`
      : `${apiBase}/api/embeddings/list`;
    
    // console.log(`[API Service] Fetching embeddings directly from: ${url}`);
    const response = await fetch(url);
    
    if (!response.ok) {
      let errorText;
      try {
        const errorData = await response.json();
        errorText = JSON.stringify(errorData);
      } catch (e) {
        errorText = await response.text();
      }
      console.error('[API Service] Failed to fetch embeddings:', response.status, errorText);
      throw new Error(`Failed to fetch embeddings${documentId ? ` for document ${documentId}` : ''}. Status: ${response.status}`);
    }
      const data = await response.json();
    // console.log(`[API Service] Successfully fetched ${data.length} embeddings directly`);
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.error('[API Service] Error fetching embeddings directly:', err);
    throw err;
  }
}

/**
 * Fetch vector indices directly from the backend API
 * @returns {Promise<Array>} - Array of vector indices
 */
export async function fetchIndicesDirectly() {
  try {    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8200';
    const url = `${apiBase}/api/indices/list`;
    
    // console.log(`[API Service] Fetching indices directly from: ${url}`);
    const response = await fetch(url);
    
    if (!response.ok) {
      let errorText;
      try {
        const errorData = await response.json();
        errorText = JSON.stringify(errorData);
      } catch (e) {
        errorText = await response.text();
      }
      console.error('[API Service] Failed to fetch indices:', response.status, errorText);
      throw new Error(`Failed to fetch indices. Status: ${response.status}`);
    }
      const data = await response.json();
    // console.log(`[API Service] Successfully fetched ${data.length} indices directly`);
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.error('[API Service] Error fetching indices directly:', err);
    throw err;
  }
}
