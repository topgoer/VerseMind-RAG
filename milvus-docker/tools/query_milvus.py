import argparse
import os
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer
import openai

# 配置
MILVUS_HOST = 'localhost'
MILVUS_PORT = 19530
COLLECTION_NAME = 'concepts_only_name'
VECTOR_FIELD = 'vector'
EMBED_MODEL = 'BAAI/bge-m3'

# LLM 配置（可选）
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def get_embedding(text, model):
    return model.encode([text])[0]


def query_milvus(query, topk, fields, model, collection):
    query_vec = get_embedding(query, model)
    results = collection.search(
        data=[query_vec],
        anns_field=VECTOR_FIELD,
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=topk,
        output_fields=fields
    )
    hits = []
    for hit in results[0]:
        hits.append({field: hit.entity.get(field) for field in fields})
    return hits


def query_by_id(id_value, id_field, fields, collection):
    expr = f"{id_field} == '{id_value}'"
    print(f"[DEBUG] Milvus expr: {expr}")
    results = collection.query(expr, output_fields=fields)
    if not results:
        # 如果查无结果，尝试模糊查找并打印所有相关主键
        like_expr = f"{id_field} like '{id_value}%'"
        print(f"[DEBUG] No exact match, try: {like_expr}")
        like_results = collection.query(like_expr, output_fields=[id_field])
        for r in like_results:
            print(f"[DEBUG] Similar key: {repr(r[id_field])}, length: {len(r[id_field])}")
    return results


def llm_summarize(results, query, llm_model="gpt-3.5-turbo"):
    if not OPENAI_API_KEY:
        print("[WARN] 未设置 OPENAI_API_KEY，无法调用 LLM。仅输出原始结果。")
        return results
    openai.api_key = OPENAI_API_KEY
    context = "\n".join([str(r) for r in results])
    prompt = f"已检索到如下内容：\n{context}\n\n请基于上述内容，简要回答用户问题：{query}"
    response = openai.ChatCompletion.create(
        model=llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512
    )
    return response.choices[0].message.content.strip()


def interactive_mode(collection, model, fields, id_field, use_llm):
    print("进入 Milvus 向量检索交互模式，输入 q 退出。")
    while True:
        query = input("请输入检索文本或主键ID：").strip()
        if query.lower() == 'q':
            break
        if query.isdigit() or (id_field and query.startswith(id_field)):
            results = query_by_id(query, id_field, fields, collection)
        else:
            results = query_milvus(query, 5, fields, model, collection)
        print("检索结果：")
        for r in results:
            print(r)
        if use_llm:
            print("\n[LLM 总结/问答]")
            print(llm_summarize(results, query))


def main():
    parser = argparse.ArgumentParser(description="Milvus 向量检索与 LLM 互动工具")
    parser.add_argument('--query', type=str, help='检索文本')
    parser.add_argument('--topk', type=int, default=5, help='返回topK条')
    parser.add_argument('--fields', type=str, default='concept_name', help='输出字段,逗号分隔')
    parser.add_argument('--id', type=str, help='按主键/ID精确查找')
    parser.add_argument('--id-field', type=str, default='concept_id', help='主键字段名')
    parser.add_argument('--interactive', action='store_true', help='进入交互模式')
    parser.add_argument('--llm', action='store_true', help='用 LLM 对检索结果做摘要/问答')
    parser.add_argument('--collection', type=str, default='concepts_only_name', help='Milvus collection 名称')
    args = parser.parse_args()

    # 连接 Milvus
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    collection = Collection(args.collection)

    # 加载嵌入模型
    model = SentenceTransformer(EMBED_MODEL)
    fields = [f.strip() for f in args.fields.split(',')]

    if args.interactive:
        interactive_mode(collection, model, fields, args.id_field, args.llm)
        return

    if args.id:
        results = query_by_id(args.id, args.id_field, fields, collection)
    elif args.query:
        results = query_milvus(args.query, args.topk, fields, model, collection)
    else:
        print("请指定 --query 或 --id 参数，或加 --interactive 进入交互模式。")
        return

    print("检索结果：")
    for r in results:
        print(r)
    if args.llm:
        print("\n[LLM 总结/问答]")
        print(llm_summarize(results, args.query or args.id))

if __name__ == '__main__':
    main()
