/**
 * Model configuration for VerseMind-RAG
 * This file centralizes all model definitions and can be extended
 * without modifying component code
 */

// Default models configuration
export const defaultModels = [
  // DeepSeek models
  { id: 'deepseek-chat', name: 'DeepSeek Chat', provider: 'deepseek', type: 'chat', aliases: ['deepseek-v3'] },
  { id: 'deepseek-reasoner', name: 'DeepSeek Reasoner', provider: 'deepseek', type: 'chat', aliases: ['deepseek-r1', 'deepseek-r1:14b'] },
  
  // OpenAI models
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai', type: 'chat' },
  { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'openai', type: 'chat' },
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai', type: 'chat' },
  
  // Ollama models with metadata
    { id: 'gemma3:4b', name: 'Gemma 3 4B', provider: 'ollama', size: '3.3 GB', modified: '6 weeks ago', type: 'chat', aliases: ['gemma3'] },
  { id: 'phi4', name: 'Phi-4', provider: 'ollama', size: '9.1 GB', modified: '3 months ago', type: 'chat' },
  { id: 'llava:v1.6', name: 'Llava v1.6', provider: 'ollama', size: '4.7 GB', modified: '4 months ago', type: 'chat', aliases: ['llava'] },
  { id: 'wizard-math:latest', name: 'Wizard Math', provider: 'ollama', size: '4.1 GB', modified: '4 months ago', type: 'chat', aliases: ['wizard-math'] },
  { id: 'qwen2.5:7b', name: 'Qwen 2.5 7B', provider: 'ollama', size: '4.7 GB', modified: '4 months ago', type: 'chat', aliases: ['qwen2.5'] },
  { id: 'wizardcoder:latest', name: 'Wizard Coder', provider: 'ollama', size: '3.8 GB', modified: '4 months ago', type: 'chat', aliases: ['wizardcoder'] },
  { id: 'openhermes:latest', name: 'Open Hermes', provider: 'ollama', size: '4.1 GB', modified: '4 months ago', type: 'chat', aliases: ['openhermes'] },
  { id: 'mistral:latest', name: 'Mistral', provider: 'ollama', size: '4.1 GB', modified: '5 months ago', type: 'chat', aliases: ['mistral'] },
  { id: 'llama3.2-vision:latest', name: 'Llama 3.2 Vision', provider: 'ollama', size: '7.9 GB', modified: '5 months ago', type: 'chat', aliases: ['llama3.2-vision'] },
  { id: 'codellama:latest', name: 'Code Llama', provider: 'ollama', size: '3.8 GB', modified: '6 months ago', type: 'chat', aliases: ['codellama'] },
  { id: 'deepseek-r1:14b', name: 'DeepSeek Reasoner (Ollama)', provider: 'ollama', size: '6.8 GB', type: 'chat', displayNameOverride: true },
  
  // Embedding models - separate from chat models
  { id: 'bge-large', name: 'BGE-large', provider: 'ollama', type: 'embedding' },
  { id: 'bge-m3', name: 'Bge-m3', provider: 'ollama', type: 'embedding' }
];

// Function to fetch Ollama models dynamically
export async function fetchOllamaModels() {
  try {
    // Only use backend API (which handles CORS) to fetch models
    const backendUrl = import.meta.env.VITE_API_BASE_URL || '';
    let response;
    
    try {
      response = await fetch(`${backendUrl}/api/generate/models`);
      if (response.ok) {
        const data = await response.json();
        if (data && data.providers && data.providers.ollama && data.providers.ollama.models) {
          return data.providers.ollama.models.map(model => ({
            id: model.id,
            name: model.description || formatModelName(model.id),
            provider: 'ollama',
            type: isEmbeddingModel(model.id) ? 'embedding' : 'chat'
          }));
        }
      }
      // If we get here but don't have models yet, return empty array
      console.warn('Backend API returned success but no Ollama models were found');
      return [];
    } catch (backendError) {
      console.error('Failed to fetch models from backend API:', backendError);
      return [];
    }
  } catch (error) {
    console.error('Error fetching Ollama models:', error);
    return [];
  }
}

// Helper function to format model name for display
function formatModelName(modelName) {
  // Handle DeepSeek models specially
  if (modelName.toLowerCase().includes('deepseek')) {
    if (modelName.toLowerCase().includes('r1')) {
      return 'DeepSeek Reasoner';
    }
    return 'DeepSeek Chat';
  }
  
  // Remove version tags like ':latest', ':7b', etc.
  const baseName = modelName.split(':')[0];
  
  // Properly capitalize model name
  return baseName.charAt(0).toUpperCase() + baseName.slice(1);
}

