import os
import json
import datetime
import uuid
import numpy as np
from typing import Dict, List, Any, Optional
from enum import Enum
from pymilvus import connections, utility, Collection, DataType, FieldSchema, CollectionSchema
from app.core.config import settings

class VectorDBProvider(str, Enum):
    FAISS = "faiss"
    CHROMA = "chroma"
    MILVUS = "milvus"

class VectorDBConfig:
    """
    Configuration for vector databases
    """
    def __init__(self, provider: str, index_mode: str):
        self.provider = provider
        self.index_mode = index_mode
        # FAISS specific settings
        if provider == VectorDBProvider.FAISS.value:
            self.index_type = settings.FAISS_INDEX_TYPE
            self.metric = settings.FAISS_METRIC
        # Chroma specific settings
        elif provider == VectorDBProvider.CHROMA.value:
            self.collection_name = settings.CHROMA_COLLECTION_NAME
            self.distance_function = settings.CHROMA_DISTANCE_FUNCTION
        # Milvus specific settings
        elif provider == VectorDBProvider.MILVUS.value:
            self.milvus_uri = os.getenv("MILVUS_URI", "127.0.0.1:19530")
        
        # Common settings
        self.persist_directory = settings.VECTOR_STORE_PERSIST_DIR

    def get_index_params(self):
        """Get index parameters based on vector DB provider"""
        if self.provider == VectorDBProvider.MILVUS.value:
            return {"metric_type": "COSINE"}
        elif self.provider == VectorDBProvider.FAISS.value:
            metric_map = {
                "cosine": "METRIC_INNER_PRODUCT",
                "l2": "METRIC_L2",
                "ip": "METRIC_INNER_PRODUCT"
            }
            return {"metric_type": metric_map.get(self.metric, "METRIC_INNER_PRODUCT")}
        elif self.provider == VectorDBProvider.CHROMA.value:
            return {"distance_function": self.distance_function}

