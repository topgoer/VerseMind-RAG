import argparse
import sys
from pymilvus import (
    model,
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
import pandas as pd
from tqdm import tqdm
import logging
import torch
import traceback

# Ensured proper usage of `collection` and addressed the linting issue

# Milvus Configuration Variables
MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
MILVUS_COLLECTION = "concepts_only_name"
MILVUS_DIM = 1024

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# 命令行参数解析
parser = argparse.ArgumentParser(
    description="Create Milvus collection from CSV file with optional schema inference."
)
parser.add_argument(
    "--csv", type=str, default="data/SNOMED_5000.csv", help="Path to the CSV file."
)
parser.add_argument(
    "--collection",
    type=str,
    default="concepts_only_name",
    help="Milvus collection name.",
)
parser.add_argument(
    "--embed-col",
    type=str,
    default=None,
    help="Column name to use for embedding. If not provided, will prompt.",
)
parser.add_argument(
    "--infer-schema", action="store_true", help="Automatically infer schema from CSV."
)
args = parser.parse_args()

# 检查是否有可用的 GPU
device = "cuda:0" if torch.cuda.is_available() else "cpu"
logging.info(f"Using device: {device}")

# 初始化嵌入函数
embedding_function = model.dense.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-m3", device=device, trust_remote_code=True, batch_size=32
)

# 文件路径和集合名
file_path = args.csv
collection_name = args.collection

# 连接到 Milvus Docker 容器
connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)


def create_milvus_collection():
    # Check if the collection already exists
    if utility.has_collection(collection_name):
        print(f"Collection {collection_name} already exists.")
        return

    # Define the collection schema
    fields = [
        FieldSchema(
            name="concept_id", dtype=DataType.VARCHAR, max_length=50, is_primary=True
        ),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=MILVUS_DIM),
        FieldSchema(name="concept_name", dtype=DataType.VARCHAR, max_length=240),
        FieldSchema(name="domain_id", dtype=DataType.VARCHAR, max_length=18),
        FieldSchema(name="vocabulary_id", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="concept_class_id", dtype=DataType.VARCHAR, max_length=19),
        FieldSchema(name="standard_concept", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="concept_code", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="valid_start_date", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="valid_end_date", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="invalid_reason", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="FSN", dtype=DataType.VARCHAR, max_length=587),
    ]
    schema = CollectionSchema(fields=fields, description="Medical document embeddings")

    # Create the collection
    collection = Collection(name=collection_name, schema=schema)
    print(f"Collection {collection_name} created successfully.")

    # Explicitly use `collection` for further operations
    collection.create_index(
        field_name="vector",
        index_params={"index_type": "AUTOINDEX", "metric_type": "COSINE"},
    )
    collection.load()
    logging.info(f"Collection {collection_name} is ready for data insertion.")


# 加载数据
logging.info(f"Loading data from CSV: {file_path}")
df = pd.read_csv(file_path, dtype=str, low_memory=False).fillna("NA")

# 自动去除主键字段前后空白
for key_col in ["term", "concept_id", "id"]:
    if key_col in df.columns:
        df[key_col] = df[key_col].str.strip()

# 自动推断 schema
if args.infer_schema:
    print("\n[自动推断 Milvus Schema]")
    inferred_fields = []
    for col in df.columns:
        sample_val = df[col].iloc[0]
        # 推断类型和最大长度
        if col.lower() in ["id", "concept_id", "term"]:
            max_len = max(df[col].astype(str).map(len).max(), 10)
            max_len = min(max_len, 255)
            inferred_fields.append(
                FieldSchema(
                    name=col,
                    dtype=DataType.VARCHAR,
                    max_length=max_len,
                    is_primary=True,
                )
            )
        elif sample_val.replace(".", "", 1).isdigit():
            # 简单判断是否为数字
            inferred_fields.append(
                FieldSchema(name=col, dtype=DataType.VARCHAR, max_length=50)
            )
        else:
            max_len = max(df[col].astype(str).map(len).max(), 10)
            max_len = min(max_len, 1000)
            inferred_fields.append(
                FieldSchema(name=col, dtype=DataType.VARCHAR, max_length=max_len)
            )
    # 预留向量字段，后续插入
    sample_doc = "Sample Text"
    sample_embedding = embedding_function([sample_doc])[0]
    vector_dim = len(sample_embedding)
    inferred_fields.insert(
        1, FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim)
    )
    print("推断的 schema 字段:")
    for f in inferred_fields:
        print(f"- {f.name}: {f.dtype} (max_length={getattr(f, 'max_length', '-')})")
    # 选择 embedding 列
    embed_col = args.embed_col
    if not embed_col or embed_col not in df.columns:
        print("可选的列:", list(df.columns))
        embed_col = input("请输入用于 embedding 的列名: ").strip()
        if embed_col not in df.columns:
            print("[错误] 该列不存在于 CSV 中。退出。")
            sys.exit(1)
    print(f"将使用列 '{embed_col}' 生成 embedding。\n")
    confirm = input("请确认 schema 是否正确，继续请按 y，退出请按 n: ").strip().lower()
    if confirm != "y":
        print("用户取消操作。退出。")
        sys.exit(0)
    fields = inferred_fields
