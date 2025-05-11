# VerseMind-RAG

**诗意与智慧的交融**

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
- **后端**：FastAPI + Python
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
   git clone https://github.com/yourusername/VerseMind-RAG.git
   cd VerseMind-RAG
   ```

2. 创建 Conda 环境并安装依赖：
   ```bash
   conda create -n versemind-rag python=3.12.9
   conda activate versemind-rag
   conda install -c anaconda swig
   conda install -c pytorch faiss-cpu
   ```

3. 安装前端依赖：
   ```bash
   cd frontend
   npm install
   ```

4. 安装后端依赖：
   ```bash
   cd ../backend
   pip install -r requirements.txt
   ```

5. 配置环境变量：
   ```bash
   cd frontend
   touch .env
   ```
   .env 内容示例：
   ```
   VITE_API_BASE_URL=http://localhost:8200
   VITE_OLLAMA_BASE_URL=http://localhost:11434
   VITE_PORT=4173
   VITE_USE_REAL_API=true
   ```

### 启动项目

1. **启动后端（推荐）**：
   ```bash
   start-backend.bat
   ```
   > 自动激活 conda 环境并启动 FastAPI。

   或手动启动：
   ```bash
   cd backend
   conda activate versemind-rag
   uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload
   ```
   > API: http://localhost:8200
   > 文档: http://localhost:8200/docs

2. 启动前端：
   ```bash
   start-frontend.bat dev
   # 或生产模式
   start-frontend.bat
   ```

   访问：
   - 开发模式：http://localhost:3200
   - 生产预览：http://localhost:4173

### 本地模型（Ollama）

1. 安装 Ollama：https://ollama.ai
2. 拉取模型：
   ```bash
   ollama pull bge-m3
   ollama pull bge-large
   ollama pull gemma3:4b
   ollama pull deepseek-r1:14b
   ollama pull phi4
   ollama pull mistral
   ollama pull llama3.2-vision
   # 其他模型按需拉取
   ```
3. 启动 Ollama 后再启动 VerseMind-RAG

### 模型配置系统

- 动态从 Ollama API 获取可用模型
- 支持多提供商（Ollama、OpenAI、DeepSeek）
- 前后端统一模型选择
- 运行时自动检测模型
- 配置文件：`config/config.toml`

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

有关索引类型、距离度量和性能调优的详细配置选项，请参阅[用户指南](./Temp/user_guide.md#向量数据库配置)。

### 环境变量说明

- **后端**
  - `BACKEND_HOST`：后端主机（默认 0.0.0.0）
  - `BACKEND_PORT`：后端端口（默认 8200）
- **前端**
  - `VITE_API_BASE_URL`：后端 API 地址（默认 http://localhost:8200）
  - `VITE_OLLAMA_BASE_URL`：Ollama 地址（默认 http://localhost:11434）
  - `VITE_PORT`：前端生产预览端口（默认 4173）
  - `VITE_USE_REAL_API`：设为 true 启用真实 API
- **API 密钥**
  - `VITE_OPENAI_API_KEY`、`VITE_OPENAI_API_BASE`
- **数据库**
  - `VECTOR_DB`：向量库（默认 faiss）

## GitHub 发布检查清单

### .gitignore

推荐 .gitignore 内容：
```
Temp/
*.pyc
__pycache__/
.env
.DS_Store
*.bak
node_modules/
dist/
storage/
```
- **不要上传本地数据、缓存、环境变量或敏感文件。**
- 只提交代码、配置模板和文档。

### 首次推送到 GitHub

1. **初始化 git（如未初始化）：**
   ```bash
   git init
   ```
2. **添加远程仓库：**
   ```bash
   git remote add origin https://github.com/topgoer/VerseMind-RAG.git
   ```
3. **添加并提交：**
   ```bash
   git add .
   git commit -m "Initial commit for VerseMind-RAG project"
   ```
4. **推送到 GitHub：**
   ```bash
   git branch -M main
   git push -u origin main
   ```

### 敏感/调试内容
- 故障排查、调试日志、内部笔记请放在 `Temp/MyNote.md`，**不要上传到 GitHub**。
- 不要上传 `Temp/` 或本地存储目录下的任何文件。

## 文档

详细文档请参考：
- [系统架构设计](./docs/VerseMind-RAG%20系统架构设计.md)
- [用户指南](./docs/user_guide.md)
- [部署指南](./Temp/deployment_guide.md)

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](./LICENSE)。

## 致谢

- [React](https://reactjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Ollama](https://ollama.ai/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Chroma](https://www.trychroma.com/)
