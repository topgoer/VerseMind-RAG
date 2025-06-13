import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from pymilvus import connections, utility, Collection

# 配置日志格式，移除时间戳
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # 只显示消息，不显示时间戳和日志级别
)

# 加载环境变量
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="List all Milvus collections")
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("MILVUS_HOST", "localhost"),
        help="Milvus server address",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MILVUS_PORT", "19530")),
        help="Milvus server port",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        # 连接到 Milvus
        connections.connect(host=args.host, port=args.port)
        logging.info(f"Connected to Milvus at {args.host}:{args.port}")

        # 获取所有集合
        collections = utility.list_collections()
        logging.info(f"Found {len(collections)} collections:")

        # 显示每个集合的详细信息
        for i, collection_name in enumerate(collections, 1):
            collection = Collection(collection_name)
            fields = collection.schema.fields

            logging.info(f"\n{i}. Collection: {collection_name}")
            logging.info("   Fields:")
            for field in fields:
                field_info = f"   - {field.name}: {field.dtype}"
                if hasattr(field, "max_length"):
                    field_info += f" (max_length={field.max_length})"
                if field.is_primary:
                    field_info += " [Primary Key]"
                logging.info(field_info)

            logging.info("   Statistics:")
            logging.info(f"   - Number of entities: {collection.num_entities}")

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        connections.disconnect("default")


if __name__ == "__main__":
    main()
