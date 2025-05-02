import os
import json
import datetime
import uuid
import numpy as np
from typing import Dict, List, Any, Optional

class IndexService:
    """向量索引服务，支持FAISS和Chroma向量数据库"""
    
    def __init__(self, embeddings_dir="storage/embeddings", indices_dir="storage/indices"):
        self.embeddings_dir = embeddings_dir
        self.indices_dir = indices_dir
        os.makedirs(indices_dir, exist_ok=True)
    
    def create_index(self, document_id: str, vector_db: str, collection_name: str, index_name: str, version: str = "1.0") -> Dict[str, Any]:
        """
        创建向量索引
        
        参数:
            document_id: 文档ID
            vector_db: 向量数据库类型 ("faiss", "chroma")
            collection_name: 集合名称
            index_name: 索引名称
            version: 索引版本
        
        返回:
            包含索引结果的字典
        """
        # 检查嵌入是否存在
        embedding_file = self._find_embedding_file(document_id)
        if not embedding_file:
            raise FileNotFoundError(f"请先为文档ID {document_id} 创建嵌入向量")
        
        # 读取嵌入数据
        with open(embedding_file, "r", encoding="utf-8") as f:
            embedding_data = json.load(f)
        
        # 提取嵌入向量
        embeddings = embedding_data.get("embeddings", [])
        if not embeddings:
            raise ValueError("嵌入数据为空")
        
        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        index_id = str(uuid.uuid4())[:8]
        
        # 根据向量数据库类型创建索引
        if vector_db == "faiss":
            index_info = self._create_faiss_index(embeddings, collection_name, index_name)
        elif vector_db == "chroma":
            index_info = self._create_chroma_index(embeddings, collection_name, index_name)
        else:
            raise ValueError(f"不支持的向量数据库类型: {vector_db}")
        
        # 构建索引结果
        result = {
            "document_id": document_id,
            "index_id": index_id,
            "timestamp": timestamp,
            "vector_db": vector_db,
            "collection_name": collection_name,
            "index_name": index_name,
            "version": version,
            "dimensions": embedding_data.get("dimensions", 0),
            "total_vectors": len(embeddings),
            "embedding_id": embedding_data.get("embedding_id", ""),
            "embedding_model": embedding_data.get("model", ""),
            "index_info": index_info
        }
        
        # 保存索引结果
        result_file = f"{document_id}_{timestamp}_{vector_db}_{index_name}_v{version}.json"
        result_path = os.path.join(self.indices_dir, result_file)
        
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 返回结果
        result["result_file"] = result_file
        return result
    
    def list_indices(self) -> List[Dict[str, Any]]:
        """获取所有索引列表"""
        indices = []
        
        if os.path.exists(self.indices_dir):
            for filename in os.listdir(self.indices_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.indices_dir, filename)
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        index_data = json.load(f)
                    
                    indices.append({
                        "document_id": index_data.get("document_id", ""),
                        "index_id": index_data.get("index_id", ""),
                        "timestamp": index_data.get("timestamp", ""),
                        "vector_db": index_data.get("vector_db", ""),
                        "collection_name": index_data.get("collection_name", ""),
                        "index_name": index_data.get("index_name", ""),
                        "version": index_data.get("version", ""),
                        "total_vectors": index_data.get("total_vectors", 0),
                        "file": filename
                    })
        
        return indices
    
    def update_index(self, index_id: str, version: str) -> Dict[str, Any]:
        """更新索引版本"""
        # 查找索引文件
        index_file = self._find_index_file(index_id)
        if not index_file:
            raise FileNotFoundError(f"找不到ID为{index_id}的索引")
        
        # 读取索引数据
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        # 更新版本和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        index_data["version"] = version
        index_data["timestamp"] = timestamp
        
        # 保存更新后的索引
        document_id = index_data.get("document_id", "")
        vector_db = index_data.get("vector_db", "")
        index_name = index_data.get("index_name", "")
        
        new_file = f"{document_id}_{timestamp}_{vector_db}_{index_name}_v{version}.json"
        new_path = os.path.join(self.indices_dir, new_file)
        
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        # 返回结果
        index_data["result_file"] = new_file
        return index_data
    
    def _find_embedding_file(self, document_id: str) -> Optional[str]:
        """查找指定文档的嵌入文件"""
        if os.path.exists(self.embeddings_dir):
            for filename in os.listdir(self.embeddings_dir):
                if filename.startswith(document_id) and filename.endswith("_embeddings.json"):
                    return os.path.join(self.embeddings_dir, filename)
        return None
    
    def _find_index_file(self, index_id: str) -> Optional[str]:
        """查找指定ID的索引文件"""
        if os.path.exists(self.indices_dir):
            for filename in os.listdir(self.indices_dir):
                if index_id in filename and filename.endswith(".json"):
                    return os.path.join(self.indices_dir, filename)
        return None
    
    def _create_faiss_index(self, embeddings: List[Dict[str, Any]], collection_name: str, index_name: str) -> Dict[str, Any]:
        """创建FAISS索引"""
        try:
            # 在实际实现中，这里会使用FAISS库创建索引
            # 这里使用模拟数据
            
            # 提取向量和ID
            vectors = [emb.get("vector", []) for emb in embeddings]
            ids = [emb.get("id", "") for emb in embeddings]
            
            # 模拟索引信息
            index_info = {
                "type": "faiss",
                "index_type": "IndexFlatL2",  # 或者 "IndexIVFFlat", "IndexHNSW" 等
                "dimensions": len(vectors[0]) if vectors else 0,
                "num_vectors": len(vectors),
                "index_path": f"storage/indices/{collection_name}_{index_name}.faiss"
            }
            
            return index_info
        except Exception as e:
            raise Exception(f"FAISS索引创建失败: {str(e)}")
    
    def _create_chroma_index(self, embeddings: List[Dict[str, Any]], collection_name: str, index_name: str) -> Dict[str, Any]:
        """创建Chroma索引"""
        try:
            # 在实际实现中，这里会使用Chroma库创建索引
            # 这里使用模拟数据
            
            # 提取向量、ID和文本
            vectors = [emb.get("vector", []) for emb in embeddings]
            ids = [emb.get("id", "") for emb in embeddings]
            texts = [emb.get("text", "") for emb in embeddings]
            
            # 模拟索引信息
            index_info = {
                "type": "chroma",
                "collection_name": collection_name,
                "dimensions": len(vectors[0]) if vectors else 0,
                "num_vectors": len(vectors),
                "index_path": f"storage/indices/{collection_name}_{index_name}"
            }
            
            return index_info
        except Exception as e:
            raise Exception(f"Chroma索引创建失败: {str(e)}")
