"""
LLM Service provides a unified interface for different language model providers.
"""
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator

import httpx
from openai import OpenAI, AsyncOpenAI, OpenAIError # Modified import
# Removed: import openai as openai_module

# Initialize logger
logger = logging.getLogger(__name__)

# Define which models support different capabilities
VISION_MODELS = ["gpt-4-vision-preview", "gpt-4o", "gpt-4o-mini"]

class LLMService:
    """Language Model Service that provides a unified interface for different providers."""

    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, model_type: str = "openai"):
        """Initialize a LLM service for a specific model type.

        Args:
            api_key: API key for the service
            api_base: Base URL for the API
            model_type: Type of model ("openai", "deepseek", "ollama", etc.)
        """
        self.api_key = api_key
        self.api_base = api_base
        self.model_type = model_type.lower()
        self.content_type_json = "application/json"

        self.openai_client: Optional[OpenAI] = None
        self.async_openai_client: Optional[AsyncOpenAI] = None

        logger.info(f"LLMService initializing for model_type: '{self.model_type}'")

        if self.model_type == "openai":
            effective_base_url = self.api_base if self.api_base else None # OpenAI client handles default
            try:
                self.openai_client = OpenAI(
                    api_key=self.api_key,
                    base_url=effective_base_url,
                    http_client=httpx.Client(timeout=60.0) # Pass custom httpx client
                )
                self.async_openai_client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=effective_base_url,
                    http_client=httpx.AsyncClient(timeout=300.0) # Pass custom httpx client
                )
            except OpenAIError as e:
                logger.error(f"Failed to initialize OpenAI clients: {e}")
                # Depending on desired behavior, could re-raise or handle
            except Exception as e: # Catch any other unexpected errors during init
                logger.error(f"Unexpected error initializing OpenAI clients: {e}")


        try:
            self.validate_credentials()
        except ValueError as e:
            logger.warning(f"Credential validation warning for {self.model_type}: {str(e)}")

    def normalize_model_name(self, model: str) -> str:
        """Normalize the model name based on provider-specific rules."""
        if self.model_type == "deepseek":
            if "deepseek-chat" in model or "deepseek-v3" in model:
                return "deepseek-chat"
            elif "deepseek-reasoner" in model or "deepseek-r1" in model:
                return "deepseek-reasoner"
        return model

    def prepare_messages(self, prompt: str, image_data: Optional[str] = None, supports_vision: bool = False) -> List[Dict[str, Any]]:
        """Prepare messages for the LLM based on prompt and optional image data."""
        messages = [
            {"role": "system", "content": "你是一个有用的AI助手。基于提供的信息回答问题。"}
        ]

        # Handle image data if supported
        if image_data and supports_vision and self.model_type == "openai":
            # Build message with text and image
            user_message = {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }

            # Add image to content
            user_message["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
            })

            messages.append(user_message)
        else:
            # Standard text message
            messages.append({"role": "user", "content": prompt})

        return messages

    def validate_credentials(self):
        """Validate API credentials."""
        if self.model_type in ["openai", "deepseek"] and not self.api_key:
            raise ValueError(f"未设置{self.model_type.capitalize()} API密钥")

        if self.model_type == "ollama" and not self.api_base:
            raise ValueError("未设置Ollama API地址")

    # OpenAI specific methods
    def generate_with_openai(self, prompt, model, temperature, max_tokens, image_data=None, supports_vision=False):
        """Generate text using the OpenAI SDK."""
        if not self.openai_client:
            logger.error("OpenAI client not initialized.")
            raise ValueError("OpenAI client not initialized. Ensure model_type is 'openai' and initialization succeeded.")

        messages = self.prepare_messages(prompt, image_data, supports_vision)

        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise ValueError(f"OpenAI API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI generation: {e}")
            raise

    # DeepSeek specific methods
    def generate_with_deepseek(self, prompt, model, temperature=None, max_tokens=None):
        """Generate text using DeepSeek."""
        # DeepSeek doesn't support images
        logger.warning("DeepSeek 模型不支持图片处理，将忽略图片数据")

        headers = {
            "Content-Type": self.content_type_json,
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        # Add temperature if specified
        if temperature is not None:
            payload["temperature"] = temperature

        # Add max_tokens if specified
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        api_endpoint = self.api_base or "https://api.deepseek.com/v1"

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{api_endpoint}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    # Ollama specific methods
    def generate_with_ollama(self, prompt, model, temperature, max_tokens, image_data=None, supports_vision=False):
        """Generate text using Ollama."""
        headers = {"Content-Type": self.content_type_json}

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        if image_data and supports_vision:
            logger.debug(f"Adding image data to Ollama request for model {model}")
            payload["images"] = [image_data]

        response = httpx.post(
            f"{self.api_base}/api/generate",
            headers=headers,
            json=payload,
            timeout=180.0
        )

        if response.status_code != 200:
            raise ValueError(f"Ollama API错误: {response.status_code} - {response.text}")

        result = response.json()
        return result.get("response", "")    # Main generation method
    def generate(self, prompt: str, model: str, temperature: float = 0.7,
                max_tokens: Optional[int] = None, image_data: Optional[str] = None,
                supports_vision: bool = False) -> str:
        """Generate text using the appropriate LLM."""
        try:
            # self.validate_credentials() # Removed: Validation is done in __init__
            normalized_model = self.normalize_model_name(model) # Ensure model name is normalized

            # Use the appropriate generation method
            if self.model_type == "openai":
                return self.generate_with_openai(
                    prompt, normalized_model, temperature, max_tokens, image_data, supports_vision
                )
            elif self.model_type == "deepseek":
                return self.generate_with_deepseek(
                    prompt, normalized_model, temperature, max_tokens
                )
            elif self.model_type == "ollama":
                return self.generate_with_ollama(
                    prompt, normalized_model, temperature, max_tokens, image_data, supports_vision
                )
            else:
                raise ValueError(f"不支持的模型类型: {self.model_type}")
        except Exception as e:
            logger.error(f"{self.model_type}生成错误: {str(e)}")
            raise

    # OpenAI streaming
    async def stream_with_openai(self, prompt, model, temperature, max_tokens, image_data=None, supports_vision=False):
        """Stream text generation using the OpenAI SDK."""
        if not self.async_openai_client:
            logger.error("Async OpenAI client not initialized.")
            # Consider how to handle this error in an async generator
            yield "Error: Async OpenAI client not initialized. Ensure model_type is 'openai' and initialization succeeded."
            return

        messages = self.prepare_messages(prompt, image_data, supports_vision)

        try:
            stream = await self.async_openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except OpenAIError as e:
            logger.error(f"OpenAI API streaming error: {e}")
            yield f"Error: OpenAI API streaming error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI streaming: {e}")
            yield "Error: Unexpected OpenAI streaming error"

    # DeepSeek streaming
    async def stream_with_deepseek(self, prompt, model, temperature=None, max_tokens=None,
                                   image_data=None, supports_vision=False):
        """
        Stream text generation using DeepSeek.

        Parameters image_data and supports_vision are included for API consistency
        with other providers but are not used by DeepSeek.
        """
        # Warn that DeepSeek doesn't support images
        if image_data:
            logger.warning("DeepSeek 模型不支持图片处理，将忽略图片数据")

        headers = {
            "Content-Type": self.content_type_json,
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        # Add temperature if specified
        if temperature is not None:
            payload["temperature"] = temperature

        # Add max_tokens if specified
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        api_endpoint = self.api_base or "https://api.deepseek.com/v1"

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{api_endpoint}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data:"):
                        line = line[5:].strip()

                    if line == "[DONE]":
                        break

                    try:
                        chunk = json.loads(line)
                        content = (chunk.get("choices", [{}])[0]
                                  .get("delta", {})
                                  .get("content"))
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        logger.error(f"解析JSON错误: {line}")

    def _parse_ollama_stream_chunk(self, line: str) -> tuple[Optional[str], bool]:
        """
        Parses a single line from the Ollama stream.
        Returns:
            - content (Optional[str]): The content to yield, if any.
            - is_done (bool): True if the stream is done.
        Raises:
            ValueError: If the line contains an error message from Ollama or is unparseable.
        """
        if not line.strip():
            return None, False

        try:
            chunk = json.loads(line)

            if "error" in chunk:
                error_msg = chunk["error"]
                logger.error(f"Ollama stream error from chunk: {error_msg}")
                raise ValueError(f"Ollama error: {error_msg}")

            content_to_yield = chunk.get("response")
            is_done = chunk.get("done", False)

            return content_to_yield, is_done

        except json.JSONDecodeError as e:
            logger.warning(f"Ollama stream: Failed to decode JSON line: {line}")
            raise ValueError(f"Corrupted data from Ollama stream: {line}") from e

    async def _process_ollama_response_stream(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """
        Processes the Ollama HTTP response stream, parsing lines and yielding content or errors.
        """
        async for line in response.aiter_lines():
            if not line.strip():
                continue
            try:
                content, is_done = self._parse_ollama_stream_chunk(line)

                if content:
                    yield content

                if is_done:
                    logger.info("Ollama stream finished (done flag received).")
                    return
            except ValueError as e:
                # Error already logged by _parse_ollama_stream_chunk
                yield f"Error: {str(e)}"
                return # Stop processing on parsing error

    # Ollama streaming
    async def stream_with_ollama(self, prompt, model, temperature, max_tokens, image_data=None, supports_vision=False):
        """Stream text generation using Ollama with httpx and improved error handling."""
        headers = {"Content-Type": self.content_type_json}

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        if image_data and supports_vision:
            logger.debug(f"Adding image data to Ollama streaming request for model {model}")
            payload["images"] = [image_data]

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/api/generate",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status() # Check for HTTP errors first

                    async for chunk_content in self._process_ollama_response_stream(response):
                        yield chunk_content

        except httpx.HTTPStatusError as e:
            status_code_str = "N/A"
            error_details = str(e) # Default error detail
            if e.response is not None:
                status_code_str = str(e.response.status_code)
                error_details = e.response.text # More specific detail

            logger.error(f"Ollama API HTTP Status error during stream: {status_code_str} - {error_details}")
            yield f"Error: Ollama API error {status_code_str}"
        except httpx.RequestError as e: # Handles connection errors, timeouts, etc.
            logger.error(f"Ollama API Request error during stream: {str(e)}")
            yield "Error: Olloma connection error"
        except Exception as e:
            logger.error(f"Unexpected error in Ollama stream: {str(e)}")
            yield "Error: Unexpected error in Ollama stream"

    # Main streaming method
    async def generate_stream(self, prompt: str, model: str, temperature: float = 0.7,
                             max_tokens: Optional[int] = None, image_data: Optional[str] = None,
                             supports_vision: bool = False) -> AsyncGenerator[str, None]:
        """Stream text generation using the appropriate LLM."""
        try:
            # self.validate_credentials() # Removed: Validation is done in __init__
            normalized_model = self.normalize_model_name(model)

            # Use the appropriate streaming method
            if self.model_type == "openai":
                async for chunk in self.stream_with_openai(
                    prompt, normalized_model, temperature, max_tokens, image_data, supports_vision
                ):
                    yield chunk

            elif self.model_type == "deepseek":
                async for chunk in self.stream_with_deepseek(
                    prompt, normalized_model, temperature, max_tokens, image_data, supports_vision
                ):
                    yield chunk

            elif self.model_type == "ollama":
                async for chunk in self.stream_with_ollama(
                    prompt, normalized_model, temperature, max_tokens, image_data, supports_vision
                ):
                    yield chunk

            else:
                raise ValueError(f"不支持的模型类型: {self.model_type}")

        except Exception as e:
            logger.error(f"{self.model_type}流式生成错误: {str(e)}")
            yield f"错误: {str(e)}"