else:
    # 默认 schema
    sample_doc = "Sample Text"
    sample_embedding = embedding_function([sample_doc])[0]
    vector_dim = len(sample_embedding)
    fields = [
        FieldSchema(
            name="concept_id", dtype=DataType.VARCHAR, max_length=50, is_primary=True
        ),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
        FieldSchema(name="concept_name", dtype=DataType.VARCHAR, max_length=240),
        FieldSchema(name="domain_id", dtype=DataType.VARCHAR, max_length=18),
        FieldSchema(name="vocabulary_id", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="concept_class_id", dtype=DataType.VARCHAR, max_length=19),
        FieldSchema(name="standard_concept", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="concept_code", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="valid_start_date", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="valid_end_date", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="invalid_reason", dtype=DataType.VARCHAR, max_length=10),
        FieldSchema(name="FSN", dtype=DataType.VARCHAR, max_length=587),
    ]
    embed_col = args.embed_col or "concept_name"
    if embed_col not in df.columns:
        print(
            f"[错误] 默认 embedding 列 '{embed_col}' 不存在于 CSV 中。请用 --embed-col 指定。"
        )
        sys.exit(1)

schema = CollectionSchema(
    fields, "Auto-inferred or default schema", enable_dynamic_field=True
)

# 如果集合已存在，跳过导入
if utility.has_collection(collection_name):
    logging.info(f"Collection {collection_name} already exists. Skipping import.")
else:
    # 创建新集合
    collection = Collection(name=collection_name, schema=schema)
    print(f"Collection {collection_name} created successfully.")
    # 创建索引
    index_params = {"index_type": "AUTOINDEX", "metric_type": "COSINE"}
    collection.create_index(field_name="vector", index_params=index_params)
    # 加载集合到内存
    collection.load()
    logging.info(f"Loaded collection: {collection_name}")
    batch_size = 2048

    def truncate_string(s, max_length):
        if max_length is None:
            return str(s)
        return str(s)[:max_length] if len(str(s)) > max_length else str(s)

    for start_idx in tqdm(range(0, len(df), batch_size), desc="Processing batches"):
        end_idx = min(start_idx + batch_size, len(df))
        batch_df = df.iloc[start_idx:end_idx]
        docs = [row[embed_col] for _, row in batch_df.iterrows()]
        try:
            embeddings = embedding_function(docs)
            logging.info(
                f"Generated embeddings for batch {start_idx // batch_size + 1}"
            )
        except Exception as e:
            logging.error(
                f"Error generating embeddings for batch {start_idx // batch_size + 1}: {e}"
            )
            continue
        data = []
        for idx, (_, row) in enumerate(batch_df.iterrows()):
            try:
                item = {
                    col: truncate_string(row[col], getattr(f, "max_length", 1000))
                    for col, f in zip(df.columns, fields)
                    if hasattr(f, "max_length")
                }
                item["vector"] = embeddings[idx]
                item["input_file"] = truncate_string(file_path, 500)
                collection.insert(data=[item])
            except Exception as e:
                print(
                    f"[ERROR] 插入第 {start_idx + idx} 行时出错，内容为：{row.to_dict()}"
                )
                print(f"异常信息：{e}")
                logging.error(f"Error inserting row {start_idx + idx}: {e}")
        logging.info(
            f"Inserted batch {start_idx // batch_size + 1} into collection: {collection_name}"
        )
    logging.info(f"Data import completed for collection: {collection_name}")

# 示例查询
query = "SOB"
query_embeddings = embedding_function([query])
search_result = collection.search(
    data=query_embeddings,
    anns_field="vector",
    param={"metric_type": "COSINE", "params": {"nprobe": 10}},
    limit=5,
    output_fields=[embed_col],
)
logging.info(f"Search result for '{query}': {search_result}")

if __name__ == "__main__":
    try:
        create_milvus_collection()
    except Exception as e:
        print("Exception occurred:", e)
        traceback.print_exc()
        sys.exit(1)
