import os
import json
import datetime
import uuid
from typing import Dict, List, Any, Optional
from enum import Enum
from pymilvus import (
    connections,
    utility,
    Collection,
    DataType,
    FieldSchema,
    CollectionSchema,
)
from app.core.config import settings
from app.core.logger import get_logger_with_env_level


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
            # 为FAISS设置特定路径
            self.db_path = os.path.join(settings.VECTOR_STORE_PERSIST_DIR, "faiss")
        # Chroma specific settings
        elif provider == VectorDBProvider.CHROMA.value:
            self.collection_name = settings.CHROMA_COLLECTION_NAME
            self.distance_function = settings.CHROMA_DISTANCE_FUNCTION
            # 为Chroma设置特定路径
            self.db_path = os.path.join(settings.VECTOR_STORE_PERSIST_DIR, "chroma")
        # Milvus specific settings
        elif provider == VectorDBProvider.MILVUS.value:
            self.milvus_uri = os.getenv("MILVUS_URI", "127.0.0.1:19530")
            self.db_path = (
                settings.VECTOR_STORE_PERSIST_DIR
            )  # Milvus实际上是远程的，但我们仍然保留一个本地路径以保持一致性

        # 主向量数据库目录（来自config.toml）
        self.persist_directory = settings.VECTOR_STORE_PERSIST_DIR

        # 确保向量数据库存储目录存在
        os.makedirs(self.persist_directory, exist_ok=True)
        if hasattr(self, "db_path"):
            os.makedirs(self.db_path, exist_ok=True)

    def get_index_params(self):
        """Get index parameters based on vector DB provider"""
        if self.provider == VectorDBProvider.MILVUS.value:
            return {"metric_type": "COSINE"}
        elif self.provider == VectorDBProvider.FAISS.value:
            metric_map = {
                "cosine": "METRIC_INNER_PRODUCT",
                "l2": "METRIC_L2",
                "ip": "METRIC_INNER_PRODUCT",
            }
            return {"metric_type": metric_map.get(self.metric, "METRIC_INNER_PRODUCT")}
        elif self.provider == VectorDBProvider.CHROMA.value:
            return {"distance_function": self.distance_function}


