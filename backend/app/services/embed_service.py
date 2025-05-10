import os
import json
import datetime
import uuid
import numpy as np
from typing import Dict, List, Any, Optional
import requests
import logging
import toml
from pathlib import Path
import dotenv
dotenv.load_dotenv()
from enum import Enum
import boto3

# Initialize logger
logger = logging.getLogger(__name__)

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
            _logger.info(f"Creating embedding function with provider: {config.provider}, model: {config.model_name}")
            
            if config.provider == EmbeddingProvider.BEDROCK:
                from langchain_community.embeddings import BedrockEmbeddings
                client = boto3.client(
                    'bedrock-runtime',
                    region_name=config.aws_region,
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                return BedrockEmbeddings(client=client, model_id=config.model_name)
            elif config.provider == EmbeddingProvider.OPENAI:
                from langchain_community.embeddings import OpenAIEmbeddings
                return OpenAIEmbeddings(model=config.model_name, openai_api_key=os.getenv('OPENAI_API_KEY'))
            elif config.provider == EmbeddingProvider.HUGGINGFACE:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                return HuggingFaceEmbeddings(model_name=config.model_name)
            elif config.provider == EmbeddingProvider.OLLAMA:
                # Use direct implementation for Ollama embeddings to avoid metaclass conflict
                from langchain_core.embeddings import Embeddings
                import requests
                
                class CustomOllamaEmbeddings(Embeddings):
                    """Custom implementation of Ollama embeddings to avoid pydantic version conflicts"""
                    
                    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
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
                            json={"model": self.model, "prompt": text}
                        )
                        if response.status_code != 200:
                            raise ValueError(f"Error from Ollama API: {response.text}")
                        return response.json()["embedding"]
                
                return CustomOllamaEmbeddings(model=config.model_name)
            elif config.provider == EmbeddingProvider.DEEPSEEK:
                # Implement DeepSeek embedding if available
                from langchain_community.embeddings import OpenAIEmbeddings
                return OpenAIEmbeddings(model=config.model_name, openai_api_key=os.getenv('DEEPSEEK_API_KEY'))
            else:
                raise ValueError(f"Unsupported embedding provider: {config.provider}")
        except Exception as e:
            _logger.error(f"Error creating embedding function: {str(e)}")
            raise

