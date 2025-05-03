import os
import json
import datetime
import uuid
import requests
import logging
import asyncio
import toml
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.api.config import get_config_path

logger = logging.getLogger(__name__)

class GenerateService:
    """文本生成服务，支持基于检索结果的生成"""
    
    def __init__(self, results_dir="storage/results"):
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.deepseek_api_base = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        # 只读取一次 config.toml，使用 config.py 的 get_config_path
        config_path = get_config_path()
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = toml.load(f)

    def _get_max_tokens_from_config(self, model_name: str) -> int:
        llm_config = self.config.get("llm", {})
        # 优先查找所有 [llm.xxx] 区块
        for section_key, section_cfg in llm_config.items():
            if isinstance(section_cfg, dict):
                if section_cfg.get("model", "").replace(" ", "").replace(":", "").lower() == model_name.replace(" ", "").replace(":", "").lower():
                    if "max_tokens" in section_cfg:
                        return int(section_cfg["max_tokens"])
        # 查全局 [llm] 区块
        if isinstance(llm_config, dict) and llm_config.get("model", "").replace(" ", "").replace(":", "").lower() == model_name.replace(" ", "").replace(":", "").lower():
            if "max_tokens" in llm_config:
                return int(llm_config["max_tokens"])
        # fallback: 取全局 [llm] 的 max_tokens
        if isinstance(llm_config, dict) and "max_tokens" in llm_config:
            return int(llm_config["max_tokens"])
        # 最后兜底 1024
        return 1024

    def generate_text(self, search_id: Optional[str], prompt: str, provider: str, model: str, 
                     temperature: float = 0.7, max_tokens: int = None) -> Dict[str, Any]:
        """
        基于检索结果生成文本
        
        参数:
            search_id: 搜索结果ID（可选）
            prompt: 提示文本
            provider: 提供商 ("ollama", "openai", "deepseek")
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成令牌数
        
        返回:
            包含生成结果的字典
        """
        # 获取搜索结果（如果提供了search_id）
        search_results = []
        search_data = None
        
        if search_id:
            search_file = self._find_search_file(search_id)
            if not search_file:
                raise FileNotFoundError(f"找不到ID为{search_id}的搜索结果")
            
            # 读取搜索结果
            with open(search_file, "r", encoding="utf-8") as f:
                search_data = json.load(f)
                search_results = search_data.get("results", [])
        
        # 构建上下文
        context = ""
        if search_results:
            context = "基于以下检索结果：\n\n"
            for i, result in enumerate(search_results):
                context += f"[{i+1}] {result.get('text', '')}\n\n"
        
        # 构建完整提示
        full_prompt = context + prompt if context else prompt
        
        # 强制只用 config 文件的 max_tokens
        max_tokens = self._get_max_tokens_from_config(model)
        generated_text = self._generate_text_with_model(full_prompt, provider, model, temperature, max_tokens)
        
        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        generation_id = str(uuid.uuid4())[:8]
        
        # 构建生成结果
        result = {
            "generation_id": generation_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "search_id": search_id,
            "generated_text": generated_text
        }
        
        # 保存生成结果
        result_file = f"generation_{generation_id}_{timestamp}.json"
        result_path = os.path.join(self.results_dir, result_file)
        
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 返回结果
        result["result_file"] = result_file
        return result
    
    def get_generation_models(self) -> Dict[str, Any]:
        # 直接使用 self.config
        return {"model_groups": self.config.get("model_groups", {})}
    
    def _find_search_file(self, search_id: str) -> Optional[str]:
        """查找指定ID的搜索结果文件"""
        if os.path.exists(self.results_dir):
            for filename in os.listdir(self.results_dir):
                if search_id in filename and filename.startswith("search_") and filename.endswith(".json"):
                    return os.path.join(self.results_dir, filename)
        return None
    
    def _generate_text_with_model(self, prompt: str, provider: str, model: str, temperature: float, max_tokens: int) -> str:
        """使用指定模型生成文本"""
        if provider == "ollama":
            return self._generate_with_ollama(prompt, model, temperature, max_tokens)
        elif provider == "openai":
            return self._generate_with_openai(prompt, model, temperature, max_tokens)
        elif provider == "deepseek":
            return self._generate_with_deepseek(prompt, model, temperature, max_tokens)
        elif provider == "siliconflow":
            return self._generate_with_deepseek(prompt, model, temperature, max_tokens)            
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    def _generate_with_ollama(self, prompt: str, model: str, temperature: float, max_tokens: int) -> str:
        """使用Ollama生成文本"""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API错误: {response.status_code} - {response.text}")
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Ollama生成错误: {str(e)}")
            raise
    
    def _generate_with_openai(self, prompt: str, model: str, temperature: float, max_tokens: int) -> str:
        """使用OpenAI生成文本"""
        if not self.openai_api_key:
            raise ValueError("未设置OpenAI API密钥")
            
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个有用的AI助手。基于提供的信息回答问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI生成错误: {str(e)}")
            raise
    
    def _generate_with_deepseek(self, prompt: str, model: str, temperature: float, max_tokens: int) -> str:
        """使用DeepSeek生成文本"""
        if not self.deepseek_api_key:
            raise ValueError("未设置DeepSeek API密钥 (DEEPSEEK_API_KEY)")
            
        try:
            # 使用OpenAI风格的客户端访问DeepSeek API
            from openai import OpenAI
            
            # 确定正确的模型名称
            if "deepseek-chat" in model or "deepseek-v3" in model:
                model_name = "deepseek-chat"
            elif "deepseek-reasoner" in model or "deepseek-r1" in model:
                model_name = "deepseek-reasoner"
            else:
                model_name = model
            
            # 创建客户端连接
            client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url=self.deepseek_api_base
            )
            
            # 调用API生成文本
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"DeepSeek生成错误: {str(e)}")
            raise
    
    async def generate_text_stream(self, search_id: Optional[str], prompt: str, provider: str, model: str,
                           temperature: float = 0.7, max_tokens: int = None):
        """
        流式生成文本
        
        参数:
            search_id: 搜索结果ID（可选）
            prompt: 提示文本
            provider: 提供商 ("ollama", "openai", "deepseek")
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成令牌数
        
        返回:
            生成的文本流
        """
        # 获取搜索结果（如果提供了search_id）
        search_results = []
        
        if search_id:
            search_file = self._find_search_file(search_id)
            if not search_file:
                raise FileNotFoundError(f"找不到ID为{search_id}的搜索结果")
            
            # 读取搜索结果
            with open(search_file, "r", encoding="utf-8") as f:
                search_data = json.load(f)
                search_results = search_data.get("results", [])
        
        # 构建上下文
        context = ""
        if search_results:
            context = "基于以下检索结果：\n\n"
            for i, result in enumerate(search_results):
                context += f"[{i+1}] {result.get('text', '')}\n\n"
        
        # 构建完整提示
        full_prompt = context + prompt if context else prompt
        
        # 根据提供商选择不同的流式生成方法
        if max_tokens is None:
            max_tokens = self._get_max_tokens_from_config(model)
        if provider == "deepseek":
            async for text_chunk in self._stream_with_deepseek(full_prompt, model, temperature, max_tokens):
                yield text_chunk
        elif provider == "openai":
            async for text_chunk in self._stream_with_openai(full_prompt, model, temperature, max_tokens):
                yield text_chunk
        elif provider == "ollama":
            async for text_chunk in self._stream_with_ollama(full_prompt, model, temperature, max_tokens):
                yield text_chunk
        elif provider == "siliconflow":
            async for text_chunk in self._stream_with_ollama(full_prompt, model, temperature, max_tokens):
                yield text_chunk                
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    async def _stream_with_deepseek(self, prompt: str, model: str, temperature: float, max_tokens: int):
        """使用DeepSeek流式生成文本"""
        if not self.deepseek_api_key:
            raise ValueError("未设置DeepSeek API密钥 (DEEPSEEK_API_KEY)")
            
        try:
            from openai import OpenAI
            
            # 确定正确的模型名称
            if "deepseek-chat" in model or "deepseek-v3" in model:
                model_name = "deepseek-chat"
            elif "deepseek-reasoner" in model or "deepseek-r1" in model:
                model_name = "deepseek-reasoner"
            else:
                model_name = model
            
            # 创建客户端连接
            client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url=self.deepseek_api_base
            )
            
            # 调用API流式生成文本
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"DeepSeek流式生成错误: {str(e)}")
            yield f"错误: {str(e)}"
    
    async def _stream_with_openai(self, prompt: str, model: str, temperature: float, max_tokens: int):
        """使用OpenAI流式生成文本"""
        if not self.openai_api_key:
            raise ValueError("未设置OpenAI API密钥")
            
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个有用的AI助手。基于提供的信息回答问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI流式生成错误: {str(e)}")
            yield f"错误: {str(e)}"
    
    async def _stream_with_ollama(self, prompt: str, model: str, temperature: float, max_tokens: int):
        """使用Ollama流式生成文本"""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            async def fetch_stream():
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.ollama_base_url}/api/generate",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=300)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"Ollama API错误: {response.status} - {error_text}")
                        
                        async for line in response.content:
                            if line:
                                try:
                                    data = json.loads(line)
                                    if "response" in data:
                                        yield data["response"]
                                except json.JSONDecodeError:
                                    logger.error(f"无法解析JSON: {line}")
            
            async for chunk in fetch_stream():
                yield chunk
                
        except Exception as e:
            logger.error(f"Ollama流式生成错误: {str(e)}")
            yield f"错误: {str(e)}"
