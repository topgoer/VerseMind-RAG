import argparse
from pymilvus import connections, utility

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="删除指定的 Milvus collection")
    parser.add_argument(
        "--collection", type=str, required=True, help="要删除的 collection 名称"
    )
    parser.add_argument("--host", type=str, default="localhost", help="Milvus host")
    parser.add_argument("--port", type=int, default=19530, help="Milvus port")
    args = parser.parse_args()

    connections.connect(host=args.host, port=args.port)
    if utility.has_collection(args.collection):
        utility.drop_collection(args.collection)
        print(f"Collection {args.collection} 已删除")
    else:
        print(f"Collection {args.collection} 不存在")
