let configCache = null;
let loadingPromise = null; // Track ongoing requests

let defaultConfig = {
  model_groups: {
    ollama: [
      { id: "llama3", name: "Llama 3" },
      { id: "gemma3:4b", name: "Gemma 3 4B" },
      { id: "deepseek-r1:14b", name: "DeepSeek R1 14B" },
      { id: "phi4", name: "Phi-4" },
      { id: "mistral", name: "Mistral" }
    ],
    openai: [
      { id: "gpt-4o", name: "GPT-4o" },
      { id: "gpt-4-turbo", name: "GPT-4 Turbo" },
      { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo" }
    ],
    deepseek: [
      { id: "deepseek-chat", name: "DeepSeek Chat" }
    ]
  },
  embedding_models: {
    ollama: [
      { id: "bge-large", name: "BGE Large", dimensions: 1024 },
      { id: "bge-m3", name: "BGE M3", dimensions: 1024 }
    ],
    openai: [
      { id: "text-embedding-3-small", name: "Text Embedding 3 Small", dimensions: 1536 },
      { id: "text-embedding-3-large", name: "Text Embedding 3 Large", dimensions: 3072 }
    ],
    deepseek: [
      { id: "deepseek-embedding", name: "DeepSeek Embedding", dimensions: 1024 }
    ]
  },
  vector_databases: {
    faiss: {
      name: "FAISS",
      description: "Facebook AI Similarity Search",
      local: true
    },
    chroma: {
      name: "Chroma",
      description: "Chroma Vector Database",
      local: true
    }
  }
};

export const loadConfig = async () => {
  // Return cached config if available
  if (configCache) {
    return configCache;
  }

  // If there's already a request in progress, return that promise
  // This prevents multiple simultaneous API calls
  if (loadingPromise) {
    return loadingPromise;
  }

  try {
    // Create and store the loading promise
    loadingPromise = (async () => {
      console.log('[ConfigLoader] Requesting backend /api/config ...');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/config`);
      if (!response.ok) {
        throw new Error('Failed to fetch backend config: ' + response.statusText);
      }
      const configData = await response.json();
      console.log('[ConfigLoader] Backend config loaded:', configData);
      configCache = configData;
      return configData;
    })();

    // Return the result of the loading promise
    return await loadingPromise;
  } catch (error) {
    console.error('[ConfigLoader] Error loading backend config:', error);
    console.warn('[ConfigLoader] Using default config due to loading error.');
    configCache = defaultConfig;
    return defaultConfig;
  } finally {
    // Clear the loading promise when done (success or failure)
    loadingPromise = null;
  }
};

// Helper function to safely get config values
export const getConfigValue = (config, key, defaultValue = null) => {
  if (!config) return defaultValue;
  
  const keys = key.split('.');
  let value = config;
  
  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k];
    } else {
      return defaultValue;
    }
  }
  
  return value;
};
