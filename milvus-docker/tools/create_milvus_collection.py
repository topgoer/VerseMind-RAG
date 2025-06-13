import argparse
import sys
from pymilvus import (
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
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="创建 Milvus 集合并导入数据")
    parser.add_argument("--csv", type=str, required=True, help="CSV 文件路径")
    parser.add_argument("--collection", type=str, required=True, help="集合名称")
    parser.add_argument("--embed-col", type=str, help="用于生成 embedding 的列名")
    parser.add_argument("--primary-key", type=str, help="主键列名")
    parser.add_argument(
        "--model", type=str, default="BAAI/bge-m3", help="embedding 模型名称"
    )
    parser.add_argument("--batch-size", type=int, default=32, help="批处理大小")
    parser.add_argument(
        "--host", type=str, default="localhost", help="Milvus 服务器地址"
    )
    parser.add_argument("--port", type=str, default="19530", help="Milvus 服务器端口")
    parser.add_argument("--infer-schema", action="store_true", help="自动推断 schema")
    return parser.parse_args()


# 检查是否有可用的 GPU
device = "cuda:0" if torch.cuda.is_available() else "cpu"
logging.info(f"Using device: {device}")


def get_default_schema(primary_key, embed_col, vector_dim):
    """获取默认 schema"""
    return [
        FieldSchema(
            name=primary_key, dtype=DataType.VARCHAR, max_length=255, is_primary=True
        ),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
        FieldSchema(name=embed_col, dtype=DataType.VARCHAR, max_length=1000),
    ]


def detect_primary_key_from_df(df, user_primary_key=None):
    candidates = [col for col in ["term", "concept_id", "id"] if col in df.columns]
    if user_primary_key and user_primary_key in df.columns:
        return user_primary_key
    if len(candidates) == 1:
        print(f"自动选择主键列: {candidates[0]}")
        return candidates[0]
    elif len(candidates) > 1:
        print("检测到多个可能的主键列:", candidates)
        print(f"推荐使用: {candidates[0]}")
        pk = input(f"请输入主键列名（直接回车默认 {candidates[0]}）: ").strip()
        if not pk:
            return candidates[0]
        if pk in df.columns:
            return pk
        raise ValueError("输入的主键列不存在。")
    else:
        print("可选的主键列:", list(df.columns))
        pk = input("请输入主键列名: ").strip()
        if pk in df.columns:
            return pk
        raise ValueError(
            "No suitable primary key found. Please specify with --primary-key."
        )


def infer_field_schema(df, col, primary_key):
    """Infer FieldSchema for a single column."""
    sample_val = df[col].iloc[0]
    if col == primary_key:
        # Ensure max_len is a Python int
        _max_len = max(df[col].astype(str).map(len).max(), 10)
        max_len = min(_max_len, 255)
        return FieldSchema(
            name=col, dtype=DataType.VARCHAR, max_length=int(max_len), is_primary=True
        )
    elif str(sample_val).replace(".", "", 1).isdigit():
        # 50 is already a Python int
        return FieldSchema(name=col, dtype=DataType.VARCHAR, max_length=50)
    else:
        # Ensure max_len is a Python int
        _max_len = max(df[col].astype(str).map(len).max(), 10)
        max_len = min(_max_len, 1000)
        return FieldSchema(name=col, dtype=DataType.VARCHAR, max_length=int(max_len))


def infer_schema_and_primary_key(df, args, embedding_function):
    """Auto-infer schema and primary key, coordinating helper functions."""
    primary_key = detect_primary_key_from_df(df, args.primary_key)
    inferred_fields = [infer_field_schema(df, col, primary_key) for col in df.columns]
    sample_doc = "Sample Text"
    sample_embedding = embedding_function.encode([sample_doc], convert_to_tensor=False)[
        0
    ]
    vector_dim = len(sample_embedding)  # len() should return a Python int

    # Find the primary key field to insert the vector field after it
    pk_index = -1
    for i, f_schema in enumerate(inferred_fields):
        # Check if is_primary attribute exists and is True
        if getattr(f_schema, "is_primary", False):
            pk_index = i
            break

    # Create the vector field schema, ensuring dim is a Python int
    vector_field_schema = FieldSchema(
        name="vector", dtype=DataType.FLOAT_VECTOR, dim=int(vector_dim)
    )

    if pk_index != -1:
        inferred_fields.insert(pk_index + 1, vector_field_schema)
    else:
        logging.warning(
            "Primary key not found in inferred fields list during schema construction. Appending vector field."
        )
        inferred_fields.append(vector_field_schema)

    return inferred_fields, primary_key, vector_dim


def get_embedding_column(df, embed_col):
    """获取用于嵌入的列名"""
    if not embed_col or embed_col not in df.columns:
        logging.info("可选的列: %s", list(df.columns))
        embed_col = input("请输入用于 embedding 的列名: ").strip()
        if embed_col not in df.columns:
            logging.error("[错误] 该列不存在于 CSV 中。退出。")
            sys.exit(1)
    return embed_col


