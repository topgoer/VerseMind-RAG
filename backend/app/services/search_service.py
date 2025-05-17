import os
import json
import datetime
import uuid
import numpy as np
import logging
from typing import Dict, List, Any, Optional
from app.core.logger import get_logger_with_env_level

class SearchService:
    """语义搜索服务，支持基于向量相似度的检索"""
    
    def __init__(self, indices_dir=os.path.join("storage", "indices"), 
                 embeddings_dir=os.path.join("backend", "04-embedded-docs"), 
                 results_dir=os.path.join("storage", "results")):
        self.logger = get_logger_with_env_level("SearchService")

        # 使用绝对路径
        self.storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        
        # 设置标准目录路径
        self.indices_dir = os.path.join(self.storage_dir, indices_dir)
        self.embeddings_dir = os.path.join(self.storage_dir, embeddings_dir)
        self.results_dir = os.path.join(self.storage_dir, results_dir)
        
        # 确保主要目录存在
        os.makedirs(self.indices_dir, exist_ok=True)
        os.makedirs(self.embeddings_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Ensure _initialized is a class-level attribute
        if not hasattr(SearchService, '_initialized'):
            self.logger.debug(f"Using indices_dir: {self.indices_dir}")
            self.logger.debug(f"Using embeddings_dir: {self.embeddings_dir}")
            self.logger.debug(f"Using results_dir: {self.results_dir}")
            SearchService._initialized = True
    
    def search(self, index_id: str, query: str, top_k: int = 3, similarity_threshold: float = 0.5, min_chars: int = 100) -> Dict[str, Any]:
        """
        执行语义搜索
        
        参数:
            index_id: 索引ID
            query: 查询文本
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值 (降低为0.5以提高召回率)
            min_chars: 最小字符数
        
        返回:
            包含搜索结果的字典
        """
        self.logger.debug(f"Starting search with index_id={index_id}, query={query}, top_k={top_k}, similarity_threshold={similarity_threshold} (lower threshold increases results)")
        
        search_info = {
            "params": {
                "index_id": index_id,
                "query": query,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "min_chars": min_chars
            },
            "timing": {},
            "status": {}
        }
        
        start_time = datetime.datetime.now()
        
        # 查找索引文件
        self.logger.debug(f"Looking for index file with ID={index_id}")
        index_file = self._find_index_file(index_id)
        if not index_file:
            error_msg = f"找不到ID为{index_id}的索引"
            self.logger.error(error_msg)
            search_info["status"]["error"] = error_msg
            raise FileNotFoundError(error_msg)
        
        search_info["status"]["index_file_found"] = True
        search_info["index_file_path"] = index_file
        
        # 读取索引数据
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            # 获取文档ID、向量数据库类型和其他索引信息
            document_id = index_data.get("document_id", "")
            vector_db = index_data.get("vector_db", "")
            
            # Get document filename directly from index_data or try to extract it from embedded data
            document_filename = index_data.get("document_filename", "")
            if not document_filename and "document_id" in index_data:
                # Try to extract filename from document_id (which might contain filename info)
                doc_id = index_data["document_id"]
                if isinstance(doc_id, str) and "_" in doc_id:
                    # Try to parse a document name from complex ID format like "filename_timestamp_hash"
                    try:
                        parts = doc_id.split("_")
                        if len(parts) >= 3:  # If it has the expected format
                            document_filename = "_".join(parts[:-2])  # Extract everything before timestamp_hash
                            self.logger.debug(f"Extracted document_filename '{document_filename}' from document_id '{doc_id}'")
                    except Exception as e:
                        self.logger.error(f"Error extracting filename from document_id '{doc_id}': {str(e)}")
            
            search_info["document_id"] = document_id
            search_info["vector_db"] = vector_db
            search_info["document_filename"] = document_filename
            
            self.logger.debug(f"Found index for document_id={document_id}, document_filename={document_filename}, vector_db={vector_db}")
        except Exception as e:
            error_msg = f"读取索引文件失败: {str(e)}"
            self.logger.error(error_msg)
            search_info["status"]["error"] = error_msg
            raise ValueError(error_msg)
        
        # 记录向量模型信息
        embedding_model = index_data.get("embedding_model", "unknown")
        search_info["embedding_model"] = embedding_model
        
        # 生成查询向量
        # 完全重写模型与提供商解析逻辑，以正确处理不同格式的嵌入模型名称
        embedding_model_str = index_data.get("embedding_model", "")
        self.logger.debug(f"Original embedding_model string: '{embedding_model_str}'")
        
        # 处理空值情况
        if not embedding_model_str:
            provider = "default"
            model = "default"
        else:
            # 显式处理已知格式
            known_providers = ["openai", "bedrock", "huggingface", "ollama", "deepseek", "baidu", "baai", "default"]
            
            try:
                # 首先检查嵌入文件，这是最可靠的信息源
                embedding_file_path = self._find_embedding_file(index_data.get("document_id", ""), index_data.get("embedding_id", ""))
                if embedding_file_path:
                    self.logger.debug(f"Using embedding file path to detect provider: {embedding_file_path}")
                    file_name = os.path.basename(embedding_file_path)
                    
                    # 从文件名中提取提供商信息
                    provider_found = False
                    for p in known_providers:
                        if f"_{p}_" in file_name:
                            provider = p
                            provider_found = True
                            # 提取模型名称
                            parts = file_name.split(f"_{p}_", 1)
                            if len(parts) > 1:
                                model_part = parts[1]
                                timestamp_index = model_part.find("_202")
                                if timestamp_index > 0:
                                    model = model_part[:timestamp_index]
                                else:
                                    model = model_part.split("_embedded.json")[0]
                            else:
                                model = embedding_model_str
                            self.logger.debug(f"Extracted provider='{provider}' and model='{model}' from file name")
                            break
                            
                    # 如果找到了文件但没找到提供商，尝试从嵌入文件内容中获取
                    if not provider_found:
                        try:
                            with open(embedding_file_path, "r", encoding="utf-8") as f:
                                embed_data = json.load(f)
                                if "provider" in embed_data:
                                    provider = embed_data["provider"]
                                    if "model" in embed_data:
                                        model = embed_data["model"]
                                    self.logger.debug(f"Extracted provider='{provider}' and model='{model}' from embedding file content")
                                    provider_found = True
                        except Exception as e:
                            self.logger.error(f"Error reading embedding file content: {str(e)}")
                
                # 如果通过文件路径和内容未找到提供商，尝试通过模型名称推断
                if 'provider' not in locals() or not provider:
                    # 导入嵌入服务以获取可用模型列表
                    from app.services.embed_service import EmbedService
                    embed_service = EmbedService()
                    
                    # 获取所有支持的嵌入模型
                    try:
                        models_info = embed_service.get_embedding_models()
                        if "providers" in models_info:
                            # 特殊处理 BGE 模型（直接分配给 ollama 提供商）
                            if embedding_model_str.startswith("bge-"):
                                provider = "ollama"
                                model = embedding_model_str
                                self.logger.debug(f"Special handling: BGE model '{model}' assigned to provider '{provider}'")
                            else:
                                # 在所有提供商的模型列表中查找匹配的模型名称
                                for provider_name, provider_models in models_info["providers"].items():
                                    for model_info in provider_models:
                                        if model_info.get("id") == embedding_model_str:
                                            provider = provider_name
                                            model = embedding_model_str
                                            self.logger.debug(f"Found model '{model}' in provider '{provider}' model list")
                                            break
                                    if 'provider' in locals() and provider:
                                        break
                    except Exception as e:
                        self.logger.error(f"Error getting embedding models: {str(e)}")
                
                # 如果仍然没有提供商信息，尝试从模型名称前缀推断
                if 'provider' not in locals() or not provider:
                    # 检查是否是 {provider}-* 格式
                    for p in known_providers:
                        if embedding_model_str.startswith(f"{p}-"):
                            provider = p
                            model = embedding_model_str[len(f"{p}-"):]
                            self.logger.debug(f"Extracted provider='{provider}' from model name prefix")
                            break
                    
                    # 特殊处理bge模型 - 显式检查是否是 "bge-" 开头的模型
                    if ('provider' not in locals() or not provider) and embedding_model_str.startswith("bge-"):
                        provider = "ollama"  # 显式为 bge 模型指定 ollama 提供商
                        model = embedding_model_str
                        self.logger.debug(f"Special handling for BGE model: Using provider='{provider}' with model='{model}'")
                    # 如果没有找到匹配的提供商，使用默认提供商
                    elif 'provider' not in locals() or not provider:
                        # 尝试判断是否是类似 "bge-m3:latest" 这样的本地模型名称
                        if ":" in embedding_model_str:
                            provider = "ollama"  # 对于带冒号的格式，通常是本地模型
                        else:
                            provider = "default"
                        model = embedding_model_str
                        self.logger.debug(f"No provider identified. Using provider='{provider}' with model='{model}'")
            except Exception as e:
                self.logger.error(f"Error during provider/model extraction: {str(e)}")
                provider = "default"
                model = embedding_model_str
                        
        
        vector_start_time = datetime.datetime.now()
        self.logger.debug(f"Using provider='{provider}' and model='{model}' for query vector generation")
        query_vector = self._generate_query_vector(query, provider, model)
        vector_time = datetime.datetime.now() - vector_start_time
        
        search_info["timing"]["vector_generation"] = vector_time.total_seconds()
        search_info["vector_dimensions"] = len(query_vector)
        
        # 执行向量搜索
        self.logger.debug(f"Performing vector search with {len(query_vector)}-dimensional query vector")
        
        search_start_time = datetime.datetime.now()
        search_results = self._vector_search_from_index(query_vector, index_data, top_k, similarity_threshold, min_chars)
        search_time = datetime.datetime.now() - search_start_time
        
        search_info["timing"]["vector_search"] = search_time.total_seconds()
        search_info["result_count"] = len(search_results)
        
        if search_results:
            search_info["similarity_range"] = {
                "min": min(r["similarity"] for r in search_results),
                "max": max(r["similarity"] for r in search_results),
                "avg": sum(r["similarity"] for r in search_results) / len(search_results)
            }
        
        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        search_id = str(uuid.uuid4())[:8]
        
        total_time = datetime.datetime.now() - start_time
        search_info["timing"]["total"] = total_time.total_seconds()
        
        # 构建搜索结果
        document_filename = search_info.get("document_filename", "")
        self.logger.debug(f"Initial document_filename: {document_filename}, document_id: {document_id}")
        
        # If no document_filename was found, try more advanced extraction methods
        if not document_filename and document_id:
            # 1. Try to create a user-friendly name from document_id
            try:
                # 尝试从document_id提取文件名部分
                if isinstance(document_id, str):
                    # 移除时间戳和哈希部分 (通常格式为: filename_timestamp_hash)
                    parts = document_id.split('_')
                    if len(parts) >= 3:
                        # 检查倒数第二部分是否为时间戳格式 (YYYYMMDD_HHMMSS)
                        timestamp_part = parts[-2]
                        if (len(timestamp_part) == 15 and timestamp_part[8] == '_' and 
                            timestamp_part[:8].isdigit() and timestamp_part[9:].isdigit()):
                            # 这可能是一个时间戳，使用之前的所有部分作为文件名
                            clean_name = '_'.join(parts[:-2])
                            document_filename = clean_name
                            self.logger.debug(f"Extracted document name from ID: {document_filename}")
            except Exception as e:
                self.logger.error(f"Error extracting name from document_id: {str(e)}")
                
            # 2. Try to extract filename from document paths in the results
            if not document_filename:
                try:
                    for result_item in search_results:
                        if result_item.get("metadata") and result_item["metadata"].get("source"):
                            source_path = result_item["metadata"]["source"]
                            if isinstance(source_path, str):
                                # Extract filename from path
                                try:
                                    filename = os.path.basename(source_path)
                                    if filename:
                                        document_filename = filename
                                        search_info["document_filename"] = document_filename
                                        self.logger.debug(f"Successfully extracted filename: {filename} from source path")
                                        break
                                except Exception as inner_e:
                                    self.logger.error(f"Error extracting basename from path {source_path}: {str(inner_e)}")
                except Exception as e:
                    self.logger.error(f"Error extracting document filename from results: {str(e)}")
        
        # 美化文档文件名以更友好的显示
        if document_filename:
            # 移除扩展名
            if '.' in document_filename:
                base_name = os.path.splitext(document_filename)[0]
                document_filename = base_name
                
            # 移除多余的时间戳和ID
            # 常见格式: filename_YYYYMMDD_HHMMSS_hash
            parts = document_filename.split('_')
            if len(parts) >= 4:
                # 检查倒数第三和第二部分是否为时间戳格式
                try:
                    if (parts[-3].isdigit() and len(parts[-3]) == 8 and
                        parts[-2].isdigit() and len(parts[-2]) == 6 and
                        len(parts[-1]) >= 6):  # 最后一部分可能是哈希值
                        document_filename = '_'.join(parts[:-3])
                        self.logger.debug(f"Cleaned document_filename to: {document_filename}")
                except:
                    pass
        
        # Ensure document_filename is not None to avoid serialization issues
        if document_filename is None:
            document_filename = ""
            self.logger.warning(f"document_filename is None, setting to empty string")
            
        # 如果仍然没有有效文件名，至少使用document_id的一部分
        if not document_filename and document_id:
            # 使用document_id的前30个字符，避免过长
            document_filename = document_id[:30]
            if len(document_id) > 30:
                document_filename += "..."
            
        # Enhance display name for Chinese filenames
        if document_filename and ('中文' in document_filename or 
                                  '的' in document_filename or 
                                  '一' in document_filename):
            # 这可能是一个中文文档名，给它添加一个前缀以便更容易识别
            if not document_filename.startswith('文档:'):
                document_filename = f"文档: {document_filename}"
        
        # Final filename for logging
        self.logger.debug(f"Final document_filename: '{document_filename}'")
            
        result = {
            "search_id": search_id,
            "timestamp": timestamp,
            "query": query,
            "index_id": index_id,
            "document_id": document_id,
            "document_filename": document_filename,  # 添加文档文件名
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "min_chars": min_chars,
            "results": search_results,
            "search_info": search_info  # 添加搜索详情
        }
        
        # Add document_filename to search_info for easier access
        result["search_info"]["document_filename"] = document_filename
        
        # 保存搜索结果
        result_file = f"search_{search_id}_{timestamp}.json"
        result_path = os.path.join(self.results_dir, result_file)
        
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"Saved search results to {result_path}")
        except Exception as e:
            self.logger.error(f"Error saving search results: {str(e)}")
        
        # 返回结果
        result["result_file"] = result_file
        
        # 打印搜索结果摘要
        if search_results:
            similarities = [f"{r['similarity']:.4f}" for r in search_results]
            self.logger.debug(f"Found {len(search_results)} results with similarities: {similarities}")
        else:
            self.logger.debug("No results found matching the criteria")
            
        return result
    
    def _find_index_file(self, index_id: str) -> Optional[str]:
        """查找指定ID的索引文件"""
        self.logger.debug(f"Searching for index file with index_id='{index_id}'")
        
        # 优先在索引元数据目录中查找，也在向量数据库目录中查找（兼容旧版本）
        from app.core.config import settings
        vector_db_dir = settings.VECTOR_STORE_PERSIST_DIR if hasattr(settings, 'VECTOR_STORE_PERSIST_DIR') else os.path.join(self.storage_dir, "storage", "vector_db")
        possible_dirs = [self.indices_dir, vector_db_dir]
        
        # 打印搜索目录列表
        self.logger.debug(f"Will search in directories: {possible_dirs}")
            
        for dir_path in possible_dirs:
            self.logger.debug(f"Checking directory: {dir_path}")
            
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.endswith(".json"):
                        file_path = os.path.join(dir_path, filename)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                index_data = json.load(f)
                            
                            # Check if the index_id inside the JSON matches the target index_id
                            internal_index_id = index_data.get("index_id")
                            if internal_index_id == index_id:
                                self.logger.debug(f"Match found: File '{filename}' contains index_id='{index_id}'")
                                return file_path
                                
                            # 如果文件名中包含索引ID（备用策略）
                            if index_id in filename:
                                self.logger.debug(f"Match found by filename: '{filename}' contains index_id='{index_id}'")
                                return file_path
                        except json.JSONDecodeError:
                            self.logger.error(f"Could not decode JSON from file: '{filename}'")
                        except Exception as e:
                            self.logger.error(f"Error reading file '{filename}': {str(e)}")
                
                self.logger.debug(f"No index file with index_id='{index_id}' found in {dir_path}")
            else:
                self.logger.debug(f"Indices directory '{dir_path}' does not exist")
                
        return None
    
    def _find_embedding_file(self, document_id: str, embedding_id: str = None) -> Optional[str]:
        """查找指定文档的嵌入文件"""
        self.logger.debug(f"Searching for embedding file with document_id='{document_id}' and embedding_id='{embedding_id}'")
        
        # 只在主嵌入目录中查找
        possible_dirs = [self.embeddings_dir]
        
        # 打印搜索目录列表
        self.logger.debug(f"Will search in directory: {self.embeddings_dir}")
            
        for dir_path in possible_dirs:
            self.logger.debug(f"Checking directory: '{dir_path}'")
            if os.path.exists(dir_path):
                self.logger.debug(f"Directory '{dir_path}' exists. Listing files...")
                for filename in os.listdir(dir_path):
                    # 放宽搜索条件，只要包含document_id和.json后缀即可
                    if document_id in filename and filename.endswith(".json"):
                        self.logger.debug(f"Found potential file: '{filename}'")
                        file_path = os.path.join(dir_path, filename)
                        
                        try:
                            # 检查文件内容
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            
                            # 打印文件的键，便于调试
                            self.logger.debug(f"File '{filename}' contains keys: {list(data.keys())}")
                                
                            # 如果指定了embedding_id，检查是否匹配
                            internal_embedding_id = data.get("embedding_id")
                            if embedding_id and internal_embedding_id and internal_embedding_id != embedding_id:
                                self.logger.debug(f"File '{filename}' has embedding_id='{internal_embedding_id}' which doesn't match target '{embedding_id}'")
                                continue
                            
                            # 检查多种可能的键名
                            if "embeddings" in data:
                                self.logger.debug(f"Match found: File '{filename}' contains 'embeddings' key")
                                return file_path
                                
                            if "vectors" in data:
                                self.logger.debug(f"Match found: File '{filename}' contains 'vectors' key")
                                return file_path
                                
                            if "vector" in data:
                                self.logger.debug(f"Match found: File '{filename}' contains 'vector' key")
                                return file_path
                                
                            # 如果文件名中包含"embedded"或"embedding"，很可能是嵌入文件
                            if "embedded" in filename or "embedding" in filename:
                                self.logger.debug(f"Match found by filename pattern: '{filename}'")
                                return file_path
                                
                        except json.JSONDecodeError:
                            self.logger.error(f"Could not decode JSON from file: '{filename}'")
                        except Exception as e:
                            self.logger.error(f"Error reading file '{filename}': {str(e)}")
                
                self.logger.debug(f"No matching embedding file found in '{dir_path}'")
            else:
                self.logger.debug(f"Embeddings directory '{dir_path}' does not exist")
                
        return None

    def _generate_query_vector(self, query: str, provider: str, model: str) -> List[float]:
        """
        生成查询向量
        
        参数:
            query: 查询文本
            provider: 嵌入向量的提供商 (openai, bedrock, ollama等)
            model: 嵌入向量的模型
            
        返回:
            查询向量 (浮点数列表)
        """
        # 额外处理特殊情况：BGE模型
        if "bge" in model.lower() and provider != "ollama":
            self.logger.debug(f"Converting BGE model provider from '{provider}' to 'ollama'")
            provider = "ollama"
        
        self.logger.debug(f"Generating query vector with provider={provider}, model={model}")
        
        try:
            # 导入嵌入服务
            from app.services.embed_service import EmbedService
            embed_service = EmbedService()
            
            # 使用嵌入服务生成查询向量
            vector = embed_service.generate_embedding_vector(query, provider, model)
            self.logger.debug(f"Generated query vector with dimensions: {len(vector)}")
            return vector
        except Exception as e:
            self.logger.error(f"Error generating query vector: {str(e)}")
            
            # 尝试恢复方案：如果是BGE模型但provider不正确，尝试使用ollama提供商重试
            if "bge" in model.lower() and provider != "ollama":
                self.logger.debug(f"Retrying with provider 'ollama' for BGE model")
                try:
                    from app.services.embed_service import EmbedService
                    embed_service = EmbedService()
                    vector = embed_service.generate_embedding_vector(query, "ollama", model)
                    self.logger.debug(f"Successfully generated vector with ollama provider, dimensions: {len(vector)}")
                    return vector
                except Exception as retry_e:
                    self.logger.error(f"Retry also failed: {str(retry_e)}")
            
            # 如果生成失败，返回一个随机向量
            self.logger.warning("Falling back to random vector for query")
            import numpy as np
            
            # 基于常用模型推断向量维度
            dimensions = 384  # 默认维度
            if provider == "openai":
                dimensions = 1536
            elif "bge" in model.lower():
                dimensions = 1024
                
            # 使用更新的numpy随机生成器API
            rng = np.random.Generator(np.random.PCG64(42))  # 固定种子以便调试
            vector = rng.standard_normal(dimensions)
            vector = vector / np.linalg.norm(vector)  # 归一化
            
            return vector.tolist()

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """
        计算两个向量之间的余弦相似度
        
        参数:
            v1: 第一个向量
            v2: 第二个向量
            
        返回:
            余弦相似度值 (-1到1之间)
        """
        try:
            import numpy as np
            
            # 转换为numpy数组
            a = np.array(v1)
            b = np.array(v2)
            
            # 计算余弦相似度
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            # 避免除以零
            if norm_a == 0 or norm_b == 0:
                return 0
                
            similarity = np.dot(a, b) / (norm_a * norm_b)
            
            # 确保结果在有效范围内
            return float(max(min(similarity, 1.0), -1.0))
        except Exception as e:
            self.logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
            
    def _vector_search_from_index(self, query_vector: List[float], index_data: Dict[str, Any], 
                                 top_k: int = 3, similarity_threshold: float = 0.5,
                                 min_chars: int = 100) -> List[Dict[str, Any]]:
        """
        从索引中进行向量搜索
        
        参数:
            query_vector: 查询向量
            index_data: 索引数据
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
            min_chars: 最小字符数
            
        返回:
            包含搜索结果的列表
        """
        self.logger.debug(f"Performing vector search with threshold={similarity_threshold}, top_k={top_k}")
        
        try:
            # 从索引获取文档ID和嵌入向量ID
            document_id = index_data.get("document_id", "")
            embedding_id = index_data.get("embedding_id", "")
            
            # 查找嵌入文件
            embedding_file = self._find_embedding_file(document_id, embedding_id)
            if not embedding_file:
                self.logger.error(f"Embedding file not found for document ID: {document_id}")
                raise FileNotFoundError(f"找不到文档 {document_id} 的嵌入向量文件")
            
            # 加载嵌入数据
            with open(embedding_file, "r", encoding="utf-8") as f:
                embedding_data = json.load(f)
            
            # 获取嵌入向量列表
            embeddings = embedding_data.get("embeddings", [])
            if not embeddings:
                self.logger.error(f"No embeddings found in file: {embedding_file}")
                return []
            
            self.logger.debug(f"Loaded {len(embeddings)} embeddings from {embedding_file}")
            
            # 计算相似度并排序
            results = []
            for item in embeddings:
                vector = item.get("vector", [])
                if not vector or len(vector) != len(query_vector):
                    continue
                
                # 计算相似度
                similarity = self._cosine_similarity(query_vector, vector)
                
                # 文本内容
                text = item.get("text", "")
                if "text" not in item and "content" in item:
                    text = item.get("content", "")
                    
                # 元数据
                metadata = item.get("metadata", {})
                    
                # 如果相似度超过阈值且文本长度超过最小值, 添加到结果列表
                if similarity >= similarity_threshold and len(text) >= min_chars:
                    results.append({
                        "text": text,
                        "similarity": similarity,
                        "metadata": metadata
                    })
            
            # 按相似度降序排序并选取top_k个结果
            results.sort(key=lambda x: x["similarity"], reverse=True)
            results = results[:top_k]
            
            self.logger.debug(f"Found {len(results)} results after filtering by threshold and length")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in vector search: {str(e)}")
            raise ValueError(f"向量搜索失败: {str(e)}")