class IndexService:
    """向量索引服务，支持FAISS和Chroma向量数据库"""

    def __init__(self):
        # 配置日志
        self.logger = get_logger_with_env_level("IndexService")

        # 使用settings中的配置
        self.embeddings_dir = settings.EMBEDDINGS_DIR
        self.indices_dir = settings.INDICES_DIR
        self.vector_db_dir = settings.VECTOR_STORE_PERSIST_DIR

        # 确保所有目录存在
        os.makedirs(self.embeddings_dir, exist_ok=True)
        os.makedirs(self.indices_dir, exist_ok=True)
        os.makedirs(self.vector_db_dir, exist_ok=True)
        os.makedirs(os.path.join(self.vector_db_dir, "faiss"), exist_ok=True)
        os.makedirs(os.path.join(self.vector_db_dir, "chroma"), exist_ok=True)

        # 添加日志记录所有路径
        self.logger.debug("索引服务初始化，路径配置：")
        self.logger.debug(f"  - 嵌入向量目录: {self.embeddings_dir}")
        self.logger.debug(f"  - 索引元数据目录: {self.indices_dir}")
        self.logger.debug(f"  - 向量数据库目录: {self.vector_db_dir}")

    def _prepare_index_parameters(
        self,
        document_id: str,
        vector_db: str,
        collection_name: str,
        index_name: str,
        embedding_id: str,
    ) -> Dict[str, str]:
        """
        准备索引参数，设置默认值并返回规范化的参数
        """
        # 使用配置中的默认向量数据库类型，如果未指定
        if vector_db is None:
            vector_db = settings.VECTOR_STORE_TYPE

        # 如果未指定嵌入ID，则报错
        if embedding_id is None:
            raise ValueError("必须指定嵌入ID")

        # 如果未指定集合名称或索引名称，则自动生成
        if collection_name is None:
            collection_name = f"col_{document_id[:10]}"
        if index_name is None:
            index_name = f"idx_{embedding_id[:8]}"

        return {
            "vector_db": vector_db,
            "collection_name": collection_name,
            "index_name": index_name,
        }

    def _load_embeddings(self, document_id: str, embedding_id: str) -> Dict[str, Any]:
        """
        加载嵌入数据
        """
        # 检查嵌入是否存在
        embedding_file = self._find_embedding_file(document_id, embedding_id)
        if not embedding_file:
            error_message = (
                f"请先为文档ID {document_id} (使用嵌入ID: {embedding_id}) 创建嵌入向量"
            )
            print(f"[SERVICE ERROR IndexService._load_embeddings] {error_message}")
            raise FileNotFoundError(error_message)

        print(
            f"[SERVICE LOG IndexService._load_embeddings] Found embedding file: {embedding_file}"
        )

        # 读取嵌入数据
        with open(embedding_file, "r", encoding="utf-8") as f:
            embedding_data = json.load(f)

        # 提取嵌入向量
        embeddings = embedding_data.get("embeddings", [])
        if not embeddings:
            raise ValueError("嵌入数据为空")

        return {"embedding_data": embedding_data, "embeddings": embeddings}

    def _create_vector_db_index(
        self,
        embeddings: List[Dict[str, Any]],
        vector_db: str,
        collection_name: str,
        index_name: str,
    ) -> Dict[str, Any]:
        """
        根据指定的向量数据库类型创建索引
        """
        print(
            f"[SERVICE LOG IndexService._create_vector_db_index] 使用向量数据库类型: {vector_db}"
        )

        if vector_db == VectorDBProvider.FAISS.value:
            print(
                f"[SERVICE LOG IndexService._create_vector_db_index] 创建FAISS索引，集合名: {collection_name}, 索引名: {index_name}"
            )
            index_info = self._create_faiss_index(
                embeddings, collection_name, index_name
            )
            print(
                f"[SERVICE LOG IndexService._create_vector_db_index] FAISS索引创建成功: {index_info['index_path']}"
            )
        elif vector_db == VectorDBProvider.CHROMA.value:
            print(
                f"[SERVICE LOG IndexService._create_vector_db_index] 创建Chroma索引，集合名: {collection_name}, 索引名: {index_name}"
            )
            index_info = self._create_chroma_index(
                embeddings, collection_name, index_name
            )
            print(
                f"[SERVICE LOG IndexService._create_vector_db_index] Chroma索引创建成功: {index_info['index_path']}"
            )
        elif vector_db == VectorDBProvider.MILVUS.value:
            print(
                f"[SERVICE LOG IndexService._create_vector_db_index] 创建Milvus索引，集合名: {collection_name}, 索引名: {index_name}"
            )
            config = VectorDBConfig(
                provider=VectorDBProvider.MILVUS.value, index_mode=index_name
            )
            milvus_result = self._index_to_milvus(embeddings, collection_name, config)
            index_info = milvus_result  # contains collection_name and index_size
            print(
                f"[SERVICE LOG IndexService._create_vector_db_index] Milvus索引创建成功: 集合名 {index_info['collection_name']}"
            )
        else:
            raise ValueError(f"不支持的向量数据库类型: {vector_db}")

        return index_info

    def _find_document_file(self, document_id: str) -> str:
        """
        在存储目录中查找与document_id匹配的文件
        """
        # 默认使用document_id
        document_filename = document_id

        try:
            # 搜索storage/documents目录查找匹配document_id的文件
            storage_dir = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ),
                "storage",
                "documents",
            )
            if not os.path.exists(storage_dir):
                return document_filename

            # 首先尝试精确匹配document_id开头的文件
            exact_matches = self._find_exact_matching_files(storage_dir, document_id)

            # 如果找到了精确匹配，处理第一个匹配项
            if exact_matches:
                document_filename = self._extract_filename_from_match(exact_matches[0])
            else:
                # 回退到包含document_id的任何文件
                document_filename = self._find_containing_file(storage_dir, document_id)

            # 如果上述方法都失败，尝试从document_id本身提取信息
            if document_filename == document_id:
                document_filename = self._parse_document_id(document_id)

        except Exception as e:
            self.logger.debug(f"Failed to extract document filename from ID: {str(e)}")
            # 如果提取失败则使用完整的document_id

        return document_filename

    def _find_exact_matching_files(
        self, storage_dir: str, document_id: str
    ) -> List[str]:
        """查找精确匹配document_id开头的文件"""
        exact_matches = []
        for filename in os.listdir(storage_dir):
            file_id = os.path.splitext(filename)[0]
            if file_id.startswith(document_id):
                exact_matches.append(filename)
        return exact_matches

    def _extract_filename_from_match(self, matched_file: str) -> str:
        """从匹配的文件名中提取原始文件名"""
        self.logger.info(f"Found exact match for document ID: {matched_file}")

        # 从文件名中提取原始文件名部分
        base_name = os.path.basename(matched_file)

        # 首先分离扩展名
        name_without_ext = os.path.splitext(base_name)[0]

        # 检查是否是常见的文档命名模式: name_YYYYMMDD_HHMMSS_ID
        if "_" not in name_without_ext:
            return name_without_ext

        # 查找时间戳部分的位置
        parts = name_without_ext.split("_")
        timestamp_part_index = self._find_timestamp_part(parts)

        # 如果找到了时间戳部分，提取前面的所有内容作为原始文件名
        if timestamp_part_index > 0:
            document_filename = "_".join(parts[:timestamp_part_index])
        elif len(parts) >= 3:
            # 如果没有找到明确的时间戳部分，则尝试使用倒数第三部分之前的内容
            document_filename = "_".join(parts[:-2])
        else:
            document_filename = name_without_ext

        self.logger.info(f"Extracted document filename: {document_filename}")
        return document_filename

    def _find_timestamp_part(self, parts: List[str]) -> int:
        """在文件名部分中查找可能是时间戳的部分"""
        for i, part in enumerate(parts):
            if len(part) == 8 and part.isdigit():
                return i
        return -1

    def _find_containing_file(self, storage_dir: str, document_id: str) -> str:
        """查找包含document_id的任何文件"""
        for filename in os.listdir(storage_dir):
            if document_id in filename:
                base_name = os.path.splitext(os.path.basename(filename))[0]

                # 如果文件名包含多个部分 (用下划线分隔)，可能是按照特定格式命名的
                if "_" in base_name:
                    parts = base_name.split("_")
                    if len(parts) >= 3 and parts[-2].isdigit() and len(parts[-2]) >= 8:
                        # 如果倒数第二部分是数字且长度至少为8，可能是时间戳
                        document_filename = "_".join(parts[:-2])
                    else:
                        document_filename = base_name
                else:
                    document_filename = base_name

                self.logger.info(
                    f"Found document file containing ID: {filename}, extracted document_filename: {document_filename}"
                )
                return document_filename

        # 如果没有找到任何匹配，返回原始document_id
        return document_id

    def _parse_document_id(self, document_id: str) -> str:
        """从document_id本身解析文件名"""
        if "_" not in document_id:
            return document_id

        parts = document_id.split("_")

        # 查找可能是日期部分的部分
        for i, part in enumerate(parts):
            if len(part) == 8 and part.isdigit():
                # 可能是YYYYMMDD格式的日期
                return "_".join(parts[:i])

        # 如果没有找到日期模式，但至少有3个部分，假设最后两个是日期和ID
        if len(parts) >= 3:
            return "_".join(parts[:-2])

        return document_id

    def _save_index_result(
        self,
        document_id: str,
        result: Dict[str, Any],
        timestamp: str,
        vector_db: str,
        index_name: str,
        version: str,
    ) -> str:
        """保存索引结果到文件"""
        result_file = (
            f"{document_id}_{timestamp}_{vector_db}_{index_name}_v{version}.json"
        )
        result_path = os.path.join(self.indices_dir, result_file)

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result_file

    def create_index(
        self,
        document_id: str,
        vector_db: str = None,
        collection_name: str = None,
        index_name: str = None,
        embedding_id: str = None,
        version: str = "1.0",
    ) -> Dict[str, Any]:
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
        # 准备和验证参数
        params = self._prepare_index_parameters(
            document_id, vector_db, collection_name, index_name, embedding_id
        )
        vector_db = params["vector_db"]
        collection_name = params["collection_name"]
        index_name = params["index_name"]

        print(
            f"[SERVICE LOG IndexService.create_index] Called with: document_id='{document_id}', vector_db='{vector_db}', collection_name='{collection_name}', index_name='{index_name}', embedding_id='{embedding_id}', version='{version}'"
        )

        # 加载嵌入数据
        embedding_result = self._load_embeddings(document_id, embedding_id)
        embedding_data = embedding_result["embedding_data"]
        embeddings = embedding_result["embeddings"]

        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        index_id = str(uuid.uuid4())[:8]

        # 创建向量数据库索引
        index_info = self._create_vector_db_index(
            embeddings, vector_db, collection_name, index_name
        )

        # 提取文档文件名
        document_filename = self._find_document_file(document_id)

        # 构建索引结果
        result = {
            "document_id": document_id,
            "document_filename": document_filename,
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
            "index_info": index_info,
        }

        # 保存索引结果
        result_file = self._save_index_result(
            document_id, result, timestamp, vector_db, index_name, version
        )

        # 返回结果
        result["result_file"] = result_file
        return result

    def list_indices(self) -> List[Dict[str, Any]]:
        """获取所有索引列表"""
        indices = []

        # Ensure the indices directory exists
        if not os.path.exists(self.indices_dir):
            self.logger.warning(f"Indices directory does not exist: {self.indices_dir}")
            return indices

        try:
            # Check if directory is empty
            filenames = os.listdir(self.indices_dir)
            if not filenames:
                self.logger.info(f"Indices directory is empty: {self.indices_dir}")
                return indices

            for filename in filenames:
                if filename.endswith(".json"):
                    file_path = os.path.join(self.indices_dir, filename)

                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            index_data = json.load(f)

                        # Validate that the JSON contains required fields
                        if not isinstance(index_data, dict):
                            self.logger.warning(
                                f"Invalid index file format (not a dict): {filename}"
                            )
                            continue

                        indices.append(
                            {
                                "document_id": index_data.get("document_id", ""),
                                "document_filename": index_data.get(
                                    "document_filename", ""
                                ),  # Include document filename
                                "index_id": index_data.get("index_id", ""),
                                "timestamp": index_data.get("timestamp", ""),
                                "vector_db": index_data.get("vector_db", ""),
                                "collection_name": index_data.get(
                                    "collection_name", ""
                                ),
                                "index_name": index_data.get("index_name", ""),
                                "version": index_data.get("version", ""),
                                "total_vectors": index_data.get("total_vectors", 0),
                                "file": filename,
                            }
                        )

                    except json.JSONDecodeError as e:
                        self.logger.error(
                            f"Failed to parse JSON file {filename}: {str(e)}"
                        )
                        continue
                    except Exception as e:
                        self.logger.error(
                            f"Error reading index file {filename}: {str(e)}"
                        )
                        continue

        except Exception as e:
            self.logger.error(
                f"Error listing indices directory {self.indices_dir}: {str(e)}"
            )
            # Return empty list instead of raising exception
            return indices

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
                    connections.connect(
                        alias="default", uri=VectorDBConfig("default").milvus_uri
                    )
                    if utility.has_collection(collection_name):
                        utility.drop_collection(collection_name)
                except Exception as e:
                    print(f"Milvus清理错误 (非致命): {str(e)}")
                finally:
                    try:
                        connections.disconnect("default")
                    except Exception:
                        # Ignore disconnection errors as they are non-critical during cleanup
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
                "index_name": index_name,
            }
        except Exception as e:
            raise RuntimeError(f"删除索引时发生错误: {str(e)}")

    def _find_embedding_file(
        self, document_id: str, embedding_id: str
    ) -> Optional[str]:
        """查找指定文档和嵌入ID的嵌入文件"""
        print(
            f"[SERVICE LOG IndexService._find_embedding_file] Searching for embedding file with document_id='{document_id}' and embedding_id='{embedding_id}' in directory='{self.embeddings_dir}'"
        )

        if not self._embeddings_directory_exists():
            return None

        return self._search_embedding_files(document_id, embedding_id)

    def _embeddings_directory_exists(self) -> bool:
        """检查嵌入目录是否存在"""
        if os.path.exists(self.embeddings_dir):
            print(
                f"[SERVICE LOG IndexService._find_embedding_file] Directory '{self.embeddings_dir}' exists. Listing files..."
            )
            return True
        else:
            print(
                f"[SERVICE ERROR IndexService._find_embedding_file] Embeddings directory '{self.embeddings_dir}' does not exist."
            )
            return False

    def _search_embedding_files(
        self, document_id: str, embedding_id: str
    ) -> Optional[str]:
        """在嵌入目录中搜索匹配的文件"""
        for filename in os.listdir(self.embeddings_dir):
            print(
                f"[SERVICE LOG IndexService._find_embedding_file] Checking file: '{filename}'"
            )

            if self._is_candidate_embedding_file(filename, document_id):
                file_path = self._check_embedding_file_content(filename, embedding_id)
                if file_path:
                    return file_path

        print(
            f"[SERVICE LOG IndexService._find_embedding_file] No matching file found after checking all candidate files in '{self.embeddings_dir}'."
        )
        return None

    def _is_candidate_embedding_file(self, filename: str, document_id: str) -> bool:
        """检查文件是否为候选嵌入文件"""
        is_candidate = document_id in filename and filename.endswith("_embedded.json")
        if is_candidate:
            print(
                f"[SERVICE LOG IndexService._find_embedding_file] Candidate file (matches document_id and suffix): '{filename}'"
            )
        return is_candidate

    def _check_embedding_file_content(
        self, filename: str, embedding_id: str
    ) -> Optional[str]:
        """检查嵌入文件内容是否匹配目标embedding_id"""
        file_path = os.path.join(self.embeddings_dir, filename)

        try:
            embedding_data = self._load_embedding_data(file_path)
            return self._validate_embedding_id(
                embedding_data, embedding_id, file_path, filename
            )
        except json.JSONDecodeError:
            print(
                f"[SERVICE WARNING IndexService._find_embedding_file] Could not decode JSON from candidate file: '{filename}'"
            )
        except Exception as e:
            print(
                f"[SERVICE WARNING IndexService._find_embedding_file] Error reading or processing candidate file '{filename}': {e}"
            )

        return None

    def _load_embedding_data(self, file_path: str) -> dict:
        """加载嵌入数据文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _validate_embedding_id(
        self,
        embedding_data: dict,
        target_embedding_id: str,
        file_path: str,
        filename: str,
    ) -> Optional[str]:
        """验证嵌入ID是否匹配"""
        internal_embedding_id = embedding_data.get("embedding_id")

        if internal_embedding_id == target_embedding_id:
            print(
                f"[SERVICE LOG IndexService._find_embedding_file] Match found: Internal embedding_id ('{internal_embedding_id}') matches target ('{target_embedding_id}'). File: '{file_path}'"
            )
            return file_path
        else:
            print(
                f"[SERVICE LOG IndexService._find_embedding_file] File '{filename}' matches document_id, but its internal embedding_id ('{internal_embedding_id}') does not match target ('{target_embedding_id}')."
            )
            return None

    def _find_index_file(self, index_id: str) -> Optional[str]:
        """查找指定ID的索引文件"""
        print(
            f"[SERVICE LOG IndexService._find_index_file] Searching for index file with index_id='{index_id}' in directory='{self.indices_dir}'"
        )

        if not self._indices_directory_exists():
            return None

        return self._search_index_files(index_id)

    def _indices_directory_exists(self) -> bool:
        """检查索引目录是否存在"""
        if os.path.exists(self.indices_dir):
            print(
                f"[SERVICE LOG IndexService._find_index_file] Directory '{self.indices_dir}' exists. Listing files..."
            )
            return True
        else:
            print(
                f"[SERVICE ERROR IndexService._find_index_file] Indices directory '{self.indices_dir}' does not exist"
            )
            return False

    def _search_index_files(self, index_id: str) -> Optional[str]:
        """在索引目录中搜索匹配的文件"""
        for filename in os.listdir(self.indices_dir):
            if self._is_candidate_index_file(filename):
                file_path = self._check_index_file_content(filename, index_id)
                if file_path:
                    return file_path

        print(
            f"[SERVICE WARNING IndexService._find_index_file] No index file with index_id='{index_id}' found in '{self.indices_dir}'"
        )
        return None

    def _is_candidate_index_file(self, filename: str) -> bool:
        """检查文件是否为候选索引文件"""
        return filename.endswith(".json")

    def _check_index_file_content(
        self, filename: str, target_index_id: str
    ) -> Optional[str]:
        """检查索引文件内容是否匹配目标index_id"""
        file_path = os.path.join(self.indices_dir, filename)
        print(
            f"[SERVICE LOG IndexService._find_index_file] Checking file: '{filename}'"
        )

        try:
            index_data = self._load_index_data(file_path)
            return self._validate_index_id(
                index_data, target_index_id, filename, file_path
            )
        except json.JSONDecodeError:
            print(
                f"[SERVICE WARNING IndexService._find_index_file] Could not decode JSON from file: '{filename}'"
            )
        except Exception as e:
            print(
                f"[SERVICE WARNING IndexService._find_index_file] Error reading or processing file '{filename}': {str(e)}"
            )

        return None

    def _load_index_data(self, file_path: str) -> dict:
        """加载索引数据文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _validate_index_id(
        self, index_data: dict, target_index_id: str, filename: str, file_path: str
    ) -> Optional[str]:
        """验证索引ID是否匹配"""
        internal_index_id = index_data.get("index_id")
        print(
            f"[SERVICE LOG IndexService._find_index_file] File '{filename}' has internal index_id: '{internal_index_id}'"
        )

        if internal_index_id == target_index_id:
            print(
                f"[SERVICE LOG IndexService._find_index_file] Match found: File '{filename}' contains index_id='{target_index_id}'"
            )
            return file_path

        return None

    def _create_faiss_index(
        self, embeddings: List[Dict[str, Any]], collection_name: str, index_name: str
    ) -> Dict[str, Any]:
        """创建FAISS索引"""
        try:
            # 获取FAISS配置
            vector_db_config = VectorDBConfig(
                provider=VectorDBProvider.FAISS.value, index_mode=index_name
            )

            # 提取向量和ID
            vectors = [emb.get("vector", []) for emb in embeddings]

            # 配置索引路径（使用vector_db_dir下的faiss子目录）
            index_path = os.path.join(
                self.vector_db_dir, "faiss", f"{collection_name}_{index_name}.faiss"
            )
            os.makedirs(os.path.dirname(index_path), exist_ok=True)

            # 创建并保存FAISS索引
            print(
                f"[SERVICE LOG IndexService._create_faiss_index] 正在创建FAISS索引: {index_path}"
            )

            try:
                import faiss
                import numpy as np

                # 将向量转换为numpy数组
                dimensions = len(vectors[0]) if vectors else 0
                vector_array = np.array(vectors).astype("float32")

                # 创建FAISS索引
                if vector_db_config.metric.lower() == "cosine":
                    # 对于余弦相似度，需要先对向量进行归一化
                    faiss.normalize_L2(vector_array)
                    index = faiss.IndexFlatIP(dimensions)
                elif vector_db_config.metric.lower() == "l2":
                    index = faiss.IndexFlatL2(dimensions)  # L2距离
                else:  # "ip" 内积
                    index = faiss.IndexFlatIP(dimensions)  # 内积

                # 将向量添加到索引
                if len(vectors) > 0:
                    print(
                        f"[SERVICE LOG IndexService._create_faiss_index] 添加{len(vectors)}个向量到索引，每个维度为{dimensions}"
                    )
                    index.add(vector_array)

                    # 保存索引到文件
                    print(
                        f"[SERVICE LOG IndexService._create_faiss_index] 保存FAISS索引到: {index_path}"
                    )
                    faiss.write_index(index, index_path)
                    print(
                        "[SERVICE LOG IndexService._create_faiss_index] FAISS索引已成功保存"
                    )
                else:
                    print(
                        "[SERVICE WARNING IndexService._create_faiss_index] 没有向量可添加到索引"
                    )
            except ImportError as e:
                print(
                    f"[SERVICE ERROR IndexService._create_faiss_index] 无法导入FAISS库: {str(e)}"
                )
                print(
                    "[SERVICE ERROR IndexService._create_faiss_index] 请确保已安装FAISS: pip install faiss-cpu 或 pip install faiss-gpu"
                )
                raise
            except Exception as e:
                print(
                    f"[SERVICE ERROR IndexService._create_faiss_index] 创建FAISS索引时出错: {str(e)}"
                )
                raise

            # 索引信息
            index_info = {
                "type": "faiss",
                "index_type": vector_db_config.index_type,  # 使用配置中的索引类型
                "metric": vector_db_config.metric,  # 使用配置中的度量方法
                "dimensions": dimensions,
                "num_vectors": len(vectors),
                "index_path": index_path,
            }

            return index_info
        except Exception as e:
            # 应该使用更具体的异常类型，但为保持兼容性先维持现状
            raise ValueError(f"FAISS索引创建失败: {str(e)}")

    def _create_chroma_index(
        self, embeddings: List[Dict[str, Any]], collection_name: str, index_name: str
    ) -> Dict[str, Any]:
        """创建Chroma索引"""
        try:
            # 获取Chroma配置
            vector_db_config = VectorDBConfig(
                provider=VectorDBProvider.CHROMA.value, index_mode=index_name
            )

            # 提取向量、ID和文本
            vectors = [emb.get("vector", []) for emb in embeddings]
            ids = [emb.get("id", "") for emb in embeddings]
            texts = [emb.get("text", "") for emb in embeddings]

            # 配置索引路径 - 使用vector_db_config中的db_path确保路径一致性
            index_path = os.path.join(
                vector_db_config.db_path, f"{collection_name}_{index_name}"
            )
            os.makedirs(index_path, exist_ok=True)

            print(
                f"[SERVICE LOG IndexService._create_chroma_index] 正在创建Chroma索引: {index_path}"
            )

            try:
                # 在这里添加实际的Chroma索引创建代码
                # 由于可能需要安装chromadb包，我们先添加一个基本结构
                # 如果需要实际实现，请确保已安装chromadb: pip install chromadb

                # 尝试导入chromadb
                try:
                    import chromadb

                    # 创建客户端
                    client = chromadb.PersistentClient(path=vector_db_config.db_path)

                    # 创建或获取集合
                    collection = client.create_collection(
                        name=f"{collection_name}_{index_name}",
                        metadata={"hnsw:space": vector_db_config.distance_function},
                    )

                    # 将向量添加到集合
                    if len(vectors) > 0 and len(ids) > 0:
                        print(
                            f"[SERVICE LOG IndexService._create_chroma_index] 添加{len(vectors)}个向量到Chroma集合"
                        )

                        # 确保所有ID都是字符串
                        str_ids = [str(id) for id in ids]

                        # 添加向量
                        collection.add(
                            embeddings=vectors,
                            ids=str_ids,
                            documents=texts if texts and all(texts) else None,
                        )

                        print(
                            f"[SERVICE LOG IndexService._create_chroma_index] Chroma索引已成功保存到 {index_path}"
                        )
                    else:
                        print(
                            "[SERVICE WARNING IndexService._create_chroma_index] 没有向量可添加到Chroma索引"
                        )

                except ImportError:
                    print(
                        "[SERVICE WARNING IndexService._create_chroma_index] chromadb未安装，无法创建实际的Chroma索引"
                    )
                    print(
                        "[SERVICE WARNING IndexService._create_chroma_index] 如需使用Chroma，请安装: pip install chromadb"
                    )

            except Exception as e:
                print(
                    f"[SERVICE ERROR IndexService._create_chroma_index] 创建Chroma索引时出错: {str(e)}"
                )
                # 不抛出异常，以保持与原代码一致，仅记录错误

            # 索引信息
            index_info = {
                "type": "chroma",
                "collection_name": collection_name
                if collection_name
                else vector_db_config.collection_name,
                "distance_function": vector_db_config.distance_function,
                "dimensions": len(vectors[0]) if vectors else 0,
                "num_vectors": len(vectors),
                "index_path": index_path,
            }

            return index_info
        except Exception as e:
            # 应该使用更具体的异常类型，但为保持兼容性先维持现状
            raise ValueError(f"Chroma索引创建失败: {str(e)}")

    def _index_to_milvus(
        self,
        embeddings: List[Dict[str, Any]],
        collection_name: str,
        config: VectorDBConfig,
    ) -> Dict[str, Any]:
        """
        Insert embeddings into Milvus collection
        """
        # connect to Milvus
        connections.connect(alias="default", uri=config.milvus_uri)
        try:
            # prepare schema
            dim = len(embeddings[0].get("vector", [])) if embeddings else 0
            fields = [
                FieldSchema(
                    name="id", dtype=DataType.INT64, is_primary=True, auto_id=True
                ),
                FieldSchema(
                    name="vector",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=dim,
                    params=config.get_index_params(),
                ),
            ]
            schema = CollectionSchema(
                fields=fields, description=f"Milvus collection for {collection_name}"
            )
            collection = Collection(name=collection_name, schema=schema)
            # insert data
            vectors = [emb.get("vector", []) for emb in embeddings]
            insert_result = collection.insert([vectors])
            # create index
            collection.create_index(
                field_name="vector", index_params=config.get_index_params()
            )
            collection.load()
            return {
                "type": "milvus",
                "collection_name": collection_name,
                "dimensions": dim,
                "num_vectors": len(vectors),
                "index_size": len(insert_result.primary_keys),
            }
        except Exception as e:
            raise ValueError(f"Milvus索引创建失败: {str(e)}")
        finally:
            connections.disconnect("default")