def create_collection(schema, collection_name):
    """创建 Milvus 集合"""
    if utility.has_collection(collection_name):
        logging.info(f"Collection {collection_name} already exists.")
        return Collection(collection_name)

    collection = Collection(
        name=collection_name,
        schema=CollectionSchema(
            schema, "Auto-inferred or default schema", enable_dynamic_field=True
        ),
    )
    index_params = {"index_type": "AUTOINDEX", "metric_type": "COSINE"}
    collection.create_index(field_name="vector", index_params=index_params)
    collection.load()
    logging.info(f"Created and loaded collection: {collection_name}")
    return collection


def process_batch(batch_df, collection, embed_col, fields, embedding_function):
    """处理一批数据"""
    # 准备数据
    docs = batch_df[embed_col].tolist()
    embeddings = embedding_function.encode(
        docs, convert_to_tensor=False, show_progress_bar=False
    )
    insert_data = []
    for i, row in batch_df.iterrows():
        entity = {}
        for field in fields:
            if field.name == "vector":
                entity[field.name] = embeddings[i - batch_df.index[0]].tolist()
            else:
                entity[field.name] = str(row[field.name])
        insert_data.append(entity)
    # 插入数据
    collection.insert(insert_data)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def process_batch_with_retry(
    batch_df, collection, embed_col, fields, embedding_function
):
    """带重试机制的批处理函数"""
    try:
        process_batch(batch_df, collection, embed_col, fields, embedding_function)
    except Exception as e:
        if "etcdserver: request timed out" in str(e):
            logging.warning(f"etcd timeout, retrying... Error: {str(e)}")
            raise  # 触发重试
        raise  # 其他错误直接抛出


def truncate_string(s, max_length):
    """截断字符串到指定长度"""
    if max_length is None:
        return str(s)
    return str(s)[:max_length] if len(str(s)) > max_length else str(s)


def validate_csv_columns(df, embed_col, primary_key):
    """验证 CSV 列名"""
    if embed_col not in df.columns:
        raise ValueError(f"指定的 embedding 列 '{embed_col}' 不存在于 CSV 中")
    if primary_key not in df.columns:
        raise ValueError(f"指定的主键列 '{primary_key}' 不存在于 CSV 中")


def detect_primary_key(df, primary_key=None):
    """自动检测主键列"""
    if primary_key:
        if primary_key not in df.columns:
            raise ValueError(f"指定的主键列 '{primary_key}' 不存在于 CSV 中")
        return primary_key

    # 按优先级尝试常见的主键列名
    for key_col in ["term", "concept_id", "id"]:
        if key_col in df.columns:
            # 检查唯一性
            if df[key_col].nunique() == len(df):
                return key_col

    raise ValueError(
        "No suitable primary key found. Please specify with --primary-key."
    )


def get_vector_dimension(embedding_function):
    """获取向量维度"""
    sample_doc = "Sample Text"
    sample_embedding = embedding_function.encode([sample_doc], convert_to_tensor=False)[
        0
    ]
    return len(sample_embedding)


def get_field_max_length(df, col, is_primary=False):
    """获取字段最大长度"""
    max_len = max(df[col].astype(str).map(len).max(), 10)
    if is_primary:
        return min(max_len, 255)  # 主键最大长度 255
    return min(max_len, 1000)  # 普通字段最大长度 1000


def create_field_schema(col, df, primary_key):
    """创建字段 schema"""
    is_primary = col == primary_key
    max_len = get_field_max_length(df, col, is_primary)

    if is_primary:
        return FieldSchema(
            name=col, dtype=DataType.VARCHAR, max_length=max_len, is_primary=True
        )
    else:
        return FieldSchema(name=col, dtype=DataType.VARCHAR, max_length=max_len)


def create_schema(df, primary_key, embed_col, embedding_function, args):
    """创建集合 schema"""
    vector_dim = get_vector_dimension(embedding_function)

    if not args.infer_schema:
        return get_default_schema(primary_key, embed_col, vector_dim)

    logging.info("\n[Auto-infer Milvus Schema]")
    inferred_fields, primary_key, vector_dim = infer_schema_and_primary_key(
        df, args, embedding_function
    )

    logging.info("Inferred schema fields:")
    for f in inferred_fields:
        logging.info(
            f"- {f.name}: {f.dtype} (max_length={getattr(f, 'max_length', '-')})"
        )
    return inferred_fields


