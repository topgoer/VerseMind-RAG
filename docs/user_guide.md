# VerseMind-RAG User Guide

Welcome to the VerseMind-RAG system, a powerful Retrieval-Augmented Generation system that combines vector retrieval with large language models to provide intelligent question-answering services based on your documents.

## System Overview

VerseMind-RAG (Where Poetry Meets AI) is a modular retrieval-augmented generation system supporting the following core functions:

1. **Document Loading**: Support for uploading and managing PDF, DOCX, TXT, and Markdown files
2. **Document Chunking**: Using various strategies to divide documents into text blocks suitable for processing
3. **Document Parsing**: Analyzing document structure, extracting paragraphs, headings, tables, and images
4. **Vector Embedding**: Converting text into high-dimensional vectors for semantic search
5. **Semantic Search**: Finding the most relevant content based on user queries
6. **Text Generation**: Creating coherent responses using advanced language models

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

### Advanced Document Processing

VerseMind-RAG provides flexible document processing configurations that can be adjusted to optimize for different document types and use cases.

For detailed configuration options, please refer to the configuration example file (`config/config.example.toml`).

### Batch Processing

For scenarios requiring processing of large numbers of documents, you can:

1. Create a directory containing multiple documents
2. Use the batch upload feature to process all documents at once
3. Create a unified index for all documents

### Custom Models

Advanced users can:

1. Add custom models in Ollama
2. Modify the system configuration to use these models

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

4. **Embedding Generation Failures**:
   - Ensure the selected embedding model is correctly loaded
   - For OpenAI, check if the API key is valid

5. **Irrelevant Search Results**:
   - Try lowering the similarity threshold
   - Rephrase the query using more specific terms

6. **Low-quality Generated Content**:
   - Try different generation models
   - Adjust temperature and maximum token parameters
   - Ensure search results are relevant to the query

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
1. Check the [Issues](https://github.com/topgoer/VerseMind-RAG/issues) section on GitHub
2. Submit a detailed bug report including:
   - Steps to reproduce
   - Error messages
   - System configuration
   - Log files from the `logs` directory
