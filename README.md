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
   git clone https://github.com/topgoer/VerseMind-RAG.git
   cd VerseMind-RAG
   ```

2. Set up Conda environment:
   ```bash
   # Create and activate the environment
   conda create -n versemind-rag python=3.12.9
   conda activate versemind-rag
   ```

3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

4. Install backend dependencies (choose one method):

   **Option A: Using pip with requirements.txt**
   ```bash
   cd ../backend
   pip install -r requirements.txt
   ```

   **Option B: Using Poetry**
   ```bash
   cd ../backend
   # Install Poetry if not already installed
   # pip install poetry
   poetry install
   ```

   **Option C: Using uv (faster Python package installer)**
   ```bash
   cd ../backend
   # Install uv if not already installed
   # pip install uv
   uv pip install -r requirements.txt
   ```

5. Configure environment variables:
   ```bash
   # Create a config.toml file based on the example
   cp config/config.example.toml config/config.toml
   # Edit the config.toml file to set your API keys and preferences
   ```

### Running the Project

1. **Start backend:**
   ```bash
   # Using the convenience script (Windows):
   start-backend.bat
   
   # OR manually:
   cd backend
   conda activate versemind-rag  # Or your virtual environment
   uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload
   ```
   
   The backend will be available at:
   - API endpoint: http://localhost:8200
   - API documentation: http://localhost:8200/docs

2. **Start frontend:**
   ```bash
   # Development mode with hot reload:
   cd frontend
   npm run dev
   
   # OR using convenience script:
   start-frontend.bat dev
   ```
   
   ```bash
   # Production mode:
   cd frontend
   npm run build
   npm run preview
   
   # OR using convenience script:
   start-frontend.bat
   ```

3. **Access the application:**
   - Development mode: http://localhost:3200
   - Production preview: http://localhost:4173

### Using Local Models with Ollama

VerseMind-RAG can utilize local AI models through [Ollama](https://ollama.ai) for both text generation and embedding, which:
- Keeps your data private by processing it locally
- Eliminates API costs and rate limits
- Provides offline functionality

**Setup Steps:**

1. Install Ollama from [ollama.ai](https://ollama.ai)

2. Pull the models you want to use:
   ```bash
   # Pull embedding models (choose at least one)
   ollama pull bge-m3        # Smaller, faster embedding model
   ollama pull bge-large     # Larger, more accurate embedding model
   
   # Pull generation models (choose models that fit your hardware)
   ollama pull gemma3:4b     # Smaller, faster model (4B parameters)
   ollama pull deepseek-r1:14b # Better quality, needs more RAM (14B parameters)
   ollama pull phi4          # Microsoft's latest model
   ollama pull mistral       # Good performance/resource balance
   ollama pull llama3.2-vision # For image understanding capabilities
   ```

3. Ensure Ollama is running in the background before starting VerseMind-RAG

4. In the VerseMind-RAG interface, select your preferred models from the Models dropdown menu

### Environment Configuration

The application is configured through `config/config.toml`. You need to copy and modify the example configuration file:

```bash
# Copy the example configuration
cp config/config.example.toml config/config.toml

# Edit the config.toml file according to your needs
# For Ollama users, the default settings should work out of the box
# For API-based models (OpenAI, DeepSeek), you'll need to add your API keys
```

Basic configuration options:

```toml
# Main LLM configuration - selects your default model
[llm]
api_type = "ollama"  # Use "ollama" for local models, "openai" for OpenAI/DeepSeek APIs
model = "gemma3:4b"  # Your preferred model
base_url = "http://localhost:11434"  # Ollama API URL (default)

# Server settings
[server]
host = "0.0.0.0"
port = 8200

# Vector database settings
[vector_store]
type = "faiss"  # Options: "faiss", "chroma"
persist_directory = "./storage/vector_db"
```

See the `config/config.example.toml` file for more configuration options.

## Advanced Usage

### Custom Model Configuration

VerseMind-RAG allows you to customize models through the `config/config.toml` file. You can configure:

- Multiple embedding models with different dimensions and providers
- Custom generation models with specific parameters (temperature, max_tokens, etc.)
- Provider-specific configurations for different AI services

See the model configuration section in `config/config.example.toml` for examples.

### Vector Database Optimization

VerseMind-RAG supports multiple vector database backends for storing and retrieving document embeddings:

- **FAISS**: Optimized for high-performance vector similarity search
  - Excellent for large-scale datasets (millions of vectors)
  - Multiple index types (Flat, HNSW32, HNSW64)
  - Various distance metrics (cosine, L2, inner product)

- **Chroma**: Feature-rich vector database with metadata filtering
  - Rich metadata filtering capabilities
  - Easy-to-use API and simple configuration
  - Excellent for complex document retrieval requirements

Configuration is managed through the `config/config.toml` file using this structure:

```toml
[vector_store]
type = "faiss"  # Options: "faiss", "chroma"
persist_directory = "./storage/vector_db"

[vector_store.faiss]
index_type = "HNSW32"  # Options: "Flat", "HNSW32", "HNSW64"
metric = "cosine"      # Options: "cosine", "l2", "ip"

