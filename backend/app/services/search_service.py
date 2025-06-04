import os
import json
import datetime
import uuid
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from app.core.logger import get_logger_with_env_level

# Constants for string literals to avoid duplication
JSON_EXTENSION = ".json"

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
    
    def _initialize_search_info(self, index_id_or_collection: str, query: str, top_k: int, 
                           similarity_threshold: float, min_chars: int) -> Dict[str, Any]:
        """初始化搜索信息对象"""
        return {
            "params": {
                "index_id_or_collection": index_id_or_collection,
                "query": query,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "min_chars": min_chars
            },
            "timing": {},
            "status": {}
        }
        
    def _find_and_validate_index_files(self, index_id_or_collection: str, search_info: Dict[str, Any]) -> List[str]:
        """查找并验证索引文件"""
        self.logger.debug(f"Looking for indices with ID or collection={index_id_or_collection}")
        
        index_files = self._find_index_files_by_collection_or_id(index_id_or_collection)
        if not index_files:
            error_msg = f"找不到ID为{index_id_or_collection}的索引或集合"
            self.logger.error(error_msg)
            search_info["status"]["error"] = error_msg
            raise FileNotFoundError(error_msg)
        
        self.logger.debug(f"Found {len(index_files)} indices for collection or ID: {index_id_or_collection}")
        search_info["status"]["index_files_found"] = len(index_files)
        search_info["index_file_paths"] = index_files
        
        return index_files
        
    def _initialize_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """初始化集合信息对象"""
        return {
            "collection_name": collection_name,
            "document_ids": [],
            "document_filenames": [],
            "vector_dbs": [],
            "embedding_models": []
        }
        
    def _extract_filename_from_document_id(self, doc_id: str) -> str:
        """从复杂文档ID中提取文件名"""
        if not isinstance(doc_id, str) or "_" not in doc_id:
            return ""
            
        try:
            parts = doc_id.split("_")
            if len(parts) >= 3:  # If it has the expected format
                return "_".join(parts[:-2])  # Extract everything before timestamp_hash
        except Exception as e:
            self.logger.error(f"Error extracting filename from document_id '{doc_id}': {str(e)}")
            
        return ""
        
    def _load_index_data(self, index_file: str, search_info: Dict[str, Any]) -> Dict[str, Any]:
        """加载索引数据并提取基本信息"""
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        # 获取文档ID、向量数据库类型和其他索引信息
        document_id = index_data.get("document_id", "")
        vector_db = index_data.get("vector_db", "")
        
        # Get document filename directly from index_data or try to extract it from embedded data
        document_filename = index_data.get("document_filename", "")
        if not document_filename and "document_id" in index_data:
            document_filename = self._extract_filename_from_document_id(index_data["document_id"])
            if document_filename:
                self.logger.debug(f"Extracted document_filename '{document_filename}' from document_id '{index_data['document_id']}'")
        
        search_info["document_id"] = document_id
        search_info["vector_db"] = vector_db
        search_info["document_filename"] = document_filename
        
        self.logger.debug(f"Found index for document_id={document_id}, document_filename={document_filename}, vector_db={vector_db}")
        
        return index_data
        
    def _extract_provider_from_embedding_file_name(self, file_name: str, known_providers: List[str], embedding_model_str: str) -> Tuple[str, str, bool]:
        """从嵌入文件名中提取提供商和模型信息"""
        provider = ""
        model = embedding_model_str
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
                        model = model_part.split("_embedded" + JSON_EXTENSION)[0]
                self.logger.debug(f"Extracted provider='{provider}' and model='{model}' from file name")
                break
                
        return provider, model, provider_found
        
    def _extract_provider_from_embedding_file_content(self, embedding_file_path: str) -> Tuple[str, str, bool]:
        """从嵌入文件内容中提取提供商和模型信息"""
        provider = ""
        model = ""
        provider_found = False
        
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
            
        return provider, model, provider_found
        
    def _extract_provider_from_model_list(self, embedding_model_str: str) -> Tuple[str, str]:
        """通过可用模型列表匹配提供商和模型"""
        provider = ""
        model = embedding_model_str
        
        # 特殊处理 BGE 模型（直接分配给 ollama 提供商）
        if embedding_model_str.startswith("bge-"):
            provider = "ollama"
            self.logger.debug(f"Special handling: BGE model '{model}' assigned to provider '{provider}'")
            return provider, model
            
        # 导入嵌入服务以获取可用模型列表
        try:
            from app.services.embed_service import EmbedService
            embed_service = EmbedService()
            models_info = embed_service.get_embedding_models()
            
            if "providers" in models_info:
                # 在所有提供商的模型列表中查找匹配的模型名称
                for provider_name, provider_models in models_info["providers"].items():
                    for model_info in provider_models:
                        if model_info.get("id") == embedding_model_str:
                            provider = provider_name
                            self.logger.debug(f"Found model '{model}' in provider '{provider}' model list")
                            return provider, model
        except Exception as e:
            self.logger.error(f"Error getting embedding models: {str(e)}")
            
        return provider, model
        
    def _extract_provider_from_model_name(self, embedding_model_str: str, known_providers: List[str]) -> Tuple[str, str]:
        """从模型名称中推断提供商"""
        provider = ""
        model = embedding_model_str
        
        # 检查是否是 {provider}-* 格式
        for p in known_providers:
            if embedding_model_str.startswith(f"{p}-"):
                provider = p
                model = embedding_model_str[len(f"{p}-"):]
                self.logger.debug(f"Extracted provider='{provider}' from model name prefix")
                return provider, model
        
        # 特殊处理bge模型
        if embedding_model_str.startswith("bge-"):
            provider = "ollama"  # 显式为 bge 模型指定 ollama 提供商
            self.logger.debug(f"Special handling for BGE model: Using provider='{provider}' with model='{model}'")
            return provider, model
            
        # 尝试判断是否是类似 "bge-m3:latest" 这样的本地模型名称
        if ":" in embedding_model_str:
            provider = "ollama"  # 对于带冒号的格式，通常是本地模型
        else:
            provider = "default"
        
        self.logger.debug(f"No provider identified. Using provider='{provider}' with model='{model}'")
        return provider, model
        
    def _extract_provider_and_model(self, embedding_model_str: str, document_id: str, embedding_id: str) -> Tuple[str, str]:
        """从嵌入模型名称、文档ID和嵌入ID中提取提供商和模型信息"""
        if not embedding_model_str:
            return "default", "default"
            
        known_providers = ["openai", "bedrock", "huggingface", "ollama", "deepseek", "baidu", "baai", "default"]
        
        try:
            # 1. 首先检查嵌入文件，这是最可靠的信息源
            embedding_file_path = self._find_embedding_file(document_id, embedding_id)
            if embedding_file_path:
                self.logger.debug(f"Using embedding file path to detect provider: {embedding_file_path}")
                file_name = os.path.basename(embedding_file_path)
                
                # 从文件名中提取提供商信息
                provider, model, provider_found = self._extract_provider_from_embedding_file_name(
                    file_name, known_providers, embedding_model_str
                )
                
                if provider_found:
                    return provider, model
                    
                # 如果从文件名中未找到提供商，尝试从嵌入文件内容中获取
                provider, model, provider_found = self._extract_provider_from_embedding_file_content(embedding_file_path)
                
                if provider_found:
                    return provider, model
            
            # 2. 如果通过文件未找到提供商，尝试通过模型名称推断
            # 通过可用模型列表匹配
            provider, model = self._extract_provider_from_model_list(embedding_model_str)
            if provider:
                return provider, model
                
            # 3. 从模型名称中推断
            return self._extract_provider_from_model_name(embedding_model_str, known_providers)
                
        except Exception as e:
            self.logger.error(f"Error during provider/model extraction: {str(e)}")
            return "default", embedding_model_str
            
    def _update_collection_info(self, collection_info: Dict[str, Any], 
                               doc_id: str, vec_db: str, embed_model: str, doc_filename: str) -> None:
        """更新集合信息"""
        # 添加到集合信息
        if doc_id and doc_id not in collection_info["document_ids"]:
            collection_info["document_ids"].append(doc_id)
        
        if vec_db and vec_db not in collection_info["vector_dbs"]:
            collection_info["vector_dbs"].append(vec_db)
            
        if embed_model and embed_model not in collection_info["embedding_models"]:
            collection_info["embedding_models"].append(embed_model)
            
        if doc_filename and doc_filename not in collection_info["document_filenames"]:
            collection_info["document_filenames"].append(doc_filename)
            
    def _perform_single_index_search(self, current_index_file: str, query_vector: List[float], 
                                    collection_info: Dict[str, Any], 
                                    top_k: int, similarity_threshold: float, 
                                    min_chars: int) -> List[Dict[str, Any]]:
        """对单个索引执行向量搜索"""
        try:
            with open(current_index_file, "r", encoding="utf-8") as f:
                current_index_data = json.load(f)
            
            # 获取文档ID、向量数据库类型和其他索引信息用于集合显示
            doc_id = current_index_data.get("document_id", "")
            vec_db = current_index_data.get("vector_db", "")
            embed_model = current_index_data.get("embedding_model", "unknown")
            
            # 获取文档文件名
            doc_filename = current_index_data.get("document_filename", "")
            if not doc_filename and "document_id" in current_index_data:
                doc_filename = self._extract_filename_from_document_id(current_index_data["document_id"])
            
            # 更新集合信息
            self._update_collection_info(collection_info, doc_id, vec_db, embed_model, doc_filename)
            
            # 执行向量搜索
            self.logger.debug(f"Searching index: {os.path.basename(current_index_file)}")
            index_search_results = self._vector_search_from_index(
                query_vector, current_index_data, top_k, similarity_threshold, min_chars
            )
            
            # 将索引的文档信息添加到结果的元数据中
            for result in index_search_results:
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["document_id"] = doc_id
                result["metadata"]["document_filename"] = doc_filename
            
            self.logger.debug(f"Found {len(index_search_results)} results in index {os.path.basename(current_index_file)}")
            return index_search_results
            
        except Exception as e:
            self.logger.error(f"Error searching index {current_index_file}: {str(e)}")
            return []
            
    def _perform_vector_search(self, query_vector: List[float], index_files: List[str], 
                              index_data: Dict[str, Any], collection_info: Dict[str, Any], 
                              top_k: int, similarity_threshold: float, min_chars: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """执行向量搜索，支持单个索引和多索引集合"""
        # 如果只有一个索引，直接搜索该索引
        if len(index_files) == 1:
            search_results = self._vector_search_from_index(
                query_vector, index_data, top_k, similarity_threshold, min_chars
            )
            return search_results, collection_info
            
        # 如果有多个索引，搜索所有索引并合并结果
        all_search_results = []
        
        # 处理每个索引文件
        for current_index_file in index_files:
            index_search_results = self._perform_single_index_search(
                current_index_file, query_vector, collection_info, 
                top_k, similarity_threshold, min_chars
            )
            all_search_results.extend(index_search_results)
        
        # 按相似度降序排序并选取top_k个结果
        all_search_results.sort(key=lambda x: x["similarity"], reverse=True)
        search_results = all_search_results[:top_k]
        
        return search_results, collection_info
        
    def _prepare_query_vector(self, search_info: Dict[str, Any], index_data: Dict[str, Any], query: str) -> List[float]:
        """准备查询向量：提取提供商和模型信息，并生成查询向量"""
        # 记录向量模型信息并解析提供商和模型
        embedding_model = index_data.get("embedding_model", "unknown")
        search_info["embedding_model"] = embedding_model
        
        # 解析嵌入模型字符串
        embedding_model_str = index_data.get("embedding_model", "")
        self.logger.debug(f"Original embedding_model string: '{embedding_model_str}'")
        
        # 解析提供商和模型
        provider, model = self._extract_provider_and_model(
            embedding_model_str, 
            index_data.get("document_id", ""), 
            index_data.get("embedding_id", "")
        )
                        
        # 生成查询向量
        vector_start_time = datetime.datetime.now()
        self.logger.debug(f"Using provider='{provider}' and model='{model}' for query vector generation")
        query_vector = self._generate_query_vector(query, provider, model)
        vector_time = datetime.datetime.now() - vector_start_time
        
        search_info["timing"]["vector_generation"] = vector_time.total_seconds()
        search_info["vector_dimensions"] = len(query_vector)
        
        return query_vector

    def _calculate_search_stats(self, search_results: List[Dict[str, Any]], search_info: Dict[str, Any]) -> None:
        """计算搜索结果的统计信息"""
        search_info["result_count"] = len(search_results)
        
        if search_results:
            search_info["similarity_range"] = {
                "min": min(r["similarity"] for r in search_results),
                "max": max(r["similarity"] for r in search_results),
                "avg": sum(r["similarity"] for r in search_results) / len(search_results)
            }
    
    def _extract_document_filename_from_results(self, search_results: List[Dict[str, Any]]) -> Optional[str]:
        """从搜索结果中提取文档文件名"""
        try:
            for result_item in search_results:
                if result_item.get("metadata") and result_item["metadata"].get("source"):
                    source_path = result_item["metadata"]["source"]
                    if isinstance(source_path, str):
                        # Extract filename from path
                        filename = os.path.basename(source_path)
                        if filename:
                            self.logger.debug(f"Successfully extracted filename: {filename} from source path")
                            return filename
        except Exception as e:
            self.logger.error(f"Error extracting document filename from results: {str(e)}")
        return None
        
    def _extract_filename_from_document_id_parts(self, document_id: str) -> Optional[str]:
        """从document_id字符串中提取可读的文件名部分"""
        try:
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
                        self.logger.debug(f"Extracted document name from ID: {clean_name}")
                        return clean_name
        except Exception as e:
            self.logger.error(f"Error extracting name from document_id: {str(e)}")
        return None
    
    def _clean_document_filename(self, document_filename: str) -> str:
        """清理文档文件名，使其更友好"""
        if not document_filename:
            return ""
            
        # 移除扩展名
        if '.' in document_filename:
            base_name = os.path.splitext(document_filename)[0]
            document_filename = base_name
            
        # 移除多余的时间戳和ID，例如格式为 filename_YYYYMMDD_HHMMSS_hash 的文件名
        parts = document_filename.split('_')
        if len(parts) >= 4:
            # 检查倒数第三和第二部分是否为时间戳格式
            try:
                if (parts[-3].isdigit() and len(parts[-3]) == 8 and
                    parts[-2].isdigit() and len(parts[-2]) == 6 and
                    len(parts[-1]) >= 6):  # 最后一部分可能是哈希值
                    document_filename = '_'.join(parts[:-3])
                    self.logger.debug(f"Cleaned document_filename to: {document_filename}")
            except Exception as e:
                self.logger.debug(f"Error while cleaning document filename: {str(e)}")
                
        # 为中文文档添加前缀
        if document_filename and ('中文' in document_filename or 
                                '的' in document_filename or 
                                '一' in document_filename):
            # 这可能是一个中文文档名，给它添加一个前缀以便更容易识别
            if not document_filename.startswith('文档:'):
                document_filename = f"文档: {document_filename}"
                
        return document_filename
        
    def _generate_collection_display_name(self, collection_info: Dict[str, Any], original_id_or_collection: str) -> str:
        """生成集合显示名称"""
        collection_display_name = original_id_or_collection
        
        if len(collection_info["document_filenames"]) > 0:
            if len(collection_info["document_filenames"]) == 1:
                collection_display_name = collection_info["document_filenames"][0]
            else:
                collection_display_name = f"集合: {original_id_or_collection} ({len(collection_info['document_ids'])}个文档)"
        
        # 清理集合显示名称
        if collection_display_name:
            # 移除扩展名
            if '.' in collection_display_name:
                base_name = os.path.splitext(collection_display_name)[0]
                collection_display_name = base_name
            
            # 对中文文档进行特殊处理
            if ('中文' in collection_display_name or 
                    '的' in collection_display_name or 
                    '一' in collection_display_name):
                # 这可能是一个中文文档名，给它添加一个前缀以便更容易识别
                if not collection_display_name.startswith('文档:') and not collection_display_name.startswith('集合:'):
                    collection_display_name = f"文档: {collection_display_name}"
                    
        return collection_display_name
        
    def _save_search_results(self, result: Dict[str, Any], search_id: str, timestamp: str) -> str:
        """保存搜索结果到文件"""
        result_file = f"search_{search_id}_{timestamp}{JSON_EXTENSION}"
        result_path = os.path.join(self.results_dir, result_file)
        
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"Saved search results to {result_path}")
        except Exception as e:
            self.logger.error(f"Error saving search results: {str(e)}")
            
        return result_file

    def search(self, index_id_or_collection: str, query: str, top_k: int = 3, 
               similarity_threshold: float = 0.5, min_chars: int = 100) -> Dict[str, Any]:
        """
        执行语义搜索，支持单个索引或整个集合
        
        参数:
            index_id_or_collection: 索引ID或集合名称
            query: 查询文本
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值 (降低为0.5以提高召回率)
            min_chars: 最小字符数
        
        返回:
            包含搜索结果的字典
        """
        self.logger.debug(f"Starting search with index_id_or_collection={index_id_or_collection}, query={query}, top_k={top_k}, similarity_threshold={similarity_threshold}")
        
        original_id_or_collection = index_id_or_collection
        start_time = datetime.datetime.now()
        
        # 初始化搜索环境
        search_info = self._initialize_search_info(
            index_id_or_collection, query, top_k, similarity_threshold, min_chars
        )
        
        # 执行搜索流程
        search_results, index_files, collection_info = self._execute_search_process(
            index_id_or_collection, original_id_or_collection, query, 
            top_k, similarity_threshold, min_chars, search_info
        )
        
        # 处理文档元数据
        document_filename, document_id = self._process_document_metadata(
            search_info, search_results
        )
        
        # 生成结果标识符和计时
        search_id, timestamp = self._generate_result_identifiers()
        total_time = datetime.datetime.now() - start_time
        search_info["timing"]["total"] = total_time.total_seconds()
        
        # 构建最终结果对象 
        collection_display_name = self._generate_collection_display_name(
            collection_info, original_id_or_collection
        )
        
        # 构造参数分组
        search_params = {
            "search_id": search_id,
            "timestamp": timestamp,
            "query": query,
            "original_id_or_collection": original_id_or_collection,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "min_chars": min_chars
        }
        
        metadata = {
            "collection_display_name": collection_display_name,
            "collection_info": collection_info,
            "index_files": index_files,
            "document_id": document_id,
            "document_filename": document_filename
        }
        
        result = self._build_result_object(
            search_params, metadata, search_results, search_info
        )
        
        # 保存结果并记录日志
        self._save_and_log_results(result, search_results)
        
        return result
        
    def _execute_search_process(self, index_id_or_collection: str, original_id_or_collection: str, 
                               query: str, top_k: int, similarity_threshold: float, min_chars: int, 
                               search_info: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
        """执行完整的搜索流程，包括查找索引、准备向量和搜索"""
        # 查找索引文件
        index_files = self._find_and_validate_index_files(index_id_or_collection, search_info)
        
        # 初始化集合信息
        collection_info = self._initialize_collection_info(original_id_or_collection)
        
        # 准备索引数据
        index_data = self._prepare_index_data(index_files, search_info)
        
        # 准备查询向量
        query_vector = self._prepare_query_vector(search_info, index_data, query)
        
        # 执行向量搜索
        search_results, collection_info = self._execute_vector_search(
            query_vector, index_files, index_data, collection_info, 
            top_k, similarity_threshold, min_chars, search_info
        )
        
        return search_results, index_files, collection_info

    def _prepare_index_data(self, index_files: List[str], search_info: Dict[str, Any]) -> Dict[str, Any]:
        """准备索引数据，从第一个索引文件中加载"""
        index_file = index_files[0]
        search_info["status"]["index_file_found"] = True
        search_info["index_file_path"] = index_file
        
        try:
            return self._load_index_data(index_file, search_info)
        except Exception as e:
            error_msg = f"读取索引文件失败: {str(e)}"
            self.logger.error(error_msg)
            search_info["status"]["error"] = error_msg
            raise ValueError(error_msg)

    def _execute_vector_search(self, query_vector: List[float], index_files: List[str], 
                              index_data: Dict[str, Any], collection_info: Dict[str, Any], 
                              top_k: int, similarity_threshold: float, min_chars: int,
                              search_info: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """执行向量搜索并记录性能指标"""
        search_start_time = datetime.datetime.now()
        self.logger.debug(f"Performing vector search with {len(query_vector)}-dimensional query vector")
        
        # 执行搜索并获取结果
        search_results, collection_info = self._perform_vector_search(
            query_vector, index_files, index_data, collection_info, 
            top_k, similarity_threshold, min_chars
        )
        
        # 记录搜索时间和统计信息
        search_time = datetime.datetime.now() - search_start_time
        search_info["timing"]["vector_search"] = search_time.total_seconds()
        
        # 计算搜索统计信息
        self._calculate_search_stats(search_results, search_info)
        search_info["collection_info"] = collection_info
        
        return search_results, collection_info

    def _process_document_metadata(self, search_info: Dict[str, Any], 
                                  search_results: List[Dict[str, Any]]) -> Tuple[str, str]:
        """处理文档元数据，确保有有效的文件名"""
        document_filename = search_info.get("document_filename", "")
        document_id = search_info.get("document_id", "")
        self.logger.debug(f"Initial document_filename: {document_filename}, document_id: {document_id}")
        
        # 如果没有文件名但有文档ID，尝试提取
        if not document_filename and document_id:
            document_filename = self._extract_document_filename_from_sources(
                document_id, search_results, search_info
            )
        
        # 美化文件名
        document_filename = self._clean_document_filename(document_filename)
        
        # 确保文件名不为None
        if document_filename is None:
            document_filename = ""
            self.logger.warning("document_filename is None, setting to empty string")
            
        # 如果仍然没有有效文件名，使用文档ID的一部分
        if not document_filename and document_id:
            document_filename = self._create_fallback_filename(document_id)
        
        self.logger.debug(f"Final document_filename: '{document_filename}'")
        return document_filename, document_id

    def _extract_document_filename_from_sources(self, document_id: str, 
                                              search_results: List[Dict[str, Any]],
                                              search_info: Dict[str, Any]) -> str:
        """从各种来源尝试提取文档文件名"""
        # 1. 从文档ID部分提取
        extracted_name = self._extract_filename_from_document_id_parts(document_id)
        if extracted_name:
            return extracted_name
            
        # 2. 从搜索结果中提取
        extracted_filename = self._extract_document_filename_from_results(search_results)
        if extracted_filename:
            search_info["document_filename"] = extracted_filename
            return extracted_filename
            
        return ""

    def _create_fallback_filename(self, document_id: str) -> str:
        """从文档ID创建备用文件名"""
        # 使用文档ID的前30个字符，避免过长
        filename = document_id[:30]
        if len(document_id) > 30:
            filename += "..."
        return filename

    def _generate_result_identifiers(self) -> Tuple[str, str]:
        """生成搜索结果标识符"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        search_id = str(uuid.uuid4())[:8]
        return search_id, timestamp

    def _build_result_object(self, search_params: Dict[str, Any], metadata: Dict[str, Any], 
                            search_results: List[Dict[str, Any]], 
                            search_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建搜索结果对象
        
        参数:
            search_params: 包含搜索ID、时间戳、查询和搜索参数的字典
            metadata: 包含集合和文档元数据的字典
            search_results: 搜索结果列表
            search_info: 搜索信息字典
        """
        # 解包元数据
        collection_info = metadata["collection_info"]
        index_files = metadata["index_files"]
        document_id = metadata["document_id"] 
        document_filename = metadata["document_filename"]
        collection_display_name = metadata["collection_display_name"]
        
        # 解包搜索参数
        search_id = search_params["search_id"]
        timestamp = search_params["timestamp"]
        query = search_params["query"]
        original_id_or_collection = search_params["original_id_or_collection"] 
        top_k = search_params["top_k"]
        similarity_threshold = search_params["similarity_threshold"]
        min_chars = search_params["min_chars"]
        
        result = {
            "search_id": search_id,
            "timestamp": timestamp,
            "query": query,
            "index_id_or_collection": original_id_or_collection,
            "collection_name": original_id_or_collection,
            "collection_display_name": collection_display_name,
            "document_count": len(collection_info["document_ids"]),
            "document_id": document_id if len(index_files) == 1 else None,
            "document_filename": document_filename if len(index_files) == 1 else collection_display_name,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "min_chars": min_chars,
            "results": search_results,
            "search_info": search_info
        }
        
        # 添加便于访问的辅助字段
        result["search_info"]["document_filename"] = document_filename if len(index_files) == 1 else collection_display_name
        result["search_info"]["collection_display_name"] = collection_display_name
        
        return result

    def _save_and_log_results(self, result: Dict[str, Any], search_results: List[Dict[str, Any]]) -> None:
        """保存搜索结果并记录日志"""
        # 保存搜索结果
        result_file = self._save_search_results(result, result["search_id"], result["timestamp"])
        result["result_file"] = result_file
        
        # 打印搜索结果摘要
        if search_results:
            similarities = [f"{r['similarity']:.4f}" for r in search_results]
            self.logger.debug(f"Found {len(search_results)} results with similarities: {similarities}")
        else:
            self.logger.debug("No results found matching the criteria")
            
    def _find_index_file(self, index_id: str) -> Optional[str]:
        """查找指定ID的索引文件"""
        self.logger.debug(f"Searching for index file with index_id='{index_id}'")
        
        # 获取搜索目录
        possible_dirs = self._get_search_directories()
        self.logger.debug(f"Will search in directories: {possible_dirs}")
            
        for dir_path in possible_dirs:
            self.logger.debug(f"Checking directory: {dir_path}")
            
            if not os.path.exists(dir_path):
                self.logger.debug(f"Directory '{dir_path}' does not exist")
                continue
                
            # 在目录中搜索匹配的索引文件
            matching_file = self._find_matching_index_in_directory(dir_path, index_id)
            if matching_file:
                return matching_file
                
        return None
        
    def _get_search_directories(self) -> List[str]:
        """获取索引文件的搜索目录列表"""
        from app.core.config import settings
        vector_db_dir = settings.VECTOR_STORE_PERSIST_DIR if hasattr(settings, 'VECTOR_STORE_PERSIST_DIR') else os.path.join(self.storage_dir, "storage", "vector_db")
        return [self.indices_dir, vector_db_dir]
        
    def _find_matching_index_in_directory(self, dir_path: str, index_id: str) -> Optional[str]:
        """在指定目录中查找匹配的索引文件"""
        for filename in os.listdir(dir_path):
            if not filename.endswith(JSON_EXTENSION):
                continue
                
            file_path = os.path.join(dir_path, filename)
            index_data = self._safely_read_json_file(file_path)
            
            if not index_data:
                continue
            
            # 检查索引ID是否匹配
            if self._is_index_match(index_data, filename, index_id):
                return file_path
        
        self.logger.debug(f"No index file with index_id='{index_id}' found in {dir_path}")
        return None
        
    def _safely_read_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """安全地读取JSON文件，处理可能的异常"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.logger.error(f"Could not decode JSON from file: '{os.path.basename(file_path)}'")
        except Exception as e:
            self.logger.error(f"Error reading file '{os.path.basename(file_path)}': {str(e)}")
        return None
        
    def _is_index_match(self, index_data: Dict[str, Any], filename: str, index_id: str) -> bool:
        """检查索引数据是否与目标索引ID匹配"""
        # 检查JSON中的索引ID
        internal_index_id = index_data.get("index_id")
        if internal_index_id == index_id:
            self.logger.debug(f"Match found: File '{filename}' contains index_id='{index_id}'")
            return True
            
        # 备用策略：检查文件名是否包含索引ID
        if index_id in filename:
            self.logger.debug(f"Match found by filename: '{filename}' contains index_id='{index_id}'")
            return True
            
        return False

    def _find_index_files_by_collection_or_id(self, index_id_or_collection: str) -> List[str]:
        """
        查找指定ID或集合名称的索引文件
        
        参数:
            index_id_or_collection: 索引ID或集合名称
            
        返回:
            包含索引文件路径的列表
        """
        self.logger.debug(f"Searching for index files with index_id or collection_name='{index_id_or_collection}'")
        
        # 获取搜索目录
        possible_dirs = self._get_search_directories()
        self.logger.debug(f"Will search in directories: {possible_dirs}")
        
        # 在所有目录中搜索匹配的索引文件
        matching_files = self._find_all_matching_indices(possible_dirs, index_id_or_collection)
        
        # 如果没有找到匹配的文件，尝试单个索引ID回退
        if not matching_files:
            matching_files = self._try_single_index_fallback(index_id_or_collection)
        
        self.logger.debug(f"Found {len(matching_files)} matching index files for '{index_id_or_collection}'")
        return matching_files

    def _find_all_matching_indices(self, directories: List[str], index_id_or_collection: str) -> List[str]:
        """在多个目录中查找所有匹配的索引文件"""
        matching_files = []
        
        for dir_path in directories:
            self.logger.debug(f"Checking directory: {dir_path}")
            
            if not os.path.exists(dir_path):
                self.logger.debug(f"Directory '{dir_path}' does not exist")
                continue
                
            matching_files.extend(self._find_matches_in_directory(dir_path, index_id_or_collection))
        
        return matching_files

    def _find_matches_in_directory(self, dir_path: str, index_id_or_collection: str) -> List[str]:
        """在单个目录中查找匹配的索引文件"""
        matches = []
        
        for filename in os.listdir(dir_path):
            if not filename.endswith(JSON_EXTENSION):
                continue
                
            file_path = os.path.join(dir_path, filename)
            index_data = self._safely_read_json_file(file_path)
            
            if not index_data:
                continue
                
            if self._is_index_match(index_data, filename, index_id_or_collection):
                matches.append(file_path)
                
        return matches

    def _is_index_match(self, index_data: Dict, filename: str, index_id_or_collection: str) -> bool:
        """检查索引数据是否与搜索条件匹配"""
        # 检查索引ID
        internal_index_id = index_data.get("index_id")
        if internal_index_id == index_id_or_collection:
            self.logger.debug(f"Match found by index_id: File '{filename}' contains index_id='{index_id_or_collection}'")
            return True
        
        # 检查集合名称
        collection_name = index_data.get("collection_name")
        if collection_name == index_id_or_collection:
            self.logger.debug(f"Match found by collection_name: File '{filename}' belongs to collection='{index_id_or_collection}'")
            return True
            
        # 备用策略：检查文件名是否包含索引ID
        if index_id_or_collection in filename:
            self.logger.debug(f"Match found by filename: '{filename}' contains '{index_id_or_collection}'")
            return True
            
        return False

    def _try_single_index_fallback(self, index_id_or_collection: str) -> List[str]:
        """尝试将输入视为单个索引ID（向后兼容）"""
        matching_files = []
        
        self.logger.debug(f"No matching collection found, trying single index fallback for '{index_id_or_collection}'")
        single_index_file = self._find_index_file(index_id_or_collection)
        
        if single_index_file:
            self.logger.debug(f"Found single index file: {single_index_file}")
            matching_files.append(single_index_file)
            
        return matching_files

    def _find_embedding_file(self, document_id: str, embedding_id: str = None) -> Optional[str]:
        """查找指定文档的嵌入文件"""
        self.logger.debug(f"Searching for embedding file with document_id='{document_id}' and embedding_id='{embedding_id}'")
        
        # 只在主嵌入目录中查找
        dir_path = self.embeddings_dir
        self.logger.debug(f"Will search in directory: {dir_path}")
        
        if not os.path.exists(dir_path):
            self.logger.debug(f"Embeddings directory '{dir_path}' does not exist")
            return None
            
        # 获取所有可能匹配的文件
        potential_files = self._get_potential_embedding_files(dir_path, document_id)
        
        # 检查每个文件是否符合条件
        for file_path, filename in potential_files:
            embedding_file = self._check_embedding_file_match(file_path, filename, embedding_id)
            if embedding_file:
                return embedding_file
                
        self.logger.debug(f"No matching embedding file found in '{dir_path}'")
        return None

    def _get_potential_embedding_files(self, dir_path: str, document_id: str) -> List[Tuple[str, str]]:
        """获取可能包含指定文档ID的所有文件"""
        potential_files = []
        
        for filename in os.listdir(dir_path):
            # 放宽搜索条件，只要包含document_id和.json后缀即可
            if document_id in filename and filename.endswith(JSON_EXTENSION):
                self.logger.debug(f"Found potential file: '{filename}'")
                file_path = os.path.join(dir_path, filename)
                potential_files.append((file_path, filename))
                
        return potential_files

    def _check_embedding_file_match(self, file_path: str, filename: str, embedding_id: str = None) -> Optional[str]:
        """检查文件是否为所需的嵌入文件"""
        data = self._safely_read_json_file(file_path)
        
        if not data:
            return None
            
        # 打印文件的键，便于调试
        self.logger.debug(f"File '{filename}' contains keys: {list(data.keys())}")
        
        # 如果指定了embedding_id，检查是否匹配
        if not self._check_embedding_id_match(data, filename, embedding_id):
            return None
            
        # 检查文件是否含有嵌入向量相关的键
        if self._has_embedding_keys(data, filename):
            return file_path
            
        # 如果文件名符合嵌入文件命名模式
        if self._has_embedding_filename_pattern(filename):
            return file_path
            
        return None

    def _check_embedding_id_match(self, data: Dict, filename: str, embedding_id: str = None) -> bool:
        """检查嵌入ID是否匹配"""
        if not embedding_id:
            return True
            
        internal_embedding_id = data.get("embedding_id")
        if internal_embedding_id and internal_embedding_id != embedding_id:
            self.logger.debug(f"File '{filename}' has embedding_id='{internal_embedding_id}' which doesn't match target '{embedding_id}'")
            return False
            
        return True

    def _has_embedding_keys(self, data: Dict, filename: str) -> bool:
        """检查文件是否含有嵌入向量相关的键"""
        for key in ["embeddings", "vectors", "vector"]:
            if key in data:
                self.logger.debug(f"Match found: File '{filename}' contains '{key}' key")
                return True
        return False

    def _has_embedding_filename_pattern(self, filename: str) -> bool:
        """检查文件名是否符合嵌入文件命名模式"""
        if "embedded" in filename or "embedding" in filename:
            self.logger.debug(f"Match found by filename pattern: '{filename}'")
            return True
        return False

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
                self.logger.debug("Retrying with provider 'ollama' for BGE model")
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
