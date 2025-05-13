# VerseMind-RAG

**诗意与智慧的交融**

[English](README.md) | [简体中文](README_CN.md)

VerseMind-RAG 是一个文档智能与语义生成系统，提供完整的 RAG（检索增强生成）解决方案，支持文档加载、分块、解析、向量嵌入、索引、语义搜索与文本生成。

## 功能特点

- **文档处理**：加载、分块、解析文档内容
- **向量嵌入**：生成语义向量用于检索
- **语义搜索**：基于自然语言查询检索相关内容
- **文本生成**：调用先进大模型生成回复
- **模块化设计**：多模型、多向量库灵活扩展
- **动态模型配置**：集中式模型管理，前后端一致

## 系统架构

- **前端**：React + Vite + TailwindCSS
- **后端**：FastAPI + Python 服务
- **存储**：文件系统 + FAISS/Chroma 向量数据库
- **模型**：Ollama（本地）+ DeepSeek/OpenAI API

## 快速开始

### 前置条件

- Node.js 18+（前端）
- Python 3.12.9（后端，推荐用 Conda）
- Conda（或 Miniconda/Anaconda）
- SWIG（Faiss 依赖，`conda install -c anaconda swig`）
- Ollama（可选，本地模型支持）

### 安装步骤

1. 克隆仓库：
   ```bash
   git clone https://github.com/topgoer/VerseMind-RAG.git
   cd VerseMind-RAG
   ```

2. 创建 Conda 环境：
   ```bash
   # 创建并激活环境
   conda create -n versemind-rag python=3.12.9
   conda activate versemind-rag
   ```

3. 安装前端依赖：
   ```bash
   cd frontend
   npm install
   ```

4. 安装后端依赖（选择一种方式）：

   **方式 A：使用 pip 与 requirements.txt**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

   **方式 B：使用 Poetry**
   ```bash
   cd backend
   # 如果还没安装 Poetry，先执行
   # pip install poetry
   poetry install
   ```

   **方式 C：使用 uv (更快的 Python 包安装工具)**
   ```bash
   cd backend
   # 如果还没安装 uv，先执行
   # pip install uv
   uv pip install -r requirements.txt
   ```

5. 配置环境：
   ```bash
   # 基于示例创建配置文件
   cp config/config.example.toml config/config.toml
   # 编辑 config.toml 文件设置 API 密钥和偏好
   ```

### 启动项目

1. **启动后端：**
   ```bash
   # 使用便捷脚本 (Windows)：
   start-backend.bat
   
   # 使用便捷脚本 (macOS/Linux)：
   chmod +x ./start-backend.sh  # 使脚本可执行（仅首次需要）
   ./start-backend.sh
   
   # 或手动启动：
   cd backend
   conda activate versemind-rag  # 或你的虚拟环境
   uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload
   ```
   
   后端将可在以下地址访问:
   - API 端点: http://localhost:8200
   - API 文档: http://localhost:8200/docs

2. **启动前端：**
   ```bash
   # 开发模式（热重载）：
   cd frontend
   npm run dev
   
   # 或使用便捷脚本 (Windows)：
   start-frontend.bat dev
   
   # 或使用便捷脚本 (macOS/Linux)：
   chmod +x ./start-frontend.sh  # 使脚本可执行（仅首次需要）
   ./start-frontend.sh dev
   ```
   
   ```bash
   # 生产模式：
   cd frontend
   npm run build
   npm run preview
   
   # 或使用便捷脚本 (Windows)：
   start-frontend.bat
   
   # 或使用便捷脚本 (macOS/Linux)：
   chmod +x ./start-frontend.sh  # 使脚本可执行（仅首次需要）
   ./start-frontend.sh
   ```

3. **访问应用：**
   - 开发模式: http://localhost:3200
   - 生产预览: http://localhost:4173

### 使用 Ollama 本地模型

