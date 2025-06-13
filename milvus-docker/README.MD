# Milvus Docker Portable Service

This directory is used for quick deployment and management of the Milvus vector database service, suitable for portable reuse across multiple projects.

## Directory Structure
- `docker-compose.yml`: Docker Compose configuration for Milvus, etcd, and minio
- `volumes/`: Data persistence directory (automatically generated)

## Quick Start
1. **Start Milvus Service**
   ```bash
   docker-compose up -d
   ```
   After starting, the Milvus service listens on port 19530 by default.

2. **Stop Service**
   ```bash
   docker-compose down
   ```

3. **Data Persistence**
   - All Milvus data is stored in the `volumes/` subdirectory.
   - As long as this directory is preserved, data will not be lost due to container reconstruction.

4. **Cross-Project Reuse**
   - You can copy the entire `milvus-docker` folder to any project root directory.
   - Simply start it directly after entering the directory, without reconfiguration.

5. **Multi-Project Usage Tips**
   - It is recommended to prefix collection names for different projects (e.g., `project1_xxx`).
   - If multiple independent Milvus instances are needed, modify the ports and volume paths.

## Port Information
- 19530: Milvus gRPC/HTTP service port
- 9091: Milvus management port

## Dependencies
- Requires [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) to be installed

---

For more advanced usage (such as backup, migration, upgrade), please refer to the main project documentation or the official Milvus documentation.

# Milvus Docker Tools

This directory contains tools for managing Milvus vector database.

## Tools List

### 1. Create Collection (create_milvus_collection.py)

Create Milvus collection and import data from CSV file.

# Milvus Collection Creation Tool

This tool creates a Milvus collection from a CSV file. It supports automatic schema inference and primary key detection.

## Usage

### Bash / Linux / macOS

```bash
python milvus-docker/tools/create_milvus_collection.py \
  --csv <path_to_csv> \
  --collection <collection_name> \
  --embed-col <column_name_for_embeddings> \
  [--primary-key <column_name_for_primary_key>] \
  [--infer-schema] \
  [--host <milvus_host>] \
  [--port <milvus_port>] \
  [--model <embedding_model>] \
  [--batch-size <batch_size>] \
  [--dim <vector_dimension>]
```

### PowerShell (Windows)

```powershell
# Using backticks for line continuation
python milvus-docker/tools/create_milvus_collection.py `
  --csv milvus-docker/data/SNOMED_5000.csv `
  --collection concepts_only_name `
  --embed-col concept_name `
  --infer-schema

# Or using a single line
python milvus-docker/tools/create_milvus_collection.py --csv milvus-docker/data/SNOMED_5000.csv --collection concepts_only_name --embed-col concept_name --infer-schema
```

## Examples

### SNOMED Medical Terminology

```bash
python milvus-docker/tools/create_milvus_collection.py \
  --csv milvus-docker/data/SNOMED_5000.csv \
  --collection concepts_only_name \
  --embed-col concept_name \
  --infer-schema
```

### Financial Terminology

```bash
python milvus-docker/tools/create_milvus_collection.py \
  --csv milvus-docker/data/万条金融标准术语.csv \
  --collection finance_terms \
  --embed-col term \
  --infer-schema
```

## Notes

- The tool automatically detects the primary key (preferring `concept_id` or `term`).
- If the primary key is not found, specify it using `--primary-key`.
- The `--embed-col` must exist in the CSV file.
- If the collection already exists, you will be prompted to delete and recreate it or exit.

### 2. Drop Collection (drop_milvus_collection.py)

Delete a specified Milvus collection.

```bash
# Basic usage
python milvus-docker/tools/drop_milvus_collection.py --collection your_collection

# Specify server
python milvus-docker/tools/drop_milvus_collection.py --collection your_collection --host localhost --port 19530
```

Parameters:
- `--collection`: Collection name to delete (required)
- `--host`: Milvus server address (default: localhost)
- `--port`: Milvus port (default: 19530)

### 3. Query Collection (query_milvus.py)

Query data from Milvus collection.

```bash
# Basic usage
python milvus-docker/tools/query_milvus.py --collection your_collection --query "your query text"

# Specify server and result limit
python milvus-docker/tools/query_milvus.py --collection your_collection --query "your query text" --host localhost --port 19530 --limit 5
```

Parameters:
- `--collection`: Collection name to query (required)
- `--query`: Query text (required)
- `--host`: Milvus server address (default: localhost)
- `--port`: Milvus port (default: 19530)
- `--limit`: Number of results to return (default: 5)

### 4. List Collections (list_milvus_collections.py)

List all Milvus collections with detailed information.

```bash
# Basic usage
python milvus-docker/tools/list_milvus_collections.py

# Specify server
python milvus-docker/tools/list_milvus_collections.py --host localhost --port 19530
```

Parameters:
- `--host`: Milvus server address (default: localhost)
- `--port`: Milvus port (default: 19530)

Output includes:
- Collection name
- Field information (name, type, length, etc.)
- Number of entities

## Environment Variables

All tools work with default settings (localhost:19530) out of the box. For custom configuration, create a `.env` file in the project root:

```bash
# .env file example (optional)
# Milvus configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=default_collection
MILVUS_DIM=1024

# Other configurations
# ... other environment variables ...
```

Notes:
1. Default settings (localhost:19530) work for local development
2. Command line arguments override environment variables
3. Environment variables are optional, tools work without them

## Dependencies

- Python 3.8+
- pymilvus
- pandas
- torch
- sentence-transformers
- python-dotenv
- tqdm
