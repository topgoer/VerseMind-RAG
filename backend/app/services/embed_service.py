import os
import json
import datetime
import uuid
import numpy as np
from typing import Dict, List, Any, Optional
import logging
import toml
from pathlib import Path
from enum import Enum
import boto3
from app.core.logger import get_logger_with_env_level

# Initialize logger using the environment-based configuration
logger = get_logger_with_env_level(__name__)


# 新增：嵌入提供商枚举
class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    BEDROCK = "bedrock"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"  # Added Ollama provider
    DEEPSEEK = "deepseek"  # Added DeepSeek provider


# 新增：嵌入配置类
class EmbeddingConfig:
    def __init__(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name
        self.aws_region = os.getenv("AWS_REGION", "ap-southeast-1")


# 新增：工厂类动态创建 embedding function
class EmbeddingFactory:
    @staticmethod
    def create_embedding_function(config: EmbeddingConfig):
        # Remove global import of Embedding classes to avoid metaclass conflicts; will lazy import in factory
        try:
            # Get logger from module
            _logger = logging.getLogger(__name__)
            _logger.debug(
                f"Creating embedding function with provider: {config.provider}, model: {config.model_name}"
            )

            if config.provider == EmbeddingProvider.BEDROCK:
                from langchain_community.embeddings import BedrockEmbeddings

                client = boto3.client(
                    "bedrock-runtime",
                    region_name=config.aws_region,
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                )
                return BedrockEmbeddings(client=client, model_id=config.model_name)
            elif config.provider == EmbeddingProvider.OPENAI:
                from langchain_community.embeddings import OpenAIEmbeddings

                return OpenAIEmbeddings(
                    model=config.model_name, openai_api_key=os.getenv("OPENAI_API_KEY")
                )
            elif config.provider == EmbeddingProvider.HUGGINGFACE:
                from langchain_community.embeddings import HuggingFaceEmbeddings

                return HuggingFaceEmbeddings(model_name=config.model_name)
            elif config.provider == EmbeddingProvider.OLLAMA:
                # Use direct implementation for Ollama embeddings to avoid metaclass conflict
                from langchain_core.embeddings import Embeddings
                import requests

                class CustomOllamaEmbeddings(Embeddings):
                    """Custom implementation of Ollama embeddings to avoid pydantic version conflicts"""

                    def __init__(
                        self, model: str, base_url: str = "http://localhost:11434"
                    ):
                        # 修复模型名称格式问题：确保 BGE 模型使用正确的名称格式 (with : instead of -)
                        if (
                            "-latest" in model
                            and "bge" in model.lower()
                            and ":" not in model
                        ):
                            model = model.replace("-latest", ":latest")
                            _logger.debug(
                                f"Fixed model name format for Ollama BGE model: {model}"
                            )

                        self.model = model
                        self.base_url = base_url

                    def embed_documents(self, texts: List[str]) -> List[List[float]]:
                        """Embed a list of documents using Ollama API"""
                        embeddings = []
                        for text in texts:
                            embeddings.append(self.embed_query(text))
                        return embeddings

                    def embed_query(self, text: str) -> List[float]:
                        """Embed a query using Ollama API"""
                        response = requests.post(
                            f"{self.base_url}/api/embeddings",
                            headers={"Content-Type": "application/json"},
                            json={"model": self.model, "prompt": text},
                            timeout=180,  # 增加超时时间以避免嵌入生成超时
                        )
                        if response.status_code != 200:
                            raise ValueError(f"Error from Ollama API: {response.text}")
                        return response.json()["embedding"]

                return CustomOllamaEmbeddings(model=config.model_name)
            elif config.provider == EmbeddingProvider.DEEPSEEK:
                # Implement DeepSeek embedding if available
                from langchain_community.embeddings import OpenAIEmbeddings

                return OpenAIEmbeddings(
                    model=config.model_name,
                    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
                )
            else:
                raise ValueError(f"Unsupported embedding provider: {config.provider}")
        except Exception as e:
            _logger.error(f"Error creating embedding function: {str(e)}")
            raise


class EmbedService:
    """向量嵌入服务，支持多种 provider 和批量调用"""

    def __init__(self):
        # Use correct base directory
        self.storage_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../..")
        )
        # Fixed paths to use backend directory structure
        self.documents_dir = os.path.join(self.storage_dir, "storage", "documents")
        self.chunks_dir = os.path.join(self.storage_dir, "backend", "02-chunked-docs")
        self.parsed_dir = os.path.join(self.storage_dir, "backend", "03-parsed-docs")
        self.embeddings_dir = os.path.join(
            self.storage_dir, "backend", "04-embedded-docs"
        )
        self.indices_dir = os.path.join(
            self.storage_dir, "backend", "storage", "indices"
        )

        # Create directories if they don't exist
        os.makedirs(self.documents_dir, exist_ok=True)
        os.makedirs(self.chunks_dir, exist_ok=True)
        os.makedirs(self.parsed_dir, exist_ok=True)
        os.makedirs(self.embeddings_dir, exist_ok=True)

        self.factory = EmbeddingFactory()
        self.logger = logger

    def _load_config(self) -> dict:
        """
        从config.toml加载配置
        """
        project_root = Path(self.storage_dir)
        config_path = project_root / "config" / "config.toml"
        example_path = project_root / "config" / "config.example.toml"

        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return toml.load(f)
            elif example_path.exists():
                with open(example_path, "r", encoding="utf-8") as f:
                    return toml.load(f)
            else:
                self.logger.warning(
                    "No configuration file found. Using default values."
                )
                return {}
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}

    def get_embedding_models(self) -> Dict[str, Any]:
        """
        从配置文件获取所有可用的嵌入模型信息
        """
        try:
            config = self._load_config()
            self.logger.debug(f"Loaded config: {config}")

            # 从配置中获取嵌入模型
            if "embedding_models" in config:
                self.logger.debug("Loading embedding models from config file")
                return config["embedding_models"]

            # 如果配置中没有找到嵌入模型，返回默认值
            self.logger.warning(
                "No embedding_models found in config. Using default values."
            )
            default_models = {
                "providers": {
                    "ollama": [
                        {"id": "bge-m3:latest", "name": "BGE-m3", "dimensions": 1024},
                        {
                            "id": "BGE-large:latest",
                            "name": "BGE-Large",
                            "dimensions": 1024,
                        },
                    ],
                    "openai": [
                        {
                            "id": "text-embedding-ada-002",
                            "name": "Ada",
                            "dimensions": 1536,
                        }
                    ],
                }
            }
            self.logger.debug(f"Returning default models: {default_models}")
            return default_models
        except Exception as e:
            self.logger.error(f"Error getting embedding models: {str(e)}")
            # 返回默认值
            default_models = {
                "providers": {
                    "ollama": [
                        {"id": "bge-m3:latest", "name": "BGE-m3", "dimensions": 1024},
                        {
                            "id": "BGE-large:latest",
                            "name": "BGE-Large",
                            "dimensions": 1024,
                        },
                    ],
                    "openai": [
                        {
                            "id": "text-embedding-ada-002",
                            "name": "Ada",
                            "dimensions": 1536,
                        }
                    ],
                }
            }
            self.logger.debug(
                f"Returning default models due to error: {default_models}"
            )
            return default_models

    def create_embeddings(
        self, document_id: str, provider: str, model: str
    ) -> Dict[str, Any]:
        """
        为文档创建嵌入向量
        """
        self.logger.debug(
            f"Creating embeddings for document_id: {document_id} with provider: {provider}, model: {model}"
        )

        # 创建嵌入配置与函数
        embed_fn = self._create_embedding_function(provider, model)

        # 加载并提取文本内容
        text_chunks = self._load_and_extract_text_chunks(document_id)

        # 生成嵌入向量
        results, dimensions = self._generate_embeddings(text_chunks, embed_fn, provider)

        # 保存结果并返回
        return self._save_embedding_results(
            document_id, provider, model, results, dimensions
        )

    def _create_embedding_function(self, provider: str, model: str):
        """创建嵌入函数"""
        config = EmbeddingConfig(provider, model)
        try:
            return self.factory.create_embedding_function(config)
        except Exception as e:
            self.logger.error(f"Error creating embedding function: {str(e)}")
            raise ValueError(f"创建嵌入函数失败: {str(e)}")

    def _load_and_extract_text_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Load parsed document and extract text chunks for embedding"""
        # Find the parsed file
        parsed_file = self._find_parsed_file(document_id)
        if not parsed_file:
            self._handle_missing_parsed_file(document_id)

        # Load and process the parsed file
        return self._process_parsed_file(parsed_file, document_id)

    def _handle_missing_parsed_file(self, document_id: str) -> None:
        """Handle the case when a parsed file is not found"""
        # Collect all locations where we searched
        search_paths = [
            self.parsed_dir,
            os.path.join(self.storage_dir, "backend", "03-parsed-docs"),
            os.path.join(self.storage_dir, "03-parsed-docs"),
            os.path.join(self.storage_dir, "backend/03-parsed-docs"),
        ]

        # Build detailed error message
        error_msg = self._build_missing_file_error_message(document_id, search_paths)
        self.logger.error(error_msg)

        # Raise exception with user-friendly message
        raise FileNotFoundError(
            f"请先对文档ID {document_id} 进行解析处理 (Please process document ID {document_id} first)"
        )

    def _build_missing_file_error_message(
        self, document_id: str, search_paths: List[str]
    ) -> str:
        """Build a detailed error message for missing parsed file"""
        error_msg = f"Parsed file not found for document ID: {document_id}. Please parse the document first.\n"
        error_msg += "Locations searched:\n"

        for path in search_paths:
            if os.path.exists(path):
                error_msg += f" - {path} (exists)\n"
                # Show sample files from the directory
                try:
                    files = os.listdir(path)
                    error_msg += f"   Files in directory ({len(files)} total):\n"
                    for i, f in enumerate(files[:5]):  # Show only first 5 files
                        error_msg += f"   - {f}\n"
                    if len(files) > 5:
                        error_msg += f"   - ... and {len(files) - 5} more files\n"
                except Exception as e:
                    error_msg += f"   Error listing files: {str(e)}\n"
            else:
                error_msg += f" - {path} (does not exist)\n"

        return error_msg

    def _process_parsed_file(
        self, parsed_file: str, document_id: str
    ) -> List[Dict[str, Any]]:
        """Process the parsed file and extract text chunks"""
        try:
            self.logger.debug(f"Loading parsed file: {parsed_file}")
            with open(parsed_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract text chunks from the content
            text_chunks = self._extract_text_chunks_from_content(
                data.get("content", {})
            )
            self.logger.debug(f"Extracted {len(text_chunks)} text chunks for embedding")

            # Add document_id to each chunk's metadata for traceability
            for chunk in text_chunks:
                if "metadata" in chunk:
                    chunk["metadata"]["document_id"] = document_id

            # Validate we have chunks to process
            if not text_chunks:
                self.logger.error("No text chunks found for embedding")
                raise ValueError(
                    "没有提取到可嵌入的文本块 (No text chunks extracted for embedding)"
                )

            return text_chunks

        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON from file {parsed_file}: {str(e)}")
            raise ValueError(f"解析文件格式错误: {str(e)} (Error parsing JSON file)")
        except Exception as e:
            self.logger.error(f"Error processing parsed file {parsed_file}: {str(e)}")
            raise ValueError(
                f"处理解析文件时出错: {str(e)} (Error processing parsed file)"
            )

    def _extract_text_chunks_from_content(self, content) -> List[Dict[str, Any]]:
        """从内容中提取文本块"""
        text_chunks = []

        if isinstance(content, dict) and "sections" in content:
            text_chunks = self._extract_from_sections(content["sections"])
        elif isinstance(content, list):
            text_chunks = self._extract_from_list_content(content)

        return text_chunks

    def _extract_from_sections(self, sections) -> List[Dict[str, Any]]:
        """从章节格式中提取文本块"""
        text_chunks = []

        for section in sections:
            # 添加章节标题
            text_chunks.extend(self._extract_section_title(section))

            # 添加段落
            text_chunks.extend(self._extract_section_paragraphs(section))

            # 处理子章节
            text_chunks.extend(self._extract_subsections(section))

        return text_chunks

    def _extract_section_title(self, section) -> List[Dict[str, Any]]:
        """提取章节标题"""
        chunks = []
        if "title" in section and section["title"]:
            chunks.append(
                {
                    "content": section["title"],
                    "metadata": {"type": "heading", "level": section.get("level", 1)},
                }
            )
        return chunks

    def _extract_section_paragraphs(self, section) -> List[Dict[str, Any]]:
        """提取章节段落"""
        chunks = []
        for para in section.get("paragraphs", []):
            if "text" in para and para["text"]:
                chunks.append(
                    {
                        "content": para["text"],
                        "metadata": {
                            "type": "paragraph",
                            "section": section.get("title", ""),
                        },
                    }
                )
        return chunks

    def _extract_subsections(self, section) -> List[Dict[str, Any]]:
        """提取子章节内容"""
        chunks = []
        for subsection in section.get("subsections", []):
            # 添加子章节标题
            if "title" in subsection and subsection["title"]:
                chunks.append(
                    {
                        "content": subsection["title"],
                        "metadata": {
                            "type": "heading",
                            "level": subsection.get("level", 2),
                        },
                    }
                )

            # 添加子章节段落
            for para in subsection.get("paragraphs", []):
                if "text" in para and para["text"]:
                    chunks.append(
                        {
                            "content": para["text"],
                            "metadata": {
                                "type": "paragraph",
                                "section": subsection.get("title", ""),
                            },
                        }
                    )
        return chunks

    def _extract_from_list_content(self, content) -> List[Dict[str, Any]]:
        """从列表格式内容中提取文本块"""
        text_chunks = []
        for item in content:
            item_type = item.get("type")
            if item_type == "text" and "content" in item:
                text_chunks.append(
                    {
                        "content": item["content"],
                        "metadata": {"type": "paragraph", "page": item.get("page")},
                    }
                )
            elif item_type == "table" and "content" in item:
                # 表格内容转成文本
                table_text = str(item["content"])
                text_chunks.append(
                    {
                        "content": table_text,
                        "metadata": {"type": "table", "page": item.get("page")},
                    }
                )
        return text_chunks

    def _generate_embeddings(
        self, text_chunks: List[Dict[str, Any]], embed_fn, provider: str
    ) -> tuple:
        """生成嵌入向量"""
        dimensions = self._get_model_dimensions(provider)
        results = []

        try:
            if provider == EmbeddingProvider.OPENAI.value:
                results, dimensions = self._generate_openai_embeddings(
                    text_chunks, embed_fn, dimensions
                )
            else:
                results, dimensions = self._generate_single_embeddings(
                    text_chunks, embed_fn, dimensions
                )
        except Exception as e:
            self.logger.error(f"Error during embedding generation: {str(e)}")
            raise ValueError(f"生成嵌入向量失败: {str(e)}")

        return results, dimensions

    def _get_model_dimensions(self, provider: str) -> int:
        """获取模型维度信息"""
        try:
            model_info = next(
                (
                    model_info
                    for provider_info in self.get_embedding_models().values()
                    for model_info in provider_info
                    if model_info["id"] == provider
                ),
                None,
            )

            if model_info:
                return model_info["dimensions"]
        except Exception as e:
            self.logger.warning(f"Error getting model dimensions: {str(e)}")
        return 0

    def _generate_openai_embeddings(
        self, text_chunks: List[Dict[str, Any]], embed_fn, dimensions: int
    ) -> tuple:
        """生成OpenAI嵌入向量（批量处理）"""
        results = []
        BATCH_SIZE = 20

        for i in range(0, len(text_chunks), BATCH_SIZE):
            batch = text_chunks[i : i + BATCH_SIZE]
            texts = [c["content"] for c in batch]
            self.logger.debug(
                f"Processing batch {i // BATCH_SIZE + 1} with {len(texts)} chunks"
            )

            vecs = embed_fn.embed_documents(texts)

            if vecs and len(vecs) > 0 and dimensions == 0:
                dimensions = len(vecs[0])

            for c, v in zip(batch, vecs):
                results.append(self._create_embedding_result(c, v))

        return results, dimensions

    def _generate_single_embeddings(
        self, text_chunks: List[Dict[str, Any]], embed_fn, dimensions: int
    ) -> tuple:
        """生成单条嵌入向量"""
        results = []

        for c in text_chunks:
            v = embed_fn.embed_query(c["content"])

            if v and len(v) > 0 and dimensions == 0:
                dimensions = len(v)

            results.append(self._create_embedding_result(c, v))

        return results, dimensions

    def _create_embedding_result(
        self, chunk: Dict[str, Any], vector: List[float]
    ) -> Dict[str, Any]:
        """创建嵌入结果对象"""
        return {
            "vector": vector,
            "metadata": chunk["metadata"],
            "text": chunk["content"][:100]
            + ("..." if len(chunk["content"]) > 100 else ""),
        }

    def _save_embedding_results(
        self,
        document_id: str,
        provider: str,
        model: str,
        results: List[Dict[str, Any]],
        dimensions: int,
    ) -> Dict[str, Any]:
        """保存嵌入结果并返回响应"""
        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        embedding_id = str(uuid.uuid4())[:8]

        # 保存嵌入文件
        result_file, result_path = self._generate_result_file_path(
            document_id, provider, model, timestamp
        )

        embedding_data = {
            "document_id": document_id,
            "embedding_id": embedding_id,
            "provider": provider,
            "model": model,
            "timestamp": timestamp,
            "dimensions": dimensions,
            "total_embeddings": len(results),
            "embeddings": results,
        }

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(
                embedding_data, f, ensure_ascii=False, cls=self.CompactJSONEncoder
            )

        self.logger.debug(
            f"Successfully created embeddings for document {document_id}. Result saved to: {result_path}"
        )

        # 返回详细的嵌入结果信息
        return {
            "document_id": document_id,
            "embedding_id": embedding_id,
            "provider": provider,
            "model": model,
            "dimensions": dimensions,
            "total_embeddings": len(results),
            "result_file": result_file,
            "message": f"嵌入向量生成成功，已存储为 {result_file}",
        }

    def _generate_result_file_path(
        self, document_id: str, provider: str, model: str, timestamp: str
    ) -> tuple:
        """生成结果文件路径"""
        # 替换模型名称中的无效字符（Windows不允许文件名中包含 : / \ * ? " < > |）
        sanitized_model = (
            model.replace(":", "-")
            .replace("/", "-")
            .replace("\\", "-")
            .replace("*", "-")
            .replace("?", "-")
            .replace('"', "-")
            .replace("<", "-")
            .replace(">", "-")
            .replace("|", "-")
        )
        result_file = (
            f"{document_id}_{provider}_{sanitized_model}_{timestamp}_embedded.json"
        )
        result_path = os.path.join(self.embeddings_dir, result_file)
        return result_file, result_path

    def list_embeddings(
        self, document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出所有嵌入向量文件
        """
        self.logger.debug(
            f"Listing embeddings for document_id: {document_id if document_id else 'all'}"
        )

        try:
            # Ensure directory exists
            os.makedirs(self.embeddings_dir, exist_ok=True)

            # Validate directory and get file list
            files = self._get_embedding_files()

            # Process embedding files
            results = self._process_embedding_files(files, document_id)

            self.logger.debug(f"Found {len(results)} embedding files")
            return results

        except Exception as e:
            self.logger.error(f"Unexpected error in list_embeddings: {str(e)}")
            return []

    def _get_embedding_files(self) -> List[str]:
        """Helper method to get list of embedding files"""
        # Check if directory exists and is valid
        if not os.path.exists(self.embeddings_dir) or not os.path.isdir(
            self.embeddings_dir
        ):
            self.logger.warning(
                f"Embeddings directory does not exist or is not a directory: {self.embeddings_dir}"
            )
            return []

        # Get file list
        try:
            return os.listdir(self.embeddings_dir)
        except Exception as e:
            self.logger.error(f"Error listing files in embeddings directory: {str(e)}")
            return []

    def _process_embedding_files(
        self, files: List[str], document_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Helper method to process embedding files and extract metadata"""
        results = []

        for filename in files:
            # Skip files that don't match our pattern
            if not filename.endswith("_embedded.json"):
                continue

            # Skip files that don't match document_id filter if provided
            if document_id and not filename.startswith(document_id):
                continue

            # Process matching file
            embedding_info = self._extract_embedding_info(filename)
            if embedding_info:
                results.append(embedding_info)

        return results

    def _extract_embedding_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Extract embedding information from a file"""
        file_path = os.path.join(self.embeddings_dir, filename)

        # Verify file exists and is a file
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            self.logger.warning(f"Embedding file not found or not a file: {file_path}")
            return None

        try:
            # Read and parse the embedding data
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract basic information
            return {
                "document_id": data.get("document_id", ""),
                "embedding_id": data.get("embedding_id", ""),
                "provider": data.get("provider", ""),
                "model": data.get("model", ""),
                "dimensions": data.get("dimensions", 0),
                "total_embeddings": data.get("total_embeddings", 0),
                "timestamp": data.get("timestamp", ""),
                "filename": filename,
            }
        except json.JSONDecodeError as e:
            self.logger.error(
                f"JSON decode error in embedding file {filename}: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Error reading embedding file {filename}: {str(e)}")

        return None

    def delete_embedding(self, embedding_id: str) -> Dict[str, Any]:
        """
        删除指定ID的嵌入向量文件
        """
        self.logger.debug(f"Deleting embedding with ID: {embedding_id}")

        # 确保目录存在
        os.makedirs(self.embeddings_dir, exist_ok=True)

        # 遍历嵌入文件目录查找匹配的文件
        found = False
        for filename in os.listdir(self.embeddings_dir):
            if filename.endswith("_embedded.json"):
                file_path = os.path.join(self.embeddings_dir, filename)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if data.get("embedding_id") == embedding_id:
                        found = True
                        os.remove(file_path)
                        self.logger.debug(
                            f"Successfully deleted embedding file: {filename}"
                        )
                        return {
                            "status": "success",
                            "message": f"嵌入 {embedding_id} 已删除",
                            "embedding_id": embedding_id,
                            "filename": filename,
                        }
                except Exception as e:
                    self.logger.error(
                        f"Error processing embedding file {filename}: {str(e)}"
                    )

        if not found:
            raise FileNotFoundError(f"未找到ID为 {embedding_id} 的嵌入向量")

        return {"status": "error", "message": "删除失败"}

    def generate_embedding_vector(
        self, text: str, provider: str = "ollama", model: str = "bge-m3"
    ) -> List[float]:
        """
        为文本生成嵌入向量，用于搜索功能

        参数:
            text: 要嵌入的文本
            provider: 嵌入服务提供商（默认：ollama）
            model: 嵌入模型（默认：bge-m3）

        返回:
            嵌入向量（浮点数列表）
        """
        self.logger.debug(
            f"Generating embedding vector for text with provider: {provider}, model: {model}"
        )

        try:
            # 修复模型名称格式
            corrected_model = self._correct_ollama_model_name(provider, model)

            # 创建嵌入配置与函数
            config = EmbeddingConfig(provider, corrected_model)
            embed_fn = self.factory.create_embedding_function(config)

            # 生成向量
            vector = embed_fn.embed_query(text)
            self.logger.debug(
                f"Successfully generated vector with dimensions: {len(vector)}"
            )
            return vector
        except Exception as e:
            self.logger.error(f"Error generating embedding vector: {str(e)}")
            self.logger.warning(
                "Falling back to random vector for development/debugging"
            )

            # 如果生成失败，返回随机向量（仅用于开发调试）
            return self._generate_fallback_vector(provider, model)

    def _correct_ollama_model_name(self, provider: str, model: str) -> str:
        """修复 Ollama 模型名称格式问题"""
        if provider.lower() == "ollama" and "-" in model and ":" not in model:
            # 检查是否是文件名处理导致的格式问题
            # 例如：'bge-m3-latest' 应该是 'bge-m3:latest'
            if model.endswith("-latest") and "bge" in model.lower():
                restored_model = model.replace("-latest", ":latest")
                self.logger.debug(
                    f"Restored Ollama model name format: '{model}' -> '{restored_model}'"
                )
                return restored_model
        return model

    def _generate_fallback_vector(self, provider: str, model: str) -> List[float]:
        """生成降级向量（用于开发调试）"""
        import numpy as np

        dimensions = self._determine_fallback_dimensions(provider, model)

        # 使用现代numpy随机生成器
        rng = np.random.default_rng(42)  # 固定种子以便调试
        vector = rng.standard_normal(dimensions)
        vector = vector / np.linalg.norm(vector)  # 归一化

        return vector.tolist()

    def _determine_fallback_dimensions(self, provider: str, model: str) -> int:
        """确定降级向量的维度"""
        dimensions = 384  # 默认维度

        # 根据模型确定维度
        if provider == "openai":
            if model == "text-embedding-3-small":
                dimensions = 1536
            elif model == "text-embedding-3-large":
                dimensions = 3072
        elif provider == "ollama" or provider == "baai":
            if "bge" in model.lower():
                dimensions = 1024

        return dimensions

    # 新增：自定义紧凑 JSON 编码
    class CompactJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (int, float, str, bool, list, dict)):
                return obj
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            return super().default(obj)

        def encode(self, obj):
            def fmt(o):
                if isinstance(o, list) and o and isinstance(o[0], (int, float)):
                    return "[" + ",".join(map(str, o)) + "]"
                if isinstance(o, list):
                    return [fmt(i) for i in o]
                if isinstance(o, dict):
                    return {k: fmt(v) for k, v in o.items()}
                return o

            return super().encode(fmt(obj))

    def _find_document(self, document_id: str) -> Optional[str]:
        """查找指定ID的文档路径"""
        self.logger.debug(
            f"Searching for document with ID: {document_id} in {self.documents_dir}"
        )
        if os.path.exists(self.documents_dir):
            for filename in os.listdir(self.documents_dir):
                if document_id in filename:
                    self.logger.debug(f"Found document: {filename}")
                    return os.path.join(self.documents_dir, filename)
        self.logger.warning(
            f"Document with ID: {document_id} not found in {self.documents_dir}"
        )
        return None

    def _find_parsed_file(self, document_id: str) -> Optional[str]:
        """Find the parsed file for a document by ID"""
        self.logger.debug(f"Searching for parsed file for document ID: {document_id}")

        # Get all search paths
        search_paths = self._get_parsed_file_search_paths()

        # Log the search paths
        self._log_search_paths(search_paths)

        # Try to find the file in each path
        return self._search_in_all_paths(search_paths, document_id)

    def _get_parsed_file_search_paths(self) -> List[str]:
        """Get all possible paths where parsed files might be located"""
        return [
            self.parsed_dir,  # Primary path
            os.path.join(
                self.storage_dir, "backend", "03-parsed-docs"
            ),  # Backend folder path
            os.path.join(self.storage_dir, "03-parsed-docs"),  # Root directory path
            os.path.join(self.storage_dir, "backend/03-parsed-docs"),  # Alt path format
            os.path.join(
                os.path.dirname(__file__), "../../../../backend/03-parsed-docs"
            ),  # Absolute path
        ]

    def _log_search_paths(self, search_paths: List[str]) -> None:
        """Log all search paths and whether they exist"""
        for i, path in enumerate(search_paths):
            self.logger.debug(f"Search path {i + 1}: {path}")
            if os.path.exists(path):
                self.logger.debug(f"Path {i + 1} exists")
            else:
                self.logger.debug(f"Path {i + 1} does NOT exist")

    def _search_in_all_paths(
        self, search_paths: List[str], document_id: str
    ) -> Optional[str]:
        """Search for the parsed file in all given paths"""
        for path in search_paths:
            result = self._search_in_directory(path, document_id)
            if result:
                return result

        self.logger.warning(
            f"Parsed file for document ID: {document_id} not found in any searched location"
        )
        return None

    def _search_in_directory(self, directory: str, document_id: str) -> Optional[str]:
        """Search for a parsed file in a specific directory"""
        if not os.path.exists(directory):
            return None

        self.logger.debug(f"Searching in: {directory}")

        for filename in os.listdir(directory):
            if self._is_matching_parsed_file(filename, document_id):
                self.logger.info(f"Found parsed file: {filename}")
                return os.path.join(directory, filename)

        return None

    def _is_matching_parsed_file(self, filename: str, document_id: str) -> bool:
        """Check if a filename matches our parsed file pattern and document ID"""
        # First check if this is a parsed file and contains the document ID
        if not filename.endswith("_parsed.json") or document_id not in filename:
            return False

        # Files are named as: {document_name}_{document_id}_{timestamp}_parsed.json
        # or: {document_id}_{timestamp}_parsed.json (legacy format)
        parts = filename.replace("_parsed.json", "").split("_")

        # If document_id is one of the parts, this is a match
        return document_id in parts