VerseMind-RAG 可以通过 [Ollama](https://ollama.ai) 使用本地 AI 模型进行文本生成和嵌入，这样可以：
- 通过本地处理数据保持数据隐私
- 消除 API 成本和速率限制
- 提供离线功能

**设置步骤：**

1. 从 [ollama.ai](https://ollama.ai) 安装 Ollama

2. 拉取你想使用的模型：
   ```bash
   # 拉取嵌入模型（至少选择一个）
   ollama pull bge-m3        # 较小，更快的嵌入模型
   ollama pull bge-large     # 较大，更精确的嵌入模型
   
   # 拉取生成模型（根据你的硬件选择合适的模型）
   ollama pull gemma3:4b     # 较小，更快的模型（4B 参数）
   ollama pull deepseek-r1:14b # 更高质量，需要更多内存（14B 参数）
   ollama pull phi4          # 微软最新模型
   ollama pull mistral       # 性能/资源良好平衡
   ollama pull llama3.2-vision # 用于图像理解功能
   ```

3. 在启动 VerseMind-RAG 前确保 Ollama 在后台运行

4. 在 VerseMind-RAG 界面中，从模型下拉菜单中选择你喜欢的模型

### 环境配置

应用通过 `config/config.toml` 进行配置。你需要复制并修改示例配置文件：

```bash
# 复制示例配置
cp config/config.example.toml config/config.toml

# 根据需要编辑 config.toml 文件
# 对于 Ollama 用户，默认设置应该可以直接使用
# 对于 API 模型（OpenAI, DeepSeek），你需要添加你的 API 密钥
```

基本配置选项：

```toml
# 主要 LLM 配置 - 选择你的默认模型
[llm]
api_type = "ollama"  # 使用 "ollama" 对应本地模型，"openai" 对应 OpenAI/DeepSeek API
model = "gemma3:4b"  # 你偏好的模型
base_url = "http://localhost:11434"  # Ollama API URL（默认）

# 服务器设置
[server]
host = "0.0.0.0"
port = 8200

# 向量数据库设置
[vector_store]
type = "faiss"  # 选项: "faiss", "chroma"
persist_directory = "./storage/vector_db"
```

更多配置选项请查看 `config/config.example.toml` 文件。

## 高级使用

### 自定义模型配置

VerseMind-RAG 允许您通过 `config/config.toml` 文件自定义模型。您可以配置：

- 具有不同维度和提供商的多个嵌入模型
- 具有特定参数（温度、最大令牌等）的自定义生成模型
- 不同 AI 服务的特定配置

具体示例请参考 `config/config.example.toml` 中的模型配置部分。

### 向量数据库优化

VerseMind-RAG 支持多种向量数据库后端来存储和检索文档嵌入：

- **FAISS**：针对高性能向量相似度搜索进行优化
  - 适用于大规模数据集（百万级向量）
  - 多种索引类型（Flat、HNSW32、HNSW64）
  - 多种距离度量方式（余弦相似度、L2、内积）

- **Chroma**：具有丰富元数据筛选功能的向量数据库
  - 强大的元数据过滤能力
  - 易用的 API 和简单的配置
  - 适用于复杂的文档检索需求

配置通过 `config/config.toml` 文件进行管理，结构如下：

```toml
[vector_store]
type = "faiss"  # 选项: "faiss", "chroma"
persist_directory = "./storage/vector_db"

[vector_store.faiss]
index_type = "HNSW32"  # 选项: "Flat", "HNSW32", "HNSW64"
metric = "cosine"      # 选项: "cosine", "l2", "ip"

[vector_store.chroma]
collection_name = "versemind_docs"
distance_function = "cosine"  # 选项: "cosine", "l2", "ip"
```

有关索引类型、距离度量和性能调优的详细配置选项，请参阅[用户指南](./docs/user_guide.md#向量数据库配置)。

### 高级文档处理

VerseMind-RAG 提供灵活的文档处理配置，可以调整以适应不同的文档类型和用例。

有关详细的配置选项，请参阅配置示例文件（`config/config.example.toml`）。

## 如何使用 VerseMind-RAG

VerseMind-RAG 提供完整的文档处理和检索流程：

1. **上传文档**：通过 UI 上传文档
2. **处理文档**：（分块、解析、嵌入、索引）
3. **查询文档**：通过聊天界面
4. **查看结果**：带有源引用和可视化

有关详细使用说明、示例查询和最佳实践，请参阅[用户指南](./docs/user_guide.md)。





## 文档

详细文档请参考：
- [系统架构设计](./docs/VerseMind-RAG%20系统架构设计.md)
- [用户指南](./docs/user_guide.md)

## 贡献

欢迎为 VerseMind-RAG 做出贡献！以下是贡献方式：

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

请确保您的代码在提交前通过所有测试。

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](./LICENSE)。

## 致谢

- [React](https://reactjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Ollama](https://ollama.ai/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Chroma](https://www.trychroma.com/)
