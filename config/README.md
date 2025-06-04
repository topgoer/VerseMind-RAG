[![CI](https://github.com/topgoer/VerseMind-RAG/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/topgoer/VerseMind-RAG/actions/workflows/ci.yml)

# VerseMind-RAG Configuration Guide

## Overview

VerseMind-RAG uses a centralized TOML-based configuration system. All model, group, embedding, and vector database settings are managed in `config/config.toml`. The backend loads this file and exposes configuration to the frontend via the `/api/config` endpoint, ensuring a single source of truth for the entire system.

## File Location

Configuration file:
```
config/config.toml
```
Template/example:
```
config/config.example.toml
```
> **Note:** Only `config.example.toml` should be committed to GitHub. `config.toml` may contain sensitive keys and should be listed in `.gitignore`.

## Configuration Flow
- **Backend**: Loads `config/config.toml` at startup and serves it via `/api/config`.
- **Frontend**: Fetches `/api/config` and uses the returned JSON to render model selectors and other options.
- **Update**: Edit `config/config.toml` and restart the backend to apply changes. The frontend will reflect updates automatically.

## config.toml Structure (Example)

### 1. LLM Model Settings
```toml
[llm]
api_type = "ollama"
model = "gemma3:4b"
base_url = "http://localhost:11434"
api_key = "ollama"
max_tokens = 4096
temperature = 0.7

[llm.deepseek_ollama]
api_type = "ollama"
model = "deepseek-r1:8b"
base_url = "http://localhost:11434"
api_key = "ollama"
max_tokens = 4096
temperature = 0.7

[llm.deepseek_v3]
api_type = "openai"
model = "deepseek-chat"
base_url = "https://api.deepseek.com/v1"
api_key = "YOUR_API_KEY"
max_tokens = 4096
temperature = 0.7

[llm.deepseek_r1]
api_type = "openai"
model = "deepseek-reasoner"
base_url = "https://api.deepseek.com/v1"
api_key = "YOUR_API_KEY"
max_tokens = 4096
temperature = 0.7

[llm.llama3_2-vision]
api_type = "ollama"
model = "llama3.2-vision:latest"
base_url = "http://localhost:11434"
api_key = "ollama"
max_tokens = 4096
temperature = 0.7
api_version = ""

[llm.gemma3]
api_type = "ollama"
model = "gemma3:4b"
base_url = "http://localhost:11434"
api_key = "ollama"
max_tokens = 4096
temperature = 0.7

[llm.phi4]
api_type = "ollama"
model = "phi4:latest"
base_url = "http://localhost:11434"
api_key = "ollama"
max_tokens = 4096
temperature = 0.7

[llm.qwen3_8b]
api_type = "ollama"
model = "qwen3:8b"
base_url = "http://localhost:11434"
api_key = "ollama"
max_tokens = 4096
temperature = 0.7

[llm.Qwen_siliconflow]
model = "Qwen/QwQ-32B"
base_url = "https://api.siliconflow.cn/v1"
api_key = "YOUR_API_KEY"
max_tokens = 8192   
temperature = 0.0
api_type = "api"

[llm.gpt_4o]
api_type = "openai"
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "YOUR_API_KEY"
max_tokens = 8192
temperature = 0.7

[llm.gpt_3_5_turbo]
api_type = "openai"
model = "gpt-3.5-turbo"
base_url = "https://api.openai.com/v1"
api_key = "YOUR_API_KEY"
max_tokens = 4096
temperature = 0.7
```

### 2. Model Groups (for UI selection)
```toml
[model_groups]
ollama = [
    { id = "qwen3:8b", name = "Qwen3 8b", config_key = "llm.qwen3_8b" },    
    { id = "gemma3:4b", name = "Gemma3 4b", config_key = "llm.gemma3" },
    { id = "deepseek-r1:8b", name = "DeepSeek R1 8b", config_key = "llm.deepseek_ollama" },
    { id = "phi4", name = "Phi-4", config_key = "llm.phi4" },
    { id = "mistral:latest", name = "Mistral", config_key = "llm.mistral" },    
    { id = "llama3.2-vision", name = "Llama 3.2 Vision", config_key = "llm.llama3_2_vision" }
]
openai = [
    { id = "gpt-4o", name = "GPT-4o", config_key = "llm.gpt_4o" },
    { id = "gpt-3.5-turbo", name = "GPT-3.5 Turbo", config_key = "llm.gpt_3_5_turbo" }
]
deepseek = [
    { id = "deepseek-chat", name = "DeepSeek Chat", config_key = "llm.deepseek_v3" },
    { id = "deepseek-reasoner", name = "DeepSeek-r1", config_key = "llm.deepseek_r1" }
]
siliconflow = [
    { id = "Qwen/QwQ-32B", name = "Qwen-32b", config_key = "llm.Qwen_siliconflow" }
]
```

### 3. Embedding Models
```toml
[embedding_models]
ollama = [
    { id = "bge-m3:latest", name = "BGE-m3", dimensions = 1024 },
    { id = "BGE-large:latest", name = "BGE-Large", dimensions = 1024 }
]
```

### 4. Vector Databases
```toml
[vector_databases]
faiss = { name = "FAISS", description = "Facebook AI Similarity Search", local = true }
chroma = { name = "Chroma", description = "Chroma Vector Database", local = true }
```

### 5. App Info
```toml
[app]
name = "VerseMind-RAG"
version = "1.0.0"
description = "Where Poetry Meets AI"
default_language = "en"
```

## How to Edit Configuration
1. Edit `config/config.toml` as needed.
2. Save the file.
3. Restart the backend server for changes to take effect.
4. The frontend will automatically reflect the new configuration.

## Adding a New Model
1. Add a new `[llm.model_key]` section with all required fields.
2. Add an entry to the appropriate `[model_groups]` array, referencing the new model's `config_key`.
3. (Optional) Add embedding model or vector DB settings if needed.

## Best Practices
- **Never commit `config/config.toml` to GitHub**. Use `config.example.toml` as a public template.
- **Keep API keys and secrets out of version control**.
- **Document each model and group** with comments for clarity.
- **Restart backend after any config change**.
- **Validate TOML syntax** to avoid backend startup errors.

## Troubleshooting
- If the frontend shows only default models, check for errors in the backend log and ensure `config.toml` is valid.
- If `/api/config` returns a 500 error, check for missing or malformed config fields.
- Use the example file as a reference for correct structure.

## Example Template
See `config/config.example.toml` for a ready-to-copy template.

## License

This project is licensed under the MIT License - see the LICENSE file for details.