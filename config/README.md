# VerseMind-RAG 配置系统文档

## 概述

VerseMind-RAG 系统使用基于 TOML 的集中式配置系统，允许用户轻松自定义和扩展系统功能，无需修改代码。**所有模型、分组、参数等配置均以 `config/config.toml` 为唯一权威来源**，前端通过后端 API 动态获取配置。

## 配置文件位置

配置文件位于项目根目录下的 `config` 文件夹中：

```
versemind-rag/
├── config/
│   └── config.toml  # 主配置文件
```

## 配置流转与前后端协作

- **后端**：启动时加载 `config/config.toml`，并通过 `/api/config`（或 `/api/model-groups` 等）API 向前端提供完整的模型分组、参数、嵌入模型、向量数据库等配置。
- **前端**：不再读取 `public/config.toml`，而是通过 `loadConfig()` 直接请求后端 `/api/config`，动态渲染模型选择、参数等界面，确保与后端配置完全一致。
- **配置变更**：只需修改 `config/config.toml`，重启后端即可，前端自动同步。

## 配置文件结构

`config.toml` 文件包含以下主要部分：

1. **默认 LLM 配置**：系统默认使用的大语言模型设置
2. **模型配置**：各种 LLM 模型的详细配置
3. **模型分组**：按提供商分组的模型列表（用于前端下拉选择）
4. **嵌入模型配置**：用于向量嵌入的模型配置
5. **向量数据库配置**：支持的向量数据库设置
6. **应用配置**：应用程序的基本设置

## 配置示例

```toml
# 默认 LLM 配置
[llm]
api_type = "ollama"
model = "gemma3:4b"
base_url = "http://localhost:11434"
api_key = "ollama"
max_tokens = 4096
temperature = 0.7

# Ollama 本地模型配置
[llm.deepseek_ollama]
api_type = "ollama"
model = "deepseek-r1:14b"
base_url = "http://localhost:11434"
api_key = "ollama"
max_tokens = 4096
temperature = 0.7

# 模型分组配置
[model_groups]
ollama = [
    { id = "llama3", name = "Llama 3", config_key = "llm.llama3" },
    { id = "gemma3:4b", name = "Gemma 3 4B", config_key = "llm.gemma3" },
    # 更多模型...
]

# 嵌入模型配置
[embedding_models]
ollama = [
    { id = "bge-large", name = "BGE Large", dimensions = 1024 }
]

# 向量数据库配置
[vector_databases]
faiss = {
    name = "FAISS",
    description = "Facebook AI Similarity Search",
    local = true
}
```

## 配置项说明

### LLM 模型配置

每个 LLM 模型配置包含以下字段：

| 字段 | 描述 | 示例值 |
|------|------|--------|
| api_type | API 类型 | "ollama", "openai", "azure" |
| model | 模型标识符 | "gemma3:4b", "gpt-4o" |
| base_url | API 基础 URL | "http://localhost:11434" |
| api_key | API 密钥 | "YOUR_API_KEY" |
| max_tokens | 最大生成令牌数 | 4096 |
| temperature | 生成温度 | 0.7 |
| api_version | API 版本（可选） | "2024-08-01-preview" |

### 模型分组配置

模型分组配置用于在 UI 中组织模型选择器：

```toml
[model_groups]
provider_name = [
    { id = "model_id", name = "显示名称", config_key = "llm.model_config_key" },
    # 更多模型...
]
```

### 嵌入模型配置

嵌入模型配置用于向量嵌入功能：

```toml
[embedding_models]
provider_name = [
    { id = "model_id", name = "显示名称", dimensions = 1024 },
    # 更多模型...
]
```

### 向量数据库配置

向量数据库配置定义了系统支持的向量存储：

```toml
[vector_databases]
database_id = {
    name = "显示名称",
    description = "数据库描述",
    local = true  # 是否为本地数据库
}
```

## 如何修改配置

1. 打开 `config/config.toml` 文件
2. 根据需要修改配置项
3. 保存文件
4. 重启后端服务以应用更改（前端自动同步）

## 添加新模型

要添加新的 LLM 模型，请按照以下步骤操作：

1. 在适当的部分添加模型配置：

```toml
[llm.new_model_key]
api_type = "provider_type"
model = "model_id"
base_url = "api_url"
api_key = "api_key"
max_tokens = 4096
temperature = 0.7
```

2. 将模型添加到相应的模型分组中：

```toml
[model_groups]
provider_name = [
    # 现有模型...
    { id = "new_model_id", name = "新模型显示名称", config_key = "llm.new_model_key" }
]
```

## 最佳实践

1. **只维护 config/config.toml**：不要再维护 public/config.toml，所有配置以后端为准。
2. **保护 API 密钥**：在生产环境中，不要在配置文件中存储实际的 API 密钥。考虑使用环境变量或安全的密钥管理系统。
3. **备份配置**：在进行重大更改前，备份您的配置文件。
4. **验证配置**：修改配置后，验证所有功能是否正常工作。
5. **注释**：使用注释（以 `#` 开头）来解释复杂的配置项。
6. **组织结构**：保持配置文件的组织结构清晰，使用空行和注释来分隔不同的部分。

## 故障排除

如果您在使用配置系统时遇到问题，请检查：

1. TOML 语法是否正确（确保没有缺少引号、括号等）
2. 配置文件是否位于正确的位置
3. 后端日志和前端控制台中是否有配置相关的错误消息
4. `/api/config` 是否能正确返回配置内容

## 配置系统技术实现

- 后端使用 `toml` 库解析 `config/config.toml`，并通过 `/api/config` 提供配置数据。
- 前端组件通过 `configLoader.js` 的 `loadConfig()` 函数请求 `/api/config`，动态加载配置。
- 配置加载器实现了缓存机制，以避免重复加载配置文件。

```javascript
// 前端示例
import { loadConfig } from '../../utils/configLoader';

useEffect(() => {
  const fetchConfig = async () => {
    const configData = await loadConfig();
    setConfig(configData);
    // 使用配置数据...
  };
  fetchConfig();
}, []);
```
