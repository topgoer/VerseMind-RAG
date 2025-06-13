# Milvus Docker 工具集

本目录包含用于管理 Milvus 向量数据库的工具脚本。

## 工具列表

### 1. 创建集合 (create_milvus_collection.py)

用于从 CSV 文件创建 Milvus 集合并导入数据。

```bash
# 基本用法（使用默认配置）
python milvus-docker/tools/create_milvus_collection.py

# 指定 CSV 文件和集合名
python milvus-docker/tools/create_milvus_collection.py --csv your_data.csv --collection your_collection

# 完整参数示例
python milvus-docker/tools/create_milvus_collection.py \
    --csv your_data.csv \
    --collection your_collection \
    --embed-col text_column \
    --infer-schema \
    --host localhost \
    --port 19530 \
    --model BAAI/bge-m3 \
    --batch-size 32 \
    --dim 1024
```

参数说明：
- `--csv`: CSV 文件路径（默认：data/SNOMED_5000.csv）
- `--collection`: 集合名称（默认：concepts_only_name）
- `--embed-col`: 用于生成嵌入的列名（默认：concept_name）
- `--infer-schema`: 自动从 CSV 推断 schema
- `--host`: Milvus 服务器地址（默认：localhost）
- `--port`: Milvus 端口（默认：19530）
- `--model`: 嵌入模型名称（默认：BAAI/bge-m3）
- `--batch-size`: 批处理大小（默认：32）
- `--dim`: 向量维度（默认：1024）

### 2. 删除集合 (drop_milvus_collection.py)

用于删除指定的 Milvus 集合。

```bash
# 基本用法
python milvus-docker/tools/drop_milvus_collection.py --collection your_collection

# 指定服务器
python milvus-docker/tools/drop_milvus_collection.py --collection your_collection --host localhost --port 19530
```

参数说明：
- `--collection`: 要删除的集合名称（必需）
- `--host`: Milvus 服务器地址（默认：localhost）
- `--port`: Milvus 端口（默认：19530）

### 3. 查询集合 (query_milvus.py)

用于查询 Milvus 集合中的数据。

```bash
# 基本用法
python milvus-docker/tools/query_milvus.py --collection your_collection --query "your query text"

# 指定服务器和结果数量
python milvus-docker/tools/query_milvus.py --collection your_collection --query "your query text" --host localhost --port 19530 --limit 5
```

参数说明：
- `--collection`: 要查询的集合名称（必需）
- `--query`: 查询文本（必需）
- `--host`: Milvus 服务器地址（默认：localhost）
- `--port`: Milvus 端口（默认：19530）
- `--limit`: 返回结果数量（默认：5）

### 4. 列出集合 (list_milvus_collections.py)

用于列出所有 Milvus 集合及其详细信息。

```bash
# 基本用法
python milvus-docker/tools/list_milvus_collections.py

# 指定服务器
python milvus-docker/tools/list_milvus_collections.py --host localhost --port 19530
```

参数说明：
- `--host`: Milvus 服务器地址（默认：localhost）
- `--port`: Milvus 端口（默认：19530）

输出信息包括：
- 集合名称
- 字段信息（名称、类型、长度等）
- 实体数量

## 环境变量

所有工具都使用默认配置（localhost:19530），无需额外设置即可工作。如果需要自定义配置，可以在项目根目录创建 `.env` 文件：

```bash
# .env 文件示例（可选）
# Milvus 配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=default_collection
MILVUS_DIM=1024

# 其他配置
# ... 其他环境变量 ...
```

注意：
1. 默认配置（localhost:19530）适用于本地开发环境
2. 命令行参数会覆盖环境变量中的设置
3. 环境变量是可选的，不设置也能正常工作

## 依赖项

- Python 3.8+
- pymilvus
- pandas
- torch
- sentence-transformers
- python-dotenv
- tqdm