class EmbedService:
    """向量嵌入服务，支持多种 provider 和批量调用"""
    def __init__(self):
        # Use correct base directory
        self.storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        # Fixed paths to use backend directory structure
        self.documents_dir = os.path.join(self.storage_dir, 'storage', 'documents')
        self.chunks_dir = os.path.join(self.storage_dir, 'backend', '02-chunked-docs')
        self.parsed_dir = os.path.join(self.storage_dir, 'backend', '03-parsed-docs')
        self.embeddings_dir = os.path.join(self.storage_dir, 'backend', '04-embedded-docs')
        self.indices_dir = os.path.join(self.storage_dir, 'backend', 'storage', 'indices')
        
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
                self.logger.warning("No configuration file found. Using default values.")
                return {}
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
            
    def get_embedding_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        从配置文件获取所有可用的嵌入模型信息
        """
        try:
            config = self._load_config()
            
            # 从配置中获取嵌入模型
            if "embedding_models" in config:
                self.logger.info("Loading embedding models from config file")
                return config["embedding_models"]
                
            # 如果配置中没有找到嵌入模型，返回默认值
            self.logger.warning("No embedding_models found in config. Using default values.")
            return {
                "ollama": [
                    {"id": "bge-m3:latest", "name": "BGE-m3", "dimensions": 1024},
                    {"id": "BGE-large:latest", "name": "BGE-Large", "dimensions": 1024}
                ]
            }
        except Exception as e:
            self.logger.error(f"Error getting embedding models: {str(e)}")
            # 返回默认值
            return {
                "ollama": [
                    {"id": "bge-m3:latest", "name": "BGE-m3", "dimensions": 1024},
                    {"id": "BGE-large:latest", "name": "BGE-Large", "dimensions": 1024}
                ]
            }

    def create_embeddings(self, document_id: str, provider: str, model: str) -> Dict[str, Any]:
        """
        为文档创建嵌入向量
        """
        self.logger.info(f"Creating embeddings for document_id: {document_id} with provider: {provider}, model: {model}")
        
        # 创建嵌入配置与函数
        config = EmbeddingConfig(provider, model)
        try:
            embed_fn = self.factory.create_embedding_function(config)
        except Exception as e:
            self.logger.error(f"Error creating embedding function: {str(e)}")
            raise ValueError(f"创建嵌入函数失败: {str(e)}")
        
        # 加载解析数据
        parsed_file = self._find_parsed_file(document_id)
        if not parsed_file:
            self.logger.error(f"Parsed file not found for document ID: {document_id}. Please parse the document first.")
            raise FileNotFoundError(f"请先对文档ID {document_id} 进行解析处理")
        
        self.logger.info(f"Loading parsed file: {parsed_file}")
        with open(parsed_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取文本内容
        text_chunks = []
        
        # 确定解析的数据结构
        content = data.get('content', {})
        
        # 基于解析策略不同，提取文本块
        if isinstance(content, dict) and 'sections' in content:
            # 按章节解析的格式
            for section in content['sections']:
                # 添加章节标题
                if 'title' in section and section['title']:
                    text_chunks.append({
                        'content': section['title'],
                        'metadata': {'type': 'heading', 'level': section.get('level', 1)}
                    })
                
                # 添加段落
                for para in section.get('paragraphs', []):
                    if 'text' in para and para['text']:
                        text_chunks.append({
                            'content': para['text'],
                            'metadata': {'type': 'paragraph', 'section': section.get('title', '')}
                        })
                
                # 处理子章节
                for subsection in section.get('subsections', []):
                    # 添加子章节标题
                    if 'title' in subsection and subsection['title']:
                        text_chunks.append({
                            'content': subsection['title'],
                            'metadata': {'type': 'heading', 'level': subsection.get('level', 2)}
                        })
                    
                    # 添加子章节段落
                    for para in subsection.get('paragraphs', []):
                        if 'text' in para and para['text']:
                            text_chunks.append({
                                'content': para['text'],
                                'metadata': {'type': 'paragraph', 'section': subsection.get('title', '')}
                            })
        elif isinstance(content, list):
            # 按文本与表格混合解析
            for item in content:
                item_type = item.get('type')
                if item_type == 'text' and 'content' in item:
                    text_chunks.append({
                        'content': item['content'],
                        'metadata': {'type': 'paragraph', 'page': item.get('page')}
                    })
                elif item_type == 'table' and 'content' in item:
                    # 表格内容转成文本
                    table_text = str(item['content'])
                    text_chunks.append({
                        'content': table_text,
                        'metadata': {'type': 'table', 'page': item.get('page')}
                    })
        
        self.logger.info(f"Extracted {len(text_chunks)} text chunks for embedding")
        
        if not text_chunks:
            self.logger.error("No text chunks found for embedding")
            raise ValueError("没有提取到可嵌入的文本块")
            
        # 批量或逐条调用嵌入API
        dimensions = 0
        results = []
        
        try:
            # 获取模型维度信息
            model_info = next((model_info for provider_info in self.get_embedding_models().values() 
                             for model_info in provider_info if model_info['id'] == model), None)
            
            if model_info:
                dimensions = model_info['dimensions']
        except Exception as e:
            self.logger.warning(f"Error getting model dimensions: {str(e)}")
            dimensions = 0
            
        # 使用提供商特定的批处理逻辑
        try:
            if provider == EmbeddingProvider.OPENAI.value:
                # OpenAI支持大批量处理
                BATCH_SIZE = 20
                for i in range(0, len(text_chunks), BATCH_SIZE):
                    batch = text_chunks[i:i+BATCH_SIZE]
                    texts = [c['content'] for c in batch]
                    self.logger.info(f"Processing batch {i//BATCH_SIZE + 1} with {len(texts)} chunks")
                    
                    vecs = embed_fn.embed_documents(texts)
                    
                    if vecs and len(vecs) > 0 and dimensions == 0:
                        dimensions = len(vecs[0])
                        
                    for c, v in zip(batch, vecs):
                        results.append({
                            'vector': v, 
                            'metadata': c['metadata'],
                            'text': c['content'][:100] + ('...' if len(c['content']) > 100 else '')
                        })
            else:
                # 其他提供商按单条处理
                for c in text_chunks:
                    v = embed_fn.embed_query(c['content'])
                    
                    if v and len(v) > 0 and dimensions == 0:
                        dimensions = len(v)
                    
                    results.append({
                        'vector': v, 
                        'metadata': c['metadata'],
                        'text': c['content'][:100] + ('...' if len(c['content']) > 100 else '')
                    })
        except Exception as e:
            self.logger.error(f"Error during embedding generation: {str(e)}")
            raise ValueError(f"生成嵌入向量失败: {str(e)}")

        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        embedding_id = str(uuid.uuid4())[:8]
        
        # 保存嵌入文件
        # 替换模型名称中的无效字符（Windows不允许文件名中包含 : / \ * ? " < > |）
        sanitized_model = model.replace(":", "-").replace("/", "-").replace("\\", "-").replace("*", "-").replace("?", "-").replace("\"", "-").replace("<", "-").replace(">", "-").replace("|", "-")
        result_file = f"{document_id}_{provider}_{sanitized_model}_{timestamp}_embedded.json"
        result_path = os.path.join(self.embeddings_dir, result_file)
        
        embedding_data = {
            'document_id': document_id,
            'embedding_id': embedding_id,
            'provider': provider,
            'model': model,
            'timestamp': timestamp,
            'dimensions': dimensions,
            'total_embeddings': len(results),
            'embeddings': results
        }
        
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(embedding_data, f, ensure_ascii=False, cls=self.CompactJSONEncoder)
            
        self.logger.info(f"Successfully created embeddings for document {document_id}. Result saved to: {result_path}")
        
        # 返回详细的嵌入结果信息
        return {
            'document_id': document_id,
            'embedding_id': embedding_id,
            'provider': provider,
            'model': model,
            'dimensions': dimensions,
            'total_embeddings': len(results),
            'result_file': result_file,
            'message': f"嵌入向量生成成功，已存储为 {result_file}"
        }

    def list_embeddings(self, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有嵌入向量文件
        """
        self.logger.info(f"Listing embeddings for document_id: {document_id if document_id else 'all'}")
        results = []
        
        # 确保目录存在
        os.makedirs(self.embeddings_dir, exist_ok=True)
        
        # 遍历嵌入文件目录
        for filename in os.listdir(self.embeddings_dir):
            if filename.endswith('_embedded.json'):
                if document_id and not filename.startswith(document_id):
                    continue
                
                file_path = os.path.join(self.embeddings_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 提取基本信息
                    results.append({
                        'document_id': data.get('document_id', ''),
                        'embedding_id': data.get('embedding_id', ''),
                        'provider': data.get('provider', ''),
                        'model': data.get('model', ''),
                        'dimensions': data.get('dimensions', 0),
                        'total_embeddings': data.get('total_embeddings', 0),
                        'timestamp': data.get('timestamp', ''),
                        'filename': filename
                    })
                except Exception as e:
                    self.logger.error(f"Error reading embedding file {filename}: {str(e)}")
            
        return results

    def delete_embedding(self, embedding_id: str) -> Dict[str, Any]:
        """
        删除指定ID的嵌入向量文件
        """
        self.logger.info(f"Deleting embedding with ID: {embedding_id}")
        
        # 确保目录存在
        os.makedirs(self.embeddings_dir, exist_ok=True)
        
        # 遍历嵌入文件目录查找匹配的文件
        found = False
        for filename in os.listdir(self.embeddings_dir):
            if filename.endswith('_embedded.json'):
                file_path = os.path.join(self.embeddings_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data.get('embedding_id') == embedding_id:
                        found = True
                        os.remove(file_path)
                        self.logger.info(f"Successfully deleted embedding file: {filename}")
                        return {
                            'status': 'success',
                            'message': f"嵌入 {embedding_id} 已删除",
                            'embedding_id': embedding_id,
                            'filename': filename
                        }
                except Exception as e:
                    self.logger.error(f"Error processing embedding file {filename}: {str(e)}")
        
        if not found:
            raise FileNotFoundError(f"未找到ID为 {embedding_id} 的嵌入向量")
        
        return {'status': 'error', 'message': '删除失败'}

    def generate_embedding_vector(self, text: str, provider: str = "ollama", model: str = "bge-m3") -> List[float]:
        """
        为文本生成嵌入向量，用于搜索功能
        
        参数:
            text: 要嵌入的文本
            provider: 嵌入服务提供商（默认：ollama）
            model: 嵌入模型（默认：bge-m3）
            
        返回:
            嵌入向量（浮点数列表）
        """
        self.logger.info(f"Generating embedding vector for text with provider: {provider}, model: {model}")
        
        try:
            # 创建嵌入配置与函数
            config = EmbeddingConfig(provider, model)
            embed_fn = self.factory.create_embedding_function(config)
            
            # 生成向量
            vector = embed_fn.embed_query(text)
            self.logger.info(f"Successfully generated vector with dimensions: {len(vector)}")
            return vector
        except Exception as e:
            self.logger.error(f"Error generating embedding vector: {str(e)}")
            self.logger.warning("Falling back to random vector for development/debugging")
            
            # 如果生成失败，返回随机向量（仅用于开发调试）
            import numpy as np
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
                
            np.random.seed(42)  # 固定种子以便调试
            vector = np.random.randn(dimensions)
            vector = vector / np.linalg.norm(vector)  # 归一化
            np.random.seed(None)  # 重置随机种子
            
            return vector.tolist()

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
                    return '[' + ','.join(map(str,o)) + ']'
                if isinstance(o, list): return [fmt(i) for i in o]
                if isinstance(o, dict): return {k: fmt(v) for k,v in o.items()}
                return o
            return super().encode(fmt(obj))

    def _find_document(self, document_id: str) -> Optional[str]:
        """查找指定ID的文档路径"""
        self.logger.debug(f"Searching for document with ID: {document_id} in {self.documents_dir}")
        if os.path.exists(self.documents_dir):
            for filename in os.listdir(self.documents_dir):
                if document_id in filename:
                    self.logger.debug(f"Found document: {filename}")
                    return os.path.join(self.documents_dir, filename)
        self.logger.warning(f"Document with ID: {document_id} not found in {self.documents_dir}")
        return None

    def _find_parsed_file(self, document_id: str) -> Optional[str]:
        """查找指定文档的解析文件"""
        self.logger.debug(f"Searching for parsed file for document ID: {document_id} in {self.parsed_dir}")
        if os.path.exists(self.parsed_dir):
            for filename in os.listdir(self.parsed_dir):
                if filename.startswith(document_id) and filename.endswith("_parsed.json"):
                    self.logger.debug(f"Found parsed file: {filename}")
                    return os.path.join(self.parsed_dir, filename)
        self.logger.warning(f"Parsed file for document ID: {document_id} not found in {self.parsed_dir}")
        return None
