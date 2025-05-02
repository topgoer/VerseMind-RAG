# VerseMind-RAG

**Where Poetry Meets AI**

VerseMind-RAG is a document intelligence and semantic generation system designed to provide a complete RAG (Retrieval-Augmented Generation) solution. It supports document loading, chunking, parsing, vector embedding, indexing, semantic search, and text generation.

## Features

- **Document Processing**: Load, chunk, and parse documents for structured content.
- **Vector Embedding**: Generate embeddings for semantic search.
- **Semantic Search**: Retrieve relevant content based on user queries.
- **Text Generation**: Generate responses using advanced AI models.
- **Modular Design**: Easily extensible with support for multiple models and vector databases.
- **Dynamic Model Configuration**: Centralized model management system for consistent model selection across components.

## System Architecture

- **Frontend**: React + Vite + TailwindCSS
- **Backend**: FastAPI + Python services
- **Storage**: File system + FAISS/Chroma vector database
- **Models**: Ollama (local) + DeepSeek/OpenAI APIs

## Quick Start

### Prerequisites

- Node.js 18+ (for frontend)
- Python 3.12.9 (for backend, recommended to use Conda)
- Conda (or Miniconda/Anaconda)
- SWIG (needed for Faiss, can be installed via Conda: `conda install -c anaconda swig`)
- Ollama (optional, for local model support)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/VerseMind-RAG.git
   cd VerseMind-RAG
   ```

2. Set up Conda environment and install prerequisites:
   ```bash
   # Create and activate the environment
   conda create -n versemind-rag python=3.12.9
   conda activate versemind-rag
   
   # Install SWIG (required for Faiss)
   conda install -c anaconda swig
   
   # Install Faiss directly using Conda (recommended)
   conda install -c pytorch faiss-cpu
   ```

3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

4. Install remaining backend dependencies using pip:
   ```bash
   cd ../backend 
   # Ensure faiss-cpu is commented out in requirements.txt if installed via conda
   pip install -r requirements.txt
   ```

5. Configure environment variables:
   ```bash
   # Create a .env file in the frontend directory
   cd frontend
   touch .env
   ```

   Add the following to the .env file:
   ```
   # Backend API URL - this is where your backend server is running
   VITE_API_BASE_URL=http://localhost:8200
   # Ollama server URL
   VITE_OLLAMA_BASE_URL=http://localhost:11434
   # Frontend port for production preview mode (not the dev server)
   VITE_PORT=4173
   # Enable real API calls
   VITE_USE_REAL_API=true
   ```

### Running the Project

1. **启动后端（推荐）**：
   ```bash
   start-backend.bat
   ```
   > 该脚本会自动激活 conda 环境并启动 FastAPI 后端服务。

   或手动启动：
   ```bash
   cd backend
   conda activate versemind-rag
   uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload
   ```
   > API 地址: http://localhost:8200
   > Swagger 文档: http://localhost:8200/docs

2. 启动前端：
   ```bash
   # 开发模式（热更新）
   start-frontend.bat dev
   # 生产模式
   start-frontend.bat
   ```

   This will automatically:
   - Clean any old build files (for production mode)
   - Build the frontend (for production mode)
   - Start the appropriate server

3. Access the application:
   - Development mode: `http://localhost:3200` (when using start-frontend.bat dev)
   - Production preview: `http://localhost:4173` (when using start-frontend.bat)

### Using Local Models with Ollama

1. Install Ollama from [ollama.ai](https://ollama.ai)

2. Pull the models you want to use:
   ```bash
   # Pull embedding models
   ollama pull bge-m3
   ollama pull bge-large
   
   # Pull generation models
   ollama pull gemma3:4b
   ollama pull deepseek-r1:14b
   ollama pull phi4
   ollama pull mistral
   ollama pull llama3.2-vision
   # Add other models as needed
   ```

3. Ensure Ollama is running in the background before starting VerseMind-RAG

### Model Configuration System

VerseMind-RAG includes a centralized model configuration system that:

- Dynamically fetches available models from Ollama API
- Supports multiple model providers (Ollama, OpenAI, DeepSeek)
- Provides consistent model selection across all components
- Auto-detects available models at runtime

The model configuration is managed in `frontend/src/config/models.js` and includes:
- Generation models for text generation and chat
- Embedding models for vector embedding
- Support for provider-specific model parameters

### Environment Configuration

The application behavior is controlled through environment variables in the `.env` file:

- **Backend Configuration**
  - `BACKEND_HOST`: Host for the backend server (default: 0.0.0.0)
  - `BACKEND_PORT`: Port for the backend server (default: 8200)

- **Frontend Configuration**
  - `VITE_API_BASE_URL`: URL for the backend API (default: http://localhost:8200)
  - `VITE_OLLAMA_BASE_URL`: URL for local Ollama server (default: http://localhost:11434)
  - `VITE_PORT`: Port for the frontend production preview server (default: 4173)
  - `VITE_USE_REAL_API`: Set to "true" to enable real API calls (important for production builds)

- **API Keys**
  - `VITE_OPENAI_API_KEY`: Your OpenAI API key
  - `VITE_OPENAI_API_BASE`: Base URL for OpenAI API (or DeepSeek API)

- **Server Configuration**
  - `VITE_OLLAMA_BASE_URL`: URL for local Ollama server (default: http://localhost:11434)

- **Database Configuration**
  - `VECTOR_DB`: Vector database to use (default: faiss)

## GitHub Release Checklist

### .gitignore

A recommended .gitignore for this project:
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
- Do **not** upload local data, cache, environment variables, or any sensitive files.
- Only commit code, config templates, and documentation.

### Initial GitHub Push

1. **Initialize git (if not already):**
   ```bash
   git init
   ```
2. **Add remote:**
   ```bash
   git remote add origin https://github.com/topgoer/VerseMind-RAG.git
   ```
3. **Add and commit:**
   ```bash
   git add .
   git commit -m "Initial commit for VerseMind-RAG project"
   ```
4. **Push to GitHub:**
   ```bash
   git branch -M main
   git push -u origin main
   ```

### Sensitive/Debug Content
- Troubleshooting, debug logs, and internal notes are kept in `Temp/MyNote.md` and **should not be published to GitHub**.
- Do not upload any files from `Temp/` or local storage directories.

## Documentation

For detailed documentation, refer to:
- [System Architecture Design](./docs/VerseMind-RAG%20系统架构设计.md)
- [User Guide](./docs/user_guide.md)
- [Deployment Guide](./Temp/deployment_guide.md)

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

## Acknowledgements

- [React](https://reactjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Ollama](https://ollama.ai/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Chroma](https://www.trychroma.com/)