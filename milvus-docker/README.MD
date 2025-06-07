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