class IndexService:
    """向量索引服务，支持FAISS和Chroma向量数据库"""
    
    def __init__(self, embeddings_dir="storage/embeddings", indices_dir="storage/indices"):
        self.embeddings_dir = embeddings_dir
        self.indices_dir = indices_dir
        os.makedirs(indices_dir, exist_ok=True)
    
    def create_index(self, document_id: str, vector_db: str = None, collection_name: str = None, index_name: str = None, embedding_id: str = None, version: str = "1.0") -> Dict[str, Any]:
        """
        创建向量索引
        
        参数:
            document_id: 文档ID
            vector_db: 向量数据库类型 ("faiss", "chroma", "milvus")，如果为None则使用配置文件中的默认值
            collection_name: 集合名称，如果为None则自动生成
            index_name: 索引名称，如果为None则自动生成
            embedding_id: 嵌入ID (用于查找对应的嵌入文件)，如果为None则使用最新的嵌入
            version: 索引版本
        
        返回:
            包含索引结果的字典
        """
        # 使用配置中的默认向量数据库类型，如果未指定
        if vector_db is None:
            vector_db = settings.VECTOR_STORE_TYPE
        
        # 如果未指定嵌入ID，则尝试查找最新的嵌入
        if embedding_id is None:
            # 这里应实现查找最新嵌入的逻辑
            # 目前暂不实现此功能，抛出错误
            raise ValueError("必须指定嵌入ID")
        
        # 如果未指定集合名称或索引名称，则自动生成
        if collection_name is None:
            collection_name = f"col_{document_id[:10]}"
        if index_name is None:
            index_name = f"idx_{embedding_id[:8]}"
        
        print(f"[SERVICE LOG IndexService.create_index] Called with: document_id='{document_id}', vector_db='{vector_db}', collection_name='{collection_name}', index_name='{index_name}', embedding_id='{embedding_id}', version='{version}'")
        
        # 检查嵌入是否存在
        embedding_file = self._find_embedding_file(document_id, embedding_id)
        if not embedding_file:
            error_message = f"请先为文档ID {document_id} (使用嵌入ID: {embedding_id}) 创建嵌入向量"
            print(f"[SERVICE ERROR IndexService.create_index] {error_message}")
            raise FileNotFoundError(error_message)
        
        print(f"[SERVICE LOG IndexService.create_index] Found embedding file: {embedding_file}")
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
        if vector_db == VectorDBProvider.FAISS.value:
            index_info = self._create_faiss_index(embeddings, collection_name, index_name)
        elif vector_db == VectorDBProvider.CHROMA.value:
            index_info = self._create_chroma_index(embeddings, collection_name, index_name)
        elif vector_db == VectorDBProvider.MILVUS.value:
            # use Milvus for index
            config = VectorDBConfig(provider=VectorDBProvider.MILVUS.value, index_mode=index_name)
            milvus_result = self._index_to_milvus(embeddings, collection_name, config)
            index_info = milvus_result  # contains collection_name and index_size
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
    
    def delete_index(self, index_id: str) -> Dict[str, Any]:
        """
        删除指定ID的索引
        
        参数:
            index_id: 索引ID
            
        返回:
            包含删除结果的字典
        """
        # 查找索引文件
        index_file = self._find_index_file(index_id)
        if not index_file:
            raise FileNotFoundError(f"找不到ID为 {index_id} 的索引")
        
        # 读取索引数据，保留一些信息用于返回
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        # 获取必要信息
        document_id = index_data.get("document_id", "")
        vector_db = index_data.get("vector_db", "")
        collection_name = index_data.get("collection_name", "")
        index_name = index_data.get("index_name", "")
        
        # 根据向量库类型执行清理操作
        try:
            if vector_db == VectorDBProvider.MILVUS.value:
                # 如果是Milvus，可能需要删除集合
                try:
                    connections.connect(alias="default", uri=VectorDBConfig("default").milvus_uri)
                    if utility.has_collection(collection_name):
                        utility.drop_collection(collection_name)
                except Exception as e:
                    print(f"Milvus清理错误 (非致命): {str(e)}")
                finally:
                    try:
                        connections.disconnect("default")
                    except:
                        pass
            
            # 删除索引文件
            os.remove(index_file)
            
            # 返回删除成功信息
            return {
                "status": "success",
                "message": f"索引 {index_id} 已删除",
                "index_id": index_id,
                "document_id": document_id,
                "vector_db": vector_db,
                "collection_name": collection_name,
                "index_name": index_name
            }
        except Exception as e:
            raise Exception(f"删除索引时发生错误: {str(e)}")
    
    def _find_embedding_file(self, document_id: str, embedding_id: str) -> Optional[str]:
        """查找指定文档和嵌入ID的嵌入文件"""
        print(f"[SERVICE LOG IndexService._find_embedding_file] Searching for embedding file with document_id='{document_id}' and embedding_id='{embedding_id}' in directory='{self.embeddings_dir}'")
        if os.path.exists(self.embeddings_dir):
            print(f"[SERVICE LOG IndexService._find_embedding_file] Directory '{self.embeddings_dir}' exists. Listing files...")
            for filename in os.listdir(self.embeddings_dir):
                print(f"[SERVICE LOG IndexService._find_embedding_file] Checking file: '{filename}'")
                # First, check if document_id is in filename and it's a .json file ending with _embedded.json
                if document_id in filename and filename.endswith("_embedded.json"):
                    print(f"[SERVICE LOG IndexService._find_embedding_file] Candidate file (matches document_id and suffix): '{filename}'")
                    file_path = os.path.join(self.embeddings_dir, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            embedding_data = json.load(f)
                        # Now check if the embedding_id inside the JSON matches the target embedding_id
                        internal_embedding_id = embedding_data.get("embedding_id") # Or however it's named in your JSON
                        if internal_embedding_id == embedding_id:
                            print(f"[SERVICE LOG IndexService._find_embedding_file] Match found: Internal embedding_id ('{internal_embedding_id}') matches target ('{embedding_id}'). File: '{file_path}'")
                            return file_path
                        else:
                            print(f"[SERVICE LOG IndexService._find_embedding_file] File '{filename}' matches document_id, but its internal embedding_id ('{internal_embedding_id}') does not match target ('{embedding_id}').")
                    except json.JSONDecodeError:
                        print(f"[SERVICE WARNING IndexService._find_embedding_file] Could not decode JSON from candidate file: '{filename}'")
                    except Exception as e:
                        print(f"[SERVICE WARNING IndexService._find_embedding_file] Error reading or processing candidate file '{filename}': {e}")
            print(f"[SERVICE LOG IndexService._find_embedding_file] No matching file found after checking all candidate files in '{self.embeddings_dir}'.")
        else:
            print(f"[SERVICE ERROR IndexService._find_embedding_file] Embeddings directory '{self.embeddings_dir}' does not exist.")
        return None
    
    def _find_index_file(self, index_id: str) -> Optional[str]:
        """查找指定ID的索引文件"""
        print(f"[SERVICE LOG IndexService._find_index_file] Searching for index file with index_id='{index_id}' in directory='{self.indices_dir}'")
        if os.path.exists(self.indices_dir):
            print(f"[SERVICE LOG IndexService._find_index_file] Directory '{self.indices_dir}' exists. Listing files...")
            for filename in os.listdir(self.indices_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.indices_dir, filename)
                    print(f"[SERVICE LOG IndexService._find_index_file] Checking file: '{filename}'")
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            index_data = json.load(f)
                        
                        # Check if the index_id inside the JSON matches the target index_id
                        internal_index_id = index_data.get("index_id")
                        print(f"[SERVICE LOG IndexService._find_index_file] File '{filename}' has internal index_id: '{internal_index_id}'")
                        
                        if internal_index_id == index_id:
                            print(f"[SERVICE LOG IndexService._find_index_file] Match found: File '{filename}' contains index_id='{index_id}'")
                            return file_path
                    except json.JSONDecodeError:
                        print(f"[SERVICE WARNING IndexService._find_index_file] Could not decode JSON from file: '{filename}'")
                    except Exception as e:
                        print(f"[SERVICE WARNING IndexService._find_index_file] Error reading or processing file '{filename}': {str(e)}")
            
            print(f"[SERVICE WARNING IndexService._find_index_file] No index file with index_id='{index_id}' found in '{self.indices_dir}'")
        else:
            print(f"[SERVICE ERROR IndexService._find_index_file] Indices directory '{self.indices_dir}' does not exist")
        return None
    
    def _create_faiss_index(self, embeddings: List[Dict[str, Any]], collection_name: str, index_name: str) -> Dict[str, Any]:
        """创建FAISS索引"""
        try:
            # 获取FAISS配置
            vector_db_config = VectorDBConfig(provider=VectorDBProvider.FAISS.value, index_mode=index_name)
            
            # 提取向量和ID
            vectors = [emb.get("vector", []) for emb in embeddings]
            # 保存IDs以备后续使用，目前未实现
            ids = [emb.get("id", "") for emb in embeddings]
            
            # 配置索引路径
            index_path = os.path.join(vector_db_config.persist_directory, f"{collection_name}_{index_name}.faiss")
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            # 索引信息
            index_info = {
                "type": "faiss",
                "index_type": vector_db_config.index_type,  # 使用配置中的索引类型
                "metric": vector_db_config.metric,          # 使用配置中的度量方法
                "dimensions": len(vectors[0]) if vectors else 0,
                "num_vectors": len(vectors),
                "index_path": index_path
            }
            
            return index_info
        except Exception as e:
            # 应该使用更具体的异常类型，但为保持兼容性先维持现状
            raise ValueError(f"FAISS索引创建失败: {str(e)}")
    
    def _create_chroma_index(self, embeddings: List[Dict[str, Any]], collection_name: str, index_name: str) -> Dict[str, Any]:
        """创建Chroma索引"""
        try:
            # 获取Chroma配置
            vector_db_config = VectorDBConfig(provider=VectorDBProvider.CHROMA.value, index_mode=index_name)
            
            # 提取向量、ID和文本
            vectors = [emb.get("vector", []) for emb in embeddings]
            # 这些变量目前未使用，保留以备后续实现
            # 实际实现时可能需要使用
            _ = [emb.get("id", "") for emb in embeddings]
            _ = [emb.get("text", "") for emb in embeddings]
            
            # 配置索引路径
            index_path = os.path.join(vector_db_config.persist_directory, f"{collection_name}_{index_name}")
            os.makedirs(index_path, exist_ok=True)
            
            # 索引信息
            index_info = {
                "type": "chroma",
                "collection_name": collection_name if collection_name else vector_db_config.collection_name,
                "distance_function": vector_db_config.distance_function,
                "dimensions": len(vectors[0]) if vectors else 0,
                "num_vectors": len(vectors),
                "index_path": index_path
            }
            
            return index_info
        except Exception as e:
            # 应该使用更具体的异常类型，但为保持兼容性先维持现状
            raise ValueError(f"Chroma索引创建失败: {str(e)}")
    
    def _index_to_milvus(self, embeddings: List[Dict[str, Any]], collection_name: str, config: VectorDBConfig) -> Dict[str, Any]:
        """
        Insert embeddings into Milvus collection
        """
        # connect to Milvus
        connections.connect(alias="default", uri=config.milvus_uri)
        try:
            # prepare schema
            dim = len(embeddings[0].get("vector", [])) if embeddings else 0
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim, params=config.get_index_params()),
            ]
            schema = CollectionSchema(fields=fields, description=f"Milvus collection for {collection_name}")
            collection = Collection(name=collection_name, schema=schema)
            # insert data
            vectors = [emb.get("vector", []) for emb in embeddings]
            insert_result = collection.insert([vectors])
            # create index
            collection.create_index(field_name="vector", index_params=config.get_index_params())
            collection.load()
            return {
                "type": "milvus",
                "collection_name": collection_name,
                "dimensions": dim,
                "num_vectors": len(vectors),
                "index_size": len(insert_result.primary_keys)
            }
        except Exception as e:
            raise ValueError(f"Milvus索引创建失败: {str(e)}")
        finally:
            connections.disconnect("default")