[vector_store.chroma]
collection_name = "versemind_docs"
distance_function = "cosine"  # Options: "cosine", "l2", "ip"
```

For detailed configuration options including index types, distance metrics, and performance tuning recommendations, please refer to the [User Guide](./Temp/user_guide.md#向量数据库配置).

### Advanced Document Processing

VerseMind-RAG provides flexible document processing configurations that can be adjusted to optimize for different document types and use cases.

For detailed configuration options, please refer to the configuration example file (`config/config.example.toml`).

## How to Use VerseMind-RAG

VerseMind-RAG provides a complete document processing and retrieval pipeline. Here's a quick guide to using the system:

### Document Processing Workflow

1. **Upload Documents**: 
   - Navigate to the Documents tab in the UI
   - Click "Upload Document" and select your files (PDF, DOCX, TXT, etc.)
   - Your documents will be loaded into the system

2. **Document Processing**:
   - The system automatically processes your documents through the pipeline:
     - **Chunking**: Breaking documents into manageable pieces
     - **Parsing**: Extracting structured content and metadata
     - **Embedding**: Converting text into vector representations
     - **Indexing**: Storing vectors for efficient retrieval

3. **Querying Documents**:
   - Navigate to the Chat tab
   - Type your query in the input field
   - The system will:
     - Search for relevant information from your documents
     - Retrieve the most semantically similar content
     - Generate comprehensive answers based on the retrieved content

4. **Viewing Results**:
   - See both the generated answer and the source documents
   - Access the specific passages that informed the response
   - Explore document relationships through the interactive visualizations

### Tips for Better Results

- **Ask specific questions** for more precise answers
- **Upload high-quality documents** with clear text (OCR quality affects results)
- **Try different models** for embedding and generation to compare results
- **Use local models** via Ollama for privacy and offline capability
- **Adjust chunk size** in config.toml for different document types

### Sample Queries

- "Summarize the key points about RAG evaluation metrics"
- "What are the challenges in implementing retrieval-augmented generation?"
- "Compare and contrast different chunking strategies for RAG systems"

## Troubleshooting

### Common Issues and Solutions

#### Backend Issues

1. **PDF Parsing Errors**
   - **Issue**: Error messages when uploading PDF files
   - **Solution**: 
     - Ensure the PDF is not password protected
     - Run the cleanup script: `python backend/scripts/simple_cleanup.py`
     - Verify you have the required dependencies: `pip install pymupdf pdfplumber reportlab`

2. **Model Connection Issues**
   - **Issue**: "Failed to connect to model provider" errors
   - **Solution**:
     - For Ollama: Ensure Ollama service is running (`ollama serve`)
     - For API-based models: Verify your API keys in config.toml
     - Check your network connection and firewall settings

3. **Storage Space Issues**
   - **Issue**: System becomes slow or fails due to excessive temp files
   - **Solution**:
     - Run cleanup scripts periodically: `python backend/scripts/clean_storage_docs.py`
     - Consider setting up a cron job/scheduled task for automatic cleanup
     - Configure shorter retention periods in config.toml

#### Frontend Issues

1. **Interface Not Loading**
   - **Issue**: Blank screen or loading spinner stuck
   - **Solution**:
     - Check browser console for errors (F12)
     - Verify backend is running and accessible
     - Clear browser cache and reload

2. **Slow Response Times**
   - **Issue**: Queries take too long to process
   - **Solution**:
     - Consider using smaller/faster models in config
     - Reduce document collection size
     - Optimize vector store settings in config.toml

### Getting Help

If you encounter issues not covered here:
1. Check the [Issues](https://github.com/yourusername/VerseMind-RAG/issues) section on GitHub
2. Submit a detailed bug report including:
   - Steps to reproduce
   - Error messages
   - System configuration
   - Log files from the `logs` directory

## Documentation

For detailed documentation, refer to:
- [System Architecture Design](./docs/VerseMind-RAG%20系统架构设计.md)
- [User Guide](./docs/user_guide.md)

## Testing

The project includes comprehensive tests for both backend and frontend:

### Backend Tests

```bash
# Run all tests with verbose output
cd backend
pytest -v

# Run with test environment settings
# Windows PowerShell
$env:TEST_ENV='true'; python -m pytest -v
# Linux/Mac
TEST_ENV=true pytest -v
```

### Test Cleanup Scripts

The project includes scripts to clean up temporary test files:

```bash
cd backend/scripts

# Simple standalone cleanup script
python simple_cleanup.py

# Advanced cleanup using TestFileCleanup class
python clean_storage_docs.py
```

These scripts help maintain disk space by removing temporary files created during tests, particularly in the `storage/documents` directory.

## Continuous Integration

VerseMind-RAG uses GitHub Actions for continuous integration to ensure code quality. The CI workflow:

- Runs backend tests on each push and pull request
- Installs dependencies automatically 
- Sets up test environment variables
- Runs cleanup scripts after tests
- Performs frontend linting and tests

You can see the CI configuration in `.github/workflows/ci.yml`.

## Contributing

Contributions to VerseMind-RAG are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code passes all tests before submitting a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

## Acknowledgements

- [React](https://reactjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Ollama](https://ollama.ai/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Chroma](https://www.trychroma.com/)
