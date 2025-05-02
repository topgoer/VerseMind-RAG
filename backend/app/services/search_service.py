import os
import json
import datetime
import uuid
import numpy as np
from typing import Dict, List, Any, Optional

class SearchService:
    """语义搜索服务，支持基于向量相似度的检索"""
    
    def __init__(self, indices_dir="storage/indices", embeddings_dir="storage/embeddings", results_dir="storage/results"):
        self.indices_dir = indices_dir
        self.embeddings_dir = embeddings_dir
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
    
    def search(self, index_id: str, query: str, top_k: int = 3, similarity_threshold: float = 0.7, min_chars: int = 100) -> Dict[str, Any]:
        """
        执行语义搜索
        
        参数:
            index_id: 索引ID
            query: 查询文本
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
            min_chars: 最小字符数
        
        返回:
            包含搜索结果的字典
        """
        # 查找索引文件
        index_file = self._find_index_file(index_id)
        if not index_file:
            raise FileNotFoundError(f"找不到ID为{index_id}的索引")
        
        # 读取索引数据
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        # 获取文档ID和嵌入ID
        document_id = index_data.get("document_id", "")
        embedding_id = index_data.get("embedding_id", "")
        vector_db = index_data.get("vector_db", "")
        
        # 查找嵌入文件
        embedding_file = self._find_embedding_file(document_id, embedding_id)
        if not embedding_file:
            raise FileNotFoundError(f"找不到文档ID {document_id} 的嵌入数据")
        
        # 读取嵌入数据
        with open(embedding_file, "r", encoding="utf-8") as f:
            embedding_data = json.load(f)
        
        # 生成查询向量
        query_vector = self._generate_query_vector(query, embedding_data.get("provider", ""), embedding_data.get("model", ""))
        
        # 执行向量搜索
        search_results = self._vector_search(query_vector, embedding_data, vector_db, top_k, similarity_threshold, min_chars)
        
        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        search_id = str(uuid.uuid4())[:8]
        
        # 构建搜索结果
        result = {
            "search_id": search_id,
            "timestamp": timestamp,
            "query": query,
            "index_id": index_id,
            "document_id": document_id,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "min_chars": min_chars,
            "results": search_results
        }
        
        # 保存搜索结果
        result_file = f"search_{search_id}_{timestamp}.json"
        result_path = os.path.join(self.results_dir, result_file)
        
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 返回结果
        result["result_file"] = result_file
        return result
    
    def _find_index_file(self, index_id: str) -> Optional[str]:
        """查找指定ID的索引文件"""
        if os.path.exists(self.indices_dir):
            for filename in os.listdir(self.indices_dir):
                if index_id in filename and filename.endswith(".json"):
                    return os.path.join(self.indices_dir, filename)
        return None
    
    def _find_embedding_file(self, document_id: str, embedding_id: str = None) -> Optional[str]:
        """查找指定文档的嵌入文件"""
        if os.path.exists(self.embeddings_dir):
            for filename in os.listdir(self.embeddings_dir):
                if filename.startswith(document_id) and filename.endswith("_embeddings.json"):
                    # 如果指定了嵌入ID，则进一步匹配
                    if embedding_id:
                        with open(os.path.join(self.embeddings_dir, filename), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if data.get("embedding_id") == embedding_id:
                                return os.path.join(self.embeddings_dir, filename)
                    else:
                        return os.path.join(self.embeddings_dir, filename)
        return None
    
    def _generate_query_vector(self, query: str, provider: str, model: str) -> List[float]:
        """生成查询文本的向量表示"""
        # 在实际实现中，这里会调用相应的嵌入模型API
        # 这里使用随机向量模拟
        
        # 根据提供商和模型确定向量维度
        dimensions = 1024  # 默认维度
        
        if provider == "openai":
            if model == "text-embedding-3-small":
                dimensions = 1536
            elif model == "text-embedding-3-large":
                dimensions = 3072
        elif provider == "ollama":
            if model == "bge-large":
                dimensions = 1024
        
        # 生成随机向量并归一化
        vector = np.random.randn(dimensions)
        vector = vector / np.linalg.norm(vector)
        
        return vector.tolist()
    
    def _vector_search(self, query_vector: List[float], embedding_data: Dict[str, Any], vector_db: str, top_k: int, similarity_threshold: float, min_chars: int) -> List[Dict[str, Any]]:
        """执行向量搜索"""
        # 在实际实现中，这里会使用向量数据库进行搜索
        # 这里使用模拟数据
        
        embeddings = embedding_data.get("embeddings", [])
        
        # 计算相似度（模拟）
        results = []
        for i, emb in enumerate(embeddings):
            # 模拟相似度计算
            similarity = 0.95 - (i * 0.05)  # 相似度递减
            
            # 检查相似度阈值
            if similarity < similarity_threshold:
                continue
                
            # 检查文本长度
            text = emb.get("text", "")
            if len(text) < min_chars:
                continue
            
            # 添加到结果
            results.append({
                "id": emb.get("id", f"result_{i}"),
                "text": text,
                "similarity": similarity,
                "source": f"文档 {embedding_data.get('document_id', '')}"
            })
            
            # 限制结果数量
            if len(results) >= top_k:
                break
        
        return results
