import os
import json
import datetime
import uuid
import numpy as np
import logging
from typing import Dict, List, Any, Optional

class SearchService:
    """语义搜索服务，支持基于向量相似度的检索"""
    
    def __init__(self, indices_dir=os.path.join("backend", "storage", "indices"), 
                 embeddings_dir=os.path.join("backend", "04-embedded-docs"), 
                 results_dir=os.path.join("backend", "storage", "results")):
        self.logger = logging.getLogger("SearchService")
        self.logger.setLevel(logging.INFO)

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
        self.logger.info(f"Starting search with index_id={index_id}, query={query}, top_k={top_k}, similarity_threshold={similarity_threshold} (lower threshold increases results)")
        
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
        self.logger.info(f"Looking for index file with ID={index_id}")
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
                            self.logger.info(f"Extracted document_filename '{document_filename}' from document_id '{doc_id}'")
                    except Exception as e:
                        self.logger.error(f"Error extracting filename from document_id '{doc_id}': {str(e)}")
            
            search_info["document_id"] = document_id
            search_info["vector_db"] = vector_db
            search_info["document_filename"] = document_filename
            
            self.logger.info(f"Found index for document_id={document_id}, document_filename={document_filename}, vector_db={vector_db}")
        except Exception as e:
            error_msg = f"读取索引文件失败: {str(e)}"
            self.logger.error(error_msg)
            search_info["status"]["error"] = error_msg
            raise ValueError(error_msg)
        
        # 记录向量模型信息
        embedding_model = index_data.get("embedding_model", "unknown")
        search_info["embedding_model"] = embedding_model
        
        # 生成查询向量
        provider = index_data.get("embedding_model", "").split("-")[0] if index_data.get("embedding_model") else "default"
        model = index_data.get("embedding_model", "").split("-")[-1] if index_data.get("embedding_model") else "default"
        
        vector_start_time = datetime.datetime.now()
        query_vector = self._generate_query_vector(query, provider, model)
        vector_time = datetime.datetime.now() - vector_start_time
        
        search_info["timing"]["vector_generation"] = vector_time.total_seconds()
        search_info["vector_dimensions"] = len(query_vector)
        
        # 执行向量搜索
        self.logger.info(f"Performing vector search with {len(query_vector)}-dimensional query vector")
        
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
        self.logger.info(f"Initial document_filename: {document_filename}, document_id: {document_id}")
        
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
                            self.logger.info(f"Extracted document name from ID: {document_filename}")
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
                                        self.logger.info(f"Successfully extracted filename: {filename} from source path")
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
                        self.logger.info(f"Cleaned document_filename to: {document_filename}")
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
        self.logger.info(f"Final document_filename: '{document_filename}'")
            
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
            self.logger.info(f"Saved search results to {result_path}")
        except Exception as e:
            self.logger.error(f"Error saving search results: {str(e)}")
        
        # 返回结果
        result["result_file"] = result_file
        
        # 打印搜索结果摘要
        if search_results:
            similarities = [f"{r['similarity']:.4f}" for r in search_results]
            self.logger.info(f"Found {len(search_results)} results with similarities: {similarities}")
        else:
            self.logger.info("No results found matching the criteria")
            
        return result
    
    def _find_index_file(self, index_id: str) -> Optional[str]:
        """查找指定ID的索引文件"""
        self.logger.info(f"Searching for index file with index_id='{index_id}'")
        
        # 只在主索引目录中查找
        possible_dirs = [self.indices_dir]
        
        # 打印搜索目录列表
        self.logger.info(f"Will search in directory: {self.indices_dir}")
            
        for dir_path in possible_dirs:
            self.logger.info(f"Checking directory: {dir_path}")
            
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
                                self.logger.info(f"Match found: File '{filename}' contains index_id='{index_id}'")
                                return file_path
                                
                            # 如果文件名中包含索引ID（备用策略）
                            if index_id in filename:
                                self.logger.info(f"Match found by filename: '{filename}' contains index_id='{index_id}'")
                                return file_path
                        except json.JSONDecodeError:
                            self.logger.error(f"Could not decode JSON from file: '{filename}'")
                        except Exception as e:
                            self.logger.error(f"Error reading file '{filename}': {str(e)}")
                
                self.logger.info(f"No index file with index_id='{index_id}' found in {dir_path}")
            else:
                self.logger.info(f"Indices directory '{dir_path}' does not exist")
                
        return None
    
    def _find_embedding_file(self, document_id: str, embedding_id: str = None) -> Optional[str]:
        """查找指定文档的嵌入文件"""
        self.logger.info(f"Searching for embedding file with document_id='{document_id}' and embedding_id='{embedding_id}'")
        
        # 只在主嵌入目录中查找
        possible_dirs = [self.embeddings_dir]
        
        # 打印搜索目录列表
        self.logger.info(f"Will search in directory: {self.embeddings_dir}")
            
        for dir_path in possible_dirs:
            self.logger.info(f"Checking directory: '{dir_path}'")
            if os.path.exists(dir_path):
                self.logger.info(f"Directory '{dir_path}' exists. Listing files...")
                for filename in os.listdir(dir_path):
                    # 放宽搜索条件，只要包含document_id和.json后缀即可
                    if document_id in filename and filename.endswith(".json"):
                        self.logger.info(f"Found potential file: '{filename}'")
                        file_path = os.path.join(dir_path, filename)
                        
                        try:
                            # 检查文件内容
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            
                            # 打印文件的键，便于调试
                            self.logger.info(f"File '{filename}' contains keys: {list(data.keys())}")
                                
                            # 如果指定了embedding_id，检查是否匹配
                            internal_embedding_id = data.get("embedding_id")
                            if embedding_id and internal_embedding_id and internal_embedding_id != embedding_id:
                                self.logger.info(f"File '{filename}' has embedding_id='{internal_embedding_id}' which doesn't match target '{embedding_id}'")
                                continue
                            
                            # 检查多种可能的键名
                            if "embeddings" in data:
                                self.logger.info(f"Match found: File '{filename}' contains 'embeddings' key")
                                return file_path
                                
                            if "vectors" in data:
                                self.logger.info(f"Match found: File '{filename}' contains 'vectors' key")
                                return file_path
                                
                            if "vector" in data:
                                self.logger.info(f"Match found: File '{filename}' contains 'vector' key")
                                return file_path
                                
                            # 如果文件名中包含"embedded"或"embedding"，很可能是嵌入文件
                            if "embedded" in filename or "embedding" in filename:
                                self.logger.info(f"Match found by filename pattern: '{filename}'")
                                return file_path
                                
                        except json.JSONDecodeError:
                            self.logger.error(f"Could not decode JSON from file: '{filename}'")
                        except Exception as e:
                            self.logger.error(f"Error reading file '{filename}': {str(e)}")
                
                self.logger.info(f"No matching embedding file found in '{dir_path}'")
            else:
                self.logger.info(f"Embeddings directory '{dir_path}' does not exist")
                
        return None