def handle_existing_collection(collection_name):
    """处理已存在的集合"""
    if utility.has_collection(collection_name):
        logging.warning(f"\n集合 '{collection_name}' 已存在。")
        logging.info("请选择操作：")
        logging.info("1. 删除现有集合并重新创建")
        logging.info("2. 退出程序")
        choice = input("请输入选项 (1/2): ").strip()
        if choice == "1":
            logging.info(f"正在删除集合 '{collection_name}'...")
            utility.drop_collection(collection_name)
            logging.info(f"集合 '{collection_name}' 已删除")
            return True
        else:
            logging.info("操作已取消")
            return False
    return True


def create_collection_with_index(collection_name, schema):
    """创建集合并设置索引"""
    collection = Collection(name=collection_name, schema=schema)
    logging.info(f"Created collection '{collection_name}'")

    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024},
    }
    collection.create_index(field_name="vector", index_params=index_params)
    logging.info("Created index on vector field")
    return collection


def process_data_in_batches(
    df, collection, embed_col, fields, batch_size, embedding_function
):
    """批量处理数据"""
    total_rows = len(df)
    num_batches = (total_rows + batch_size - 1) // batch_size
    logging.info(
        f"Processing {total_rows} rows in {num_batches} batches (batch size: {batch_size})"
    )
    for batch_num, i in enumerate(
        tqdm(range(0, total_rows, batch_size), desc="Processing batches"), 1
    ):
        batch_df = df.iloc[i : i + batch_size]
        try:
            process_batch_with_retry(
                batch_df, collection, embed_col, fields, embedding_function
            )
        except Exception as e:
            logging.error(f"Error in batch {batch_num}: {str(e)}")
            logging.error(f"Batch size: {len(batch_df)}")
            raise
    collection.flush()
    logging.info(f"All {num_batches} batches imported successfully.")


def test_search(collection, df, embed_col, primary_key, embedding_function):
    """测试搜索功能"""
    test_term = df[embed_col].sample(n=1).iloc[0]
    logging.info(f"\nTesting search with random term: {test_term}")
    query_embeddings = embedding_function.encode([test_term], convert_to_tensor=False)[
        0
    ].tolist()
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    results = collection.search(
        data=[query_embeddings],
        anns_field="vector",
        param=search_params,
        limit=5,
        output_fields=[primary_key, embed_col],
    )
    logging.info(f"Search results for '{test_term}':")
    for hits in results:
        for hit in hits:
            logging.info(f"- {hit.entity.get(embed_col)} (score: {hit.score:.4f})")


def create_milvus_collection():
    """主函数：创建 Milvus 集合并导入数据"""
    args = parse_args()

    try:
        # 连接到 Milvus
        connections.connect(host=args.host, port=args.port)
        logging.info(f"Connected to Milvus at {args.host}:{args.port}")

        # 初始化 embedding 模型
        logging.info(f"Initializing embedding model: {args.model}")
        embedding_function = SentenceTransformer(args.model)

        # 检查集合是否已存在
        if not handle_existing_collection(args.collection):
            return

        # 读取 CSV 文件
        logging.info(f"Reading CSV file: {args.csv}")
        df = pd.read_csv(args.csv)
        # 自动去除主键字段前后空白，确保唯一性判断
        for key_col in ["term", "concept_id", "id"]:
            if key_col in df.columns:
                df[key_col] = df[key_col].astype(str).str.strip()

        # 自动推断 schema 和主键
        if args.infer_schema:
            print("\n[自动推断 Milvus Schema]")
            fields, primary_key, vector_dim = infer_schema_and_primary_key(
                df, args, embedding_function
            )
            print("推断的 schema 字段:")
            for f in fields:
                print(
                    f"- {f.name}: {f.dtype} (max_length={getattr(f, 'max_length', '-')})"
                )
        else:
            # 默认 schema
            primary_key = detect_primary_key(df, args.primary_key)
            vector_dim = get_vector_dimension(embedding_function)
            fields = get_default_schema(primary_key, args.embed_col, vector_dim)

        # 选择 embedding 列
        embed_col = args.embed_col
        if not embed_col or embed_col not in df.columns:
            print("可选的列:", list(df.columns))
            embed_col = input("请输入用于 embedding 的列名: ").strip()
            if embed_col not in df.columns:
                print("[错误] 该列不存在于 CSV 中。退出。")
                sys.exit(1)
        print(f"将使用列 '{embed_col}' 生成 embedding。\n")

        # 创建 schema
        schema = CollectionSchema(
            fields, "Auto-inferred or default schema", enable_dynamic_field=True
        )

        # 创建集合并设置索引
        collection = create_collection_with_index(args.collection, schema)

        # 批量处理数据
        process_data_in_batches(
            df, collection, embed_col, fields, args.batch_size, embedding_function
        )
        logging.info("Data import completed successfully")

        # 确保集合已加载到内存
        collection.load()

        # 测试搜索
        test_search(collection, df, embed_col, primary_key, embedding_function)

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        connections.disconnect("default")


if __name__ == "__main__":
    create_milvus_collection()
