import os
import json
import datetime
import uuid
import requests
import toml
from typing import Dict, Any, Optional
from app.api.config import get_config_path
from app.core.logger import get_logger_with_env_level

# Import MCP server related functions
try:
    from app.mcp.mcp_server_manager import set_versemind_data

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Initialize logger using the environment-based configuration
logger = get_logger_with_env_level(__name__)


class GenerateService:
    """文本生成服务，支持基于检索结果的生成"""

    def __init__(self, results_dir=os.path.join("storage", "results")):
        # 使用绝对路径，与SearchService保持一致
        self.storage_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../..")
        )
        self.results_dir = os.path.join(self.storage_dir, results_dir)
        os.makedirs(self.results_dir, exist_ok=True)
        # 添加日志
        logger.debug(
            f"GenerateService initialized with results_dir: {self.results_dir}"
        )
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.deepseek_api_base = os.environ.get(
            "DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"
        )
        self.ollama_base_url = os.environ.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        logger.debug(f"Loaded OLLAMA_BASE_URL: '{self.ollama_base_url}'")
        # 只读取一次 config.toml，使用 config.py 的 get_config_path
        config_path = get_config_path()
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = toml.load(f)

    def _check_supports_vision(self, model: str) -> bool:
        """检查模型是否支持视觉功能（根据config.toml中的配置）"""
        logger.debug(f"Checking vision support for model: {model}")
        return self._get_model_config_property(model, "supports_vision", False)

    def _get_model_config_property(
        self, model: str, property_name: str, default_value: Any = None
    ) -> Any:
        """从配置中获取指定模型的特定属性值"""
        model_config = self._find_model_config(model)
        if model_config:
            return model_config.get(property_name, default_value)
        logger.debug(
            f"No configuration found for model {model}, using default value for {property_name}"
        )
        return default_value

    def _find_model_config(self, model: str) -> Optional[Dict[str, Any]]:
        """查找指定模型的配置信息"""
        # Try to find model in main llm section
        config_from_main = self._check_main_llm_section(model)
        if config_from_main:
            return config_from_main

        # Try to find model in nested sections
        config_from_nested = self._check_nested_llm_sections(model)
        if config_from_nested:
            return config_from_nested

        # Try to find model in old-style top-level sections
        config_from_oldstyle = self._check_oldstyle_sections(model)
        if config_from_oldstyle:
            return config_from_oldstyle

        logger.debug(f"No configuration found for model {model}")
        return None

    def _check_main_llm_section(self, model: str) -> Optional[Dict[str, Any]]:
        """检查主要的llm部分是否匹配模型"""
        if "llm" in self.config and isinstance(self.config["llm"], dict):
            llm_section = self.config["llm"]
            if llm_section.get("model") == model:
                logger.debug(f"Model {model} found in main llm section")
                return llm_section
        return None

    def _check_nested_llm_sections(self, model: str) -> Optional[Dict[str, Any]]:
        """检查llm内的嵌套部分"""
        if "llm" not in self.config or not isinstance(self.config["llm"], dict):
            return None

        llm_section = self.config["llm"]
        for subsection_key, subsection_cfg in llm_section.items():
            if not isinstance(subsection_cfg, dict):
                continue

            config_model = subsection_cfg.get("model")
            logger.debug(
                f"Checking config subsection: llm.{subsection_key}, model: {config_model}"
            )

            if config_model == model:
                logger.debug(f"Model {model} found in section llm.{subsection_key}")
                return subsection_cfg
        return None

    def _check_oldstyle_sections(self, model: str) -> Optional[Dict[str, Any]]:
        """检查旧格式的顶级部分（向后兼容）"""
        for section_key, section_cfg in self.config.items():
            if not section_key.startswith("llm.") or not isinstance(section_cfg, dict):
                continue

            config_model = section_cfg.get("model")
            print(
                f"[DEBUG] Checking config section: {section_key}, model: {config_model}"
            )

            if config_model == model:
                print(f"[DEBUG] Model {model} found in section {section_key}")
                return section_cfg
        return None

    def _normalize_model_name(self, model_name: str) -> str:
        """标准化模型名称以进行比较"""
        return model_name.replace(" ", "").replace(":", "").lower()

    def _get_max_tokens_from_config(self, model_name: str) -> int:
        """从配置中获取最大token数量"""
        llm_config = self.config.get("llm", {})
        normalized_model_name = self._normalize_model_name(model_name)

        # 优先查找所有 [llm.xxx] 区块
        for section_cfg in llm_config.values():
            if not isinstance(section_cfg, dict):
                continue

            config_model = section_cfg.get("model", "")
            if self._normalize_model_name(config_model) == normalized_model_name:
                if "max_tokens" in section_cfg:
                    return int(section_cfg["max_tokens"])

        # 查全局 [llm] 区块
        global_model = llm_config.get("model", "")
        if (
            isinstance(llm_config, dict)
            and self._normalize_model_name(global_model) == normalized_model_name
            and "max_tokens" in llm_config
        ):
            return int(llm_config["max_tokens"])

        # fallback: 取全局 [llm] 的 max_tokens
        if isinstance(llm_config, dict) and "max_tokens" in llm_config:
            return int(llm_config["max_tokens"])

        # 最后兜底 1024
        return 1024

    def generate_text(
        self,
        search_id: Optional[str],
        prompt: str,
        provider: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        image_data: Optional[str] = None,
        document_data: Optional[str] = None,
        document_text: Optional[str] = None,
        document_type: Optional[str] = None,
        document_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        基于检索结果生成文本

        参数:
            search_id: 搜索结果ID（可选）
            prompt: 提示文本
            provider: 提供商 ("ollama", "openai", "deepseek")
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            image_data: base64编码的图片数据（可选）
            document_data: base64编码的文档数据（可选，如PDF）
            document_text: 文档文本内容（可选，如TXT/MD）
            document_type: 文档类型（可选）
            document_name: 文档名称（可选）

        返回:
            包含生成结果的字典
        """
        # 检查是否有直接文档输入
        if document_data or document_text:
            return self._handle_direct_document_generation(
                prompt,
                provider,
                model,
                temperature,
                max_tokens,
                image_data,
                document_data,
                document_text,
                document_type,
                document_name,
            )

        # 处理基于搜索结果的生成
        return self._handle_search_based_generation(
            search_id, prompt, provider, model, temperature, max_tokens, image_data
        )

    def _handle_direct_document_generation(
        self,
        prompt: str,
        provider: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        image_data: Optional[str],
        document_data: Optional[str],
        document_text: Optional[str],
        document_type: Optional[str],
        document_name: Optional[str],
    ) -> Dict[str, Any]:
        """处理直接文档输入的生成（绕过索引搜索）"""
        logger.debug(
            f"Processing direct document input: type={document_type}, name={document_name}"
        )

        # 构建文档上下文
        document_context = self._build_document_context(
            document_data, document_text, document_type, document_name
        )

        # 生成文本
        full_prompt = document_context + prompt
        effective_max_tokens = self._get_effective_max_tokens(model, max_tokens)
        generated_text = self._generate_text_with_model(
            full_prompt, provider, model, temperature, effective_max_tokens, image_data
        )

        # 创建并保存结果
        result = self._create_generation_result(
            prompt,
            provider,
            model,
            temperature,
            effective_max_tokens,
            None,
            generated_text,  # search_id is None for direct document
        )
        self._save_generation_result(result)
        return result

    def _handle_search_based_generation(
        self,
        search_id: Optional[str],
        prompt: str,
        provider: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        image_data: Optional[str],
    ) -> Dict[str, Any]:
        """处理基于搜索结果的生成"""
        # 获取搜索结果和上下文
        search_data, search_results = self._get_search_results(search_id)
        context = self._build_context(search_results, search_id, search_data)

        # 生成文本
        full_prompt = context + prompt if context else prompt
        effective_max_tokens = self._get_effective_max_tokens(model, max_tokens)
        generated_text = self._generate_text_with_model(
            full_prompt, provider, model, temperature, effective_max_tokens, image_data
        )

        # 创建并保存结果
        result = self._create_generation_result(
            prompt,
            provider,
            model,
            temperature,
            effective_max_tokens,
            search_id,
            generated_text,
        )
        self._save_generation_result(result)  # 更新VerseMind数据（如果可用）
        if MCP_AVAILABLE:
            self._update_mcp_data(
                prompt, generated_text, context, search_id, search_data
            )

        return result

    def _build_document_context(
        self,
        document_data: Optional[str],
        document_text: Optional[str],
        document_type: Optional[str],
        document_name: Optional[str],
    ) -> str:
        """构建文档上下文字符串"""
        document_context = ""

        # 添加文档元信息
        if document_name:
            document_context += f"文档名称: {document_name}\n"
        if document_type:
            document_context += f"文档类型: {document_type}\n"

        # 处理文档内容
        if document_text:
            # 直接提供的文本内容
            document_context += f"文档内容:\n{document_text}\n\n"
        elif document_data:
            # 根据文档类型处理base64编码的数据
            if document_type == "pdf":
                document_context += self._extract_pdf_content(document_data)
            elif document_type in ["text", "txt", "markdown", "md"]:
                document_context += self._extract_text_content(
                    document_data, document_type
                )
            else:
                # 未知文档类型，尝试作为文本处理
                logger.warning(
                    f"Unknown document type: {document_type}, treating as text"
                )
                document_context += self._extract_text_content(document_data, "text")
        return document_context

    def _extract_pdf_content(self, document_data: str) -> str:
        """提取PDF文档内容"""
        try:
            logger.info(
                f"Starting PDF content extraction, data length: {len(document_data)} chars"
            )
            extracted_text = self._extract_pdf_text_from_base64(document_data)
            logger.info(
                f"PDF extraction completed, extracted text length: {len(extracted_text)} chars"
            )
            if extracted_text.strip():
                logger.info(
                    "PDF content extracted successfully, returning formatted content"
                )
                return f"PDF文档内容:\n{extracted_text}\n\n"
            else:
                logger.warning("PDF content extraction returned empty text")
                return "PDF文档已上传，但无法提取文本内容。\n\n"
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {str(e)}")
            return "PDF文档已上传，但文本提取失败。\n\n"

    def _extract_text_content(self, document_data: str, document_type: str) -> str:
        """提取文本或Markdown文档内容"""
        try:
            import base64

            logger.info(
                f"Starting {document_type} content extraction, data length: {len(document_data)} chars"
            )

            # 解码base64数据
            text_bytes = base64.b64decode(document_data)

            # 尝试多种编码方式解码文本
            for encoding in ["utf-8", "gbk", "gb2312", "big5", "latin-1"]:
                try:
                    extracted_text = text_bytes.decode(encoding)
                    logger.info(
                        f"Successfully decoded {document_type} content using {encoding}"
                    )
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # 如果所有编码都失败，使用utf-8并忽略错误
                extracted_text = text_bytes.decode("utf-8", errors="ignore")
                logger.warning(
                    f"Used utf-8 with error ignoring for {document_type} content"
                )

            logger.info(
                f"{document_type.upper()} extraction completed, extracted text length: {len(extracted_text)} chars"
            )

            if extracted_text.strip():
                logger.info(f"{document_type.upper()} content extracted successfully")

                # 根据文档类型添加适当的标签
                if document_type.lower() in ["markdown", "md"]:
                    return f"Markdown文档内容:\n{extracted_text}\n\n"
                else:
                    return f"文本文档内容:\n{extracted_text}\n\n"
            else:
                logger.warning(
                    f"{document_type.upper()} content extraction returned empty text"
                )
                return f"{document_type.upper()}文档已上传，但内容为空。\n\n"

        except Exception as e:
            logger.error(f"Failed to extract {document_type} text: {str(e)}")
            return f"{document_type.upper()}文档已上传，但文本提取失败: {str(e)}\n\n"

    def _get_search_results(
        self, search_id: Optional[str]
    ) -> tuple[Optional[dict], list]:
        """获取搜索结果数据"""
        search_results = []
        search_data = None

        if not search_id:
            return search_data, search_results

        search_file = self._find_search_file(search_id)
        if not search_file:
            raise FileNotFoundError(f"找不到ID为{search_id}的搜索结果")

        try:
            with open(search_file, "r", encoding="utf-8") as f:
                search_data = json.load(f)
                search_results = search_data.get("results", [])

            logger.debug(
                f"Loaded search results from {search_file}: found {len(search_results)} results"
            )

            if not search_results:
                query = search_data.get("query", "")
                document_filename = search_data.get("document_filename", "")
                logger.warning(
                    f"Search ID {search_id} has no results. Query: '{query}', Document: '{document_filename}'"
                )
        except Exception as e:
            logger.error(f"Error loading search results from {search_file}: {str(e)}")
            raise ValueError(f"加载搜索结果失败: {str(e)}")

        return search_data, search_results

    def _build_context(
        self,
        search_results: list,
        search_id: Optional[str],
        search_data: Optional[dict],
    ) -> str:
        """构建生成上下文"""
        context = ""
        if search_results:
            context = "基于以下检索结果：\n\n"
            for i, result in enumerate(search_results):
                context += f"[{i + 1}] {result.get('text', '')}\n\n"
        elif search_id and search_data:
            # 如果有search_id但没有搜索结果，添加有关文档的信息
            document_id = search_data.get("document_id", "")
            document_filename = search_data.get("document_filename", "")
            query = search_data.get("query", "")
            similarity_threshold = search_data.get("similarity_threshold", 0.5)

            context = f"查询未找到达到相似度阈值 ({similarity_threshold}) 的结果。\n"
            if document_filename:
                context += f"已搜索的文档: {document_filename}\n"
            elif document_id:
                context += f"已搜索的文档ID: {document_id}\n"
            context += f"查询内容: {query}\n\n"

        return context

    def _get_effective_max_tokens(self, model: str, max_tokens: Optional[int]) -> int:
        """获取有效的最大令牌数"""
        config_max_tokens = self._get_max_tokens_from_config(model)
        return max_tokens if max_tokens is not None else config_max_tokens

    def _create_generation_result(
        self,
        prompt: str,
        provider: str,
        model: str,
        temperature: float,
        max_tokens: int,
        search_id: Optional[str],
        generated_text: str,
    ) -> Dict[str, Any]:
        """创建生成结果字典"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        generation_id = str(uuid.uuid4())[:8]

        result = {
            "generation_id": generation_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "search_id": search_id,
            "generated_text": generated_text,
            "result_file": f"generation_{generation_id}_{timestamp}.json",
        }

        return result

    def _save_generation_result(self, result: Dict[str, Any]) -> None:
        """保存生成结果到文件"""
        result_path = os.path.join(self.results_dir, result["result_file"])

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def _update_mcp_data(
        self,
        prompt: str,
        generated_text: str,
        context: str,
        search_id: Optional[str],
        search_data: Optional[dict],
    ) -> None:
        """更新MCP服务数据"""
        try:
            # 创建简洁的标题
            title = prompt
            if len(title) > 100:
                title = title[:97] + "..."

            # 为MCP服务创建包含上下文和搜索结果的完整参考
            complete_reference = self._build_mcp_reference(
                prompt, generated_text, context, search_id, search_data
            )

            # 调用MCP服务更新数据
            set_versemind_data(title=title, reference=complete_reference)
            logger.debug("VerseMind data updated successfully.")
        except Exception as e:
            logger.error(f"Failed to update VerseMind data: {str(e)}")

    def _build_mcp_reference(
        self,
        prompt: str,
        generated_text: str,
        context: str,
        search_id: Optional[str],
        search_data: Optional[dict],
    ) -> str:
        """构建MCP服务的参考信息"""
        complete_reference = ""

        # 添加文档元数据信息(如果有)
        if search_id and search_data:
            doc_info = self._get_document_info(search_data)
            if doc_info:
                complete_reference += f"## 背景信息\n{' | '.join(doc_info)}\n\n"

        # 添加上下文
        if context:
            complete_reference += f"## 检索上下文\n{context}\n\n"

        # 添加原始提示和生成的回复
        complete_reference += f"## 提示\n{prompt}\n\n"
        complete_reference += f"## 回复\n{generated_text}"

        return complete_reference

    def _get_document_info(self, search_data: dict) -> list:
        """从搜索数据中获取文档信息"""
        doc_info = []
        if search_data.get("document_filename"):
            doc_info.append(f"文档: {search_data.get('document_filename')}")
        if search_data.get("query"):
            doc_info.append(f"查询: {search_data.get('query')}")
        return doc_info

    def get_generation_models(self) -> Dict[str, Any]:
        # 直接使用 self.config
        return {"model_groups": self.config.get("model_groups", {})}

    def _find_search_file(self, search_id: str) -> Optional[str]:
        """查找指定ID的搜索结果文件"""
        logger.debug(
            f"Searching for search result with ID '{search_id}' in directory: {self.results_dir}"
        )

        if os.path.exists(self.results_dir):
            logger.debug(f"Results directory exists: {self.results_dir}")
            for filename in os.listdir(self.results_dir):
                logger.debug(f"Checking file: {filename}")
                if (
                    search_id in filename
                    and filename.startswith("search_")
                    and filename.endswith(".json")
                ):
                    full_path = os.path.join(self.results_dir, filename)
                    logger.debug(f"Match found: {full_path}")
                    return full_path

            logger.warning(
                f"No search result file found for ID '{search_id}' in {self.results_dir}"
            )
        else:
            logger.error(f"Results directory does not exist: {self.results_dir}")

        return None

    def _generate_text_with_model(
        self,
        prompt: str,
        provider: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        image_data: Optional[str] = None,
    ) -> str:
        """使用指定模型生成文本，可选择包含图片数据"""
        if provider == "ollama":
            return self._generate_with_ollama(
                prompt, model, temperature, max_tokens, image_data
            )
        elif provider == "openai":
            return self._generate_with_openai(
                prompt, model, temperature, max_tokens, image_data
            )
        elif provider in ["deepseek", "siliconflow"]:
            return self._generate_with_deepseek(
                prompt, model, temperature, max_tokens, image_data
            )
        else:
            raise ValueError(f"不支持的提供商: {provider}")

    def _generate_with_ollama(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        image_data: Optional[str] = None,
    ) -> str:
        """使用Ollama生成文本，可选择包含图片数据"""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }

            # 从config.toml检查是否支持视觉
            supports_vision = self._check_supports_vision(model)

            # 如果有图片且模型支持视觉功能
            if image_data and supports_vision:
                print(f"[DEBUG] Adding image data to Ollama request for model {model}")
                # 添加图片数据到请求 - Ollama expects raw base64, not data URI format
                payload["images"] = [image_data]

            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                headers=headers,
                json=payload,
                timeout=180,  # 增加超时时间以避免大模型生成超时
            )

            if response.status_code != 200:
                raise ValueError(
                    f"Ollama API错误: {response.status_code} - {response.text}"
                )

            result = response.json()
            return result.get("response", "")

        except Exception as e:
            logger.error(f"Ollama生成错误: {str(e)}")
            raise

    def _generate_with_openai(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        image_data: Optional[str] = None,
    ) -> str:
        """使用OpenAI生成文本，可选择包含图片数据"""
        if not self.openai_api_key:
            raise ValueError("未设置OpenAI API密钥")

        try:
            import openai

            client = openai.OpenAI(api_key=self.openai_api_key)

            messages = [
                {
                    "role": "system",
                    "content": "你是一个有用的AI助手。基于提供的信息回答问题。",
                }
            ]

            # 从config.toml检查是否支持视觉
            supports_vision = self._check_supports_vision(model)

            # 如果有图片且模型支持视觉功能，则构建包含图片的消息
            if image_data and supports_vision:
                # 构建包含文本和图片的内容
                user_message = {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }

                # 添加图片到内容中
                user_message["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    }
                )

                messages.append(user_message)
            else:
                # 没有图片或者模型不支持视觉，使用普通文本消息
                messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI生成错误: {str(e)}")
            raise

    def _generate_with_deepseek(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        image_data: Optional[str] = None,
    ) -> str:
        """使用DeepSeek生成文本，可选择包含图片数据"""
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

            # 从config.toml检查是否支持视觉
            supports_vision = self._check_supports_vision(model)

            # 创建客户端连接
            client = OpenAI(
                api_key=self.deepseek_api_key, base_url=self.deepseek_api_base
            )

            # 如果有图片且模型支持视觉功能，则构建包含图片的消息
            if image_data and supports_vision:
                # 构建包含文本和图片的内容
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                },
                            },
                        ],
                    }
                ]
            else:
                # 没有图片或模型不支持视觉，使用普通文本消息
                messages = [{"role": "user", "content": prompt}]

            # 调用API生成文本
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DeepSeek生成错误: {str(e)}")
            raise

    async def generate_text_stream(
        self,
        search_id: Optional[str],
        prompt: str,
        provider: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = None,
        image_data: Optional[str] = None,
    ):
        """
        流式生成文本

        参数:
            search_id: 搜索结果ID（可选）
            prompt: 提示文本
            provider: 提供商 ("ollama", "openai", "deepseek")
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            image_data: base64编码的图片数据（可选）

        返回:
            生成的文本流
        """
        # 获取和处理搜索结果
        search_data, search_results = await self._get_stream_search_results(search_id)

        # 构建提示上下文和完整提示
        context = self._build_context(search_results, search_id, search_data)
        full_prompt = context + prompt if context else prompt

        # 准备生成参数
        if max_tokens is None:
            max_tokens = self._get_max_tokens_from_config(model)

        # 根据提供商流式生成文本
        async for chunk in self._stream_with_provider(
            provider, full_prompt, model, temperature, max_tokens, image_data
        ):
            yield chunk

    async def _get_stream_search_results(
        self, search_id: Optional[str]
    ) -> tuple[Optional[dict], list]:
        """获取流式生成的搜索结果数据"""
        search_results = []
        search_data = None

        if not search_id:
            return search_data, search_results

        search_file = self._find_search_file(search_id)
        if not search_file:
            raise FileNotFoundError(f"找不到ID为{search_id}的搜索结果")

        try:
            with open(search_file, "r", encoding="utf-8") as f:
                search_data = json.load(f)
                search_results = search_data.get("results", [])

            logger.debug(
                f"Loaded search results for streaming from {search_file}: found {len(search_results)} results"
            )

            # 检查搜索结果是否为空
            if not search_results:
                query = search_data.get("query", "")
                document_filename = search_data.get("document_filename", "")
                logger.warning(
                    f"Stream: Search ID {search_id} has no results. Query: '{query}', Document: '{document_filename}'"
                )
        except Exception as e:
            logger.error(
                f"Error loading search results for streaming from {search_file}: {str(e)}"
            )
            raise ValueError(f"加载搜索结果失败: {str(e)}")

        return search_data, search_results

    async def _stream_with_provider(
        self,
        provider: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        image_data: Optional[str] = None,
    ):
        """基于提供商选择合适的流式生成方法"""
        if provider == "deepseek":
            async for text_chunk in self._stream_with_deepseek(
                prompt, model, temperature, max_tokens, image_data
            ):
                yield text_chunk
        elif provider == "openai":
            async for text_chunk in self._stream_with_openai(
                prompt, model, temperature, max_tokens, image_data
            ):
                yield text_chunk
        elif provider in ["ollama", "siliconflow"]:
            async for text_chunk in self._stream_with_ollama(
                prompt, model, temperature, max_tokens, image_data
            ):
                yield text_chunk
        else:
            raise ValueError(f"不支持的提供商: {provider}")

    async def _stream_with_deepseek(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        image_data: Optional[str] = None,
    ):
        """使用DeepSeek流式生成文本，可选择包含图片数据"""
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

            # 从config.toml检查是否支持视觉
            supports_vision = self._check_supports_vision(model)

            # 创建客户端连接
            client = OpenAI(
                api_key=self.deepseek_api_key, base_url=self.deepseek_api_base
            )

            # 如果有图片且模型支持视觉功能，则构建包含图片的消息
            if image_data and supports_vision:
                # 构建包含文本和图片的内容
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                },
                            },
                        ],
                    }
                ]
            else:
                # 没有图片或模型不支持视觉，使用普通文本消息
                messages = [{"role": "user", "content": prompt}]

            # 调用API流式生成文本
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"DeepSeek流式生成错误: {str(e)}")
            yield f"错误: {str(e)}"

    async def _stream_with_openai(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        image_data: Optional[str] = None,
    ):
        """使用OpenAI流式生成文本，可选择包含图片数据"""
        if not self.openai_api_key:
            raise ValueError("未设置OpenAI API密钥")

        try:
            import openai

            client = openai.OpenAI(api_key=self.openai_api_key)

            messages = [
                {
                    "role": "system",
                    "content": "你是一个有用的AI助手。基于提供的信息回答问题。",
                }
            ]

            # 从config.toml检查是否支持视觉
            supports_vision = self._check_supports_vision(model)

            # 如果有图片且模型支持视觉功能，则构建包含图片的消息
            if image_data and supports_vision:
                # 构建包含文本和图片的内容
                user_message = {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }

                # 添加图片到内容中
                user_message["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    }
                )

                messages.append(user_message)
            else:
                # 没有图片或者模型不支持视觉，使用普通文本消息
                messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI流式生成错误: {str(e)}")
            yield f"错误: {str(e)}"

    async def _stream_with_ollama(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        image_data: Optional[str] = None,
    ):
        """使用Ollama流式生成文本，支持图片数据"""
        try:
            payload = self._prepare_ollama_payload(
                model, prompt, temperature, max_tokens, image_data, stream=True
            )
            async for chunk in self._fetch_ollama_stream(payload):
                yield chunk

        except Exception as e:
            logger.error(f"Ollama流式生成错误: {str(e)}")
            yield f"错误: {str(e)}"

    def _prepare_ollama_payload(
        self,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        image_data: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """准备Ollama API请求的payload"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        # 从config.toml检查是否支持视觉
        supports_vision = self._check_supports_vision(model)

        # 如果有图片且模型支持视觉功能
        if image_data and supports_vision:
            print(f"[DEBUG] Adding image data to Ollama request for model {model}")
            # 添加图片数据到请求 - Ollama expects raw base64, not data URI format
            payload["images"] = [image_data]

        return payload

    async def _fetch_ollama_stream(self, payload: Dict[str, Any]):
        """从Ollama API获取流式响应"""
        import aiohttp

        headers = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.ollama_base_url}/api/generate",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(
                        f"Ollama API错误: {response.status} - {error_text}"
                    )

                async for line in response.content:
                    if line:
                        for response in self._parse_ollama_response(line):
                            yield response

    def _parse_ollama_response(self, line):
        """解析Ollama API响应"""
        try:
            data = json.loads(line)
            if "response" in data:
                yield data["response"]
        except json.JSONDecodeError:
            logger.error(f"无法解析JSON: {line}")

    def _extract_pdf_text_from_base64(self, base64_data: str) -> str:
        """Extract text from base64 encoded PDF data"""
        import base64
        import tempfile
        import fitz  # PyMuPDF
        import os

        try:
            logger.info(
                f"Starting base64 PDF extraction, input data length: {len(base64_data)}"
            )
            # Decode base64 data
            pdf_bytes = base64.b64decode(base64_data)
            logger.info(f"Decoded PDF bytes length: {len(pdf_bytes)}")

            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(pdf_bytes)
                temp_path = temp_file.name

            logger.info(f"Created temporary PDF file: {temp_path}")

            try:
                # Extract text using PyMuPDF
                doc = fitz.open(temp_path)
                text = ""
                page_count = len(doc)
                logger.info(f"PDF has {page_count} pages")

                for page_num in range(page_count):
                    page = doc[page_num]
                    page_text = page.get_text("text")
                    logger.debug(
                        f"Page {page_num + 1} extracted {len(page_text)} characters"
                    )
                    if page_text.strip():
                        text += f"[Page {page_num + 1}]\n{page_text}\n\n"

                doc.close()

                if not text.strip():
                    logger.warning("No text extracted from PDF")
                    return ""

                logger.info(f"Successfully extracted {len(text)} characters from PDF")
                return text

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {temp_path}: {e}")

        except Exception as e:
            logger.error(f"PDF text extraction failed: {str(e)}")
            raise
