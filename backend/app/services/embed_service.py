import os
import json
import datetime
import uuid
import numpy as np
from typing import Dict, List, Any, Optional
import requests

class EmbedService:
    """向量嵌入服务，支持使用Ollama、OpenAI、HuggingFace模型"""
    
    def __init__(self, chunks_dir="storage/chunks", embeddings_dir="storage/embeddings"):
        self.chunks_dir = chunks_dir
        self.embeddings_dir = embeddings_dir
        os.makedirs(embeddings_dir, exist_ok=True)
    
    def create_embeddings(self, document_id: str, provider: str, model: str) -> Dict[str, Any]:
        """
        将文本块转换为向量表示
        
        参数:
            document_id: 文档ID
            provider: 提供商 ("ollama", "openai", "deepseek")
            model: 模型名称
        
        返回:
            包含嵌入结果的字典
        """
        # 检查解析结果是否存在
        parsed_file = self._find_parsed_file(document_id)
        if not parsed_file:
            raise FileNotFoundError(f"请先对文档ID {document_id} 进行解析处理")
        
        # 读取解析数据
        with open(parsed_file, "r", encoding="utf-8") as f:
            parsed_data = json.load(f)
        
        # 提取段落文本
        paragraphs = self._extract_paragraphs(parsed_data)
        
        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        embedding_id = str(uuid.uuid4())[:8]
        
        # 根据提供商和模型生成嵌入
        embeddings = []
        
        for i, paragraph in enumerate(paragraphs):
            # 生成嵌入向量
            try:
                vector = self._generate_embedding(paragraph["text"], provider, model)
                
                embeddings.append({
                    "id": f"{embedding_id}_{i}",
                    "text_id": paragraph["id"],
                    "text": paragraph["text"],
                    "vector": vector,
                    "dimensions": len(vector)
                })
            except Exception as e:
                print(f"为段落 {paragraph['id']} 生成嵌入时出错: {str(e)}")
        
        # 确保所有嵌入具有相同的维度
        dimensions = len(embeddings[0]["vector"]) if embeddings else 0
        
        # 保存嵌入结果
        result_file = f"{document_id}_{timestamp}_{provider}_{model}_embeddings.json"
        result_path = os.path.join(self.embeddings_dir, result_file)
        
        embedding_result = {
            "document_id": document_id,
            "embedding_id": embedding_id,
            "timestamp": timestamp,
            "provider": provider,
            "model": model,
            "dimensions": dimensions,
            "total_embeddings": len(embeddings),
            "embeddings": embeddings
        }
        
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(embedding_result, f, ensure_ascii=False, indent=2)
        
        # 返回结果时不包含向量数据，以减少响应大小
        result_summary = {
            "document_id": document_id,
            "embedding_id": embedding_id,
            "timestamp": timestamp,
            "provider": provider,
            "model": model,
            "dimensions": dimensions,
            "total_embeddings": len(embeddings),
            "result_file": result_file
        }
        
        return result_summary
    
    def get_embedding_models(self) -> Dict[str, Any]:
        """获取可用的嵌入模型列表"""
        return {
            "providers": {
                "ollama": {
                    "models": [
                        {"id": "bge-large", "dimensions": 1024, "description": "BGE Large 嵌入模型"}
                    ]
                },
                "openai": {
                    "models": [
                        {"id": "text-embedding-3-small", "dimensions": 1536, "description": "OpenAI 小型嵌入模型"},
                        {"id": "text-embedding-3-large", "dimensions": 3072, "description": "OpenAI 大型嵌入模型"}
                    ]
                },
                "deepseek": {
                    "models": [
                        {"id": "deepseek-embed", "dimensions": 1024, "description": "DeepSeek 嵌入模型"}
                    ]
                }
            }
        }
    
    def _find_parsed_file(self, document_id: str) -> Optional[str]:
        """查找指定文档的解析文件"""
        if os.path.exists(self.chunks_dir):
            for filename in os.listdir(self.chunks_dir):
                if filename.startswith(document_id) and filename.endswith("_parsed.json"):
                    return os.path.join(self.chunks_dir, filename)
        return None
    
    def _extract_paragraphs(self, parsed_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """从解析数据中提取所有段落"""
        paragraphs = []
        
        # 提取结构中的段落
        structure = parsed_data.get("structure", {})
        sections = structure.get("sections", [])
        
        for section in sections:
            # 添加章节段落
            for para in section.get("paragraphs", []):
                paragraphs.append({
                    "id": para.get("id", f"p{len(paragraphs)}"),
                    "text": para.get("text", "")
                })
            
            # 添加子章节段落
            for subsection in section.get("subsections", []):
                for para in subsection.get("paragraphs", []):
                    paragraphs.append({
                        "id": para.get("id", f"p{len(paragraphs)}"),
                        "text": para.get("text", "")
                    })
        
        return paragraphs
    
    def _generate_embedding(self, text: str, provider: str, model: str) -> List[float]:
        """
        根据提供商和模型生成文本的嵌入向量
        
        参数:
            text: 要嵌入的文本
            provider: 提供商 ("ollama", "openai", "deepseek")
            model: 模型名称
        
        返回:
            嵌入向量
        """
        if provider == "ollama":
            return self._generate_ollama_embedding(text, model)
        elif provider == "openai":
            return self._generate_openai_embedding(text, model)
        elif provider == "deepseek":
            return self._generate_deepseek_embedding(text, model)
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    def _generate_ollama_embedding(self, text: str, model: str) -> List[float]:
        """使用Ollama生成嵌入"""
        try:
            # 在实际实现中，这里会调用Ollama API
            # 这里使用随机向量模拟
            if model == "bge-large":
                dimensions = 1024
            else:
                dimensions = 768  # 默认维度
            
            # 生成随机向量并归一化
            vector = np.random.randn(dimensions)
            vector = vector / np.linalg.norm(vector)
            
            return vector.tolist()
        except Exception as e:
            raise Exception(f"Ollama嵌入生成失败: {str(e)}")
    
    def _generate_openai_embedding(self, text: str, model: str) -> List[float]:
        """使用OpenAI生成嵌入"""
        try:
            # 在实际实现中，这里会调用OpenAI API
            # 这里使用随机向量模拟
            if model == "text-embedding-3-small":
                dimensions = 1536
            elif model == "text-embedding-3-large":
                dimensions = 3072
            else:
                dimensions = 1536  # 默认维度
            
            # 生成随机向量并归一化
            vector = np.random.randn(dimensions)
            vector = vector / np.linalg.norm(vector)
            
            return vector.tolist()
        except Exception as e:
            raise Exception(f"OpenAI嵌入生成失败: {str(e)}")
    
    def _generate_deepseek_embedding(self, text: str, model: str) -> List[float]:
        """使用DeepSeek生成嵌入"""
        try:
            # 在实际实现中，这里会调用DeepSeek API
            # 这里使用随机向量模拟
            dimensions = 1024  # DeepSeek嵌入默认维度
            
            # 生成随机向量并归一化
            vector = np.random.randn(dimensions)
            vector = vector / np.linalg.norm(vector)
            
            return vector.tolist()
        except Exception as e:
            raise Exception(f"DeepSeek嵌入生成失败: {str(e)}")
