# VerseMind-RAG 配置指南

## 概述

VerseMind-RAG 采用集中式 TOML 配置系统。所有模型、分组、嵌入、向量库等设置均在 `config/config.toml` 统一管理。后端启动时加载该文件，并通过 `/api/config` 接口向前端提供配置，实现全局单一配置源。

## 文件位置

主配置文件：
```
config/config.toml
```
模板示例：
```
config/config.example.toml
```
> **注意：** 仅 `config.example.toml` 应提交到 GitHub，`config.toml` 可能包含敏感信息，应加入 `.gitignore`。

## 配置流程
- **后端**：启动时加载 `config/config.toml`，并通过 `/api/config` 提供给前端。
- **前端**：启动时请求 `/api/config`，用返回的 JSON 渲染模型选择等。
- **更新**：编辑 `config/config.toml` 并重启后端，前端会自动反映新配置。

## config.toml 结构（示例）

### 1. LLM 模型设置
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

### 2. 模型分组（用于前端下拉选择）
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

### 3. 嵌入模型
```toml
[embedding_models]
ollama = [
    { id = "bge-m3:latest", name = "BGE-m3", dimensions = 1024 },
    { id = "BGE-large:latest", name = "BGE-Large", dimensions = 1024 }
]
```

### 4. 向量数据库
```toml
[vector_databases]
faiss = { name = "FAISS", description = "Facebook AI Similarity Search", local = true }
chroma = { name = "Chroma", description = "Chroma Vector Database", local = true }
```

### 5. 应用信息
```toml
[app]
name = "VerseMind-RAG"
version = "1.0.0"
description = "Where Poetry Meets AI"
default_language = "en"
```

## 如何编辑配置
1. 按需编辑 `config/config.toml`。
2. 保存文件。
3. 重启后端服务使配置生效。
4. 前端会自动反映新配置。

## 新增模型的步骤
1. 新增 `[llm.模型key]` 配置段，填写所有必需字段。
2. 在对应 `[model_groups]` 分组数组中添加一项，`config_key` 指向新模型。
3. （可选）如需嵌入模型或向量库，也可补充相关配置。

## 最佳实践
- **切勿将 `config/config.toml` 提交到 GitHub**，请用 `config.example.toml` 作为公开模板。
- **API 密钥、敏感信息不要出现在版本库中**。
- **建议用注释说明每个模型和分组**，便于团队协作。
- **每次修改配置后需重启后端**。
- **编辑后建议用 TOML 校验工具检查语法**，避免启动报错。

## 常见问题排查
- 如果前端只显示默认模型，检查后端日志和 `config.toml` 是否有效。
- 如果 `/api/config` 返回 500，检查配置字段是否缺失或格式错误。
- 可参考 `config.example.toml` 作为标准结构。

## 示例模板
请参考 `config/config.example.toml`，可直接复制修改。