// Helper function to identify embedding models by name
function isEmbeddingModel(modelName) {
  const embeddingModelPatterns = [
    /bge[-\s]?m3/i, 
    /bge[-\s]?large/i,
    /all-mini/i,
    /all-MiniLM/i,
    /e5-/i,
    /embedding/i,
    /embed-/i
  ];
  
  return embeddingModelPatterns.some(pattern => pattern.test(modelName));
}

// Get models from environment variables if available
export function getEnvModels() {
  try {
    const envModels = import.meta.env.VITE_MODELS;
    if (envModels) {
      return JSON.parse(envModels);
    }
  } catch (error) {
    console.error('Error parsing VITE_MODELS:', error);
  }
  return null;
}

// Install an Ollama model - will be downloaded by Ollama in the background
export async function installOllamaModel(modelName) {
  try {
    // Always use the backend API for installation to avoid CORS issues
    const backendUrl = import.meta.env.VITE_API_BASE_URL || '';
    const response = await fetch(`${backendUrl}/api/generate/install-model`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ model_name: modelName }),
    });
    
    const result = await response.json();
    
    return {
      success: result.success !== false,
      message: result.message || `Started downloading model: ${modelName}`
    };
  } catch (error) {
    console.error('Error installing Ollama model:', error);
    return {
      success: false,
      message: `Failed to install model: ${error.message}`
    };
  }
}

// Get all available models, with priority:
// 1. Environment variable models
// 2. Dynamic Ollama models (if fetchDynamic is true)
// 3. Default models
export async function getAvailableModels(fetchDynamic = true, modelType = null) {
  // Check for environment variable configuration first
  const envModels = getEnvModels();
  if (envModels) {
    return modelType ? envModels.filter(m => m.type === modelType) : envModels;
  }
  
  let models = [];
  
  if (fetchDynamic) {
    try {
      // Try to fetch Ollama models dynamically
      const ollamaModels = await fetchOllamaModels();
      
      if (ollamaModels.length > 0) {
        // Get non-Ollama models from default list
        const staticNonOllamaModels = defaultModels.filter(model => model.provider !== 'ollama');
        
        // Create a map of model name -> model to deduplicate
        const modelMap = new Map();
        
        // Add all non-Ollama models to the map
        staticNonOllamaModels.forEach(model => {
          modelMap.set(model.id.toLowerCase(), model);
        });
        
        // Add all Ollama models, avoiding duplicates with the default model list
        ollamaModels.forEach(model => {
          const baseId = model.id.split(':')[0].toLowerCase();
          
          // Skip if this model should be represented by a default model instead
          let shouldSkip = false;
          let defaultMatch = null;
          
          for (const defaultModel of defaultModels) {
            // Check if this Ollama model matches one of our default models by ID or alias
            if (defaultModel.id.toLowerCase() === model.id.toLowerCase() || 
                (defaultModel.aliases && 
                 (defaultModel.aliases.includes(baseId) || 
                  defaultModel.aliases.includes(model.id.toLowerCase())))) {
                  
              shouldSkip = true;
              defaultMatch = defaultModel;
              break;
            }
          }
          
          if (shouldSkip && defaultMatch) {
            // If the model should be skipped but it's actually an Ollama model with a display override,
            // we should still include it with the preferred display name
            if (defaultMatch.provider === 'ollama' && defaultMatch.displayNameOverride) {
              modelMap.set(model.id.toLowerCase(), defaultMatch);
            }
          } else {
            modelMap.set(model.id.toLowerCase(), model);
          }
        });
        
        // Convert map back to array
        models = Array.from(modelMap.values());
      } else {
        models = defaultModels;
      }
    } catch (error) {
      console.error('Error getting dynamic models:', error);
      models = defaultModels;
    }
  } else {
    // Fall back to default models
    models = defaultModels;
  }
  
  // Filter by model type if specified
  return modelType ? models.filter(m => m.type === modelType) : models;
}

// Group models by provider for UI organization
export function groupModelsByProvider(models) {
  return models.reduce((grouped, model) => {
    const provider = model.provider;
    if (!grouped[provider]) {
      grouped[provider] = [];
    }
    grouped[provider].push(model);
    return grouped;
  }, {});
}