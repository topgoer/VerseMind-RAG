"""
对话服务：支持异步流式对话，包括多轮对话和会话管理
基于您提供的DeepSeek API示例实现
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    """异步对话服务，支持多轮对话和会话管理"""

    def __init__(self, storage_dir="storage/conversations"):
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)

        # API配置
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

        logger.info(f"ConversationService initialized with storage: {self.storage_dir}")

    async def start_conversation(self, system_prompt: Optional[str] = None) -> str:
        """开始新的对话会话"""
        conversation_id = str(uuid.uuid4())

        conversation_data = {
            "conversation_id": conversation_id,
            "created_at": datetime.now().isoformat(),
            "system_prompt": system_prompt or "You are a helpful assistant.",
            "messages": [],
            "total_tokens": 0,
            "last_updated": datetime.now().isoformat()
        }

        await self._save_conversation(conversation_id, conversation_data)
        logger.info(f"Started new conversation: {conversation_id}")
        return conversation_id

    async def add_message(self, conversation_id: str, role: str, content: str) -> Dict[str, Any]:
        """向对话添加消息"""
        conversation = await self._load_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "tokens": len(content.split())  # 简单的token估算
        }

        conversation["messages"].append(message)
        conversation["total_tokens"] += message["tokens"]
        conversation["last_updated"] = datetime.now().isoformat()

        await self._save_conversation(conversation_id, conversation)
        return message

    async def chat_stream(
        self,
        conversation_id: str,
        user_message: str,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """异步流式对话"""
        try:
            # 加载对话历史
            conversation = await self._load_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")

            # 添加用户消息
            await self.add_message(conversation_id, "user", user_message)

            # 构建消息历史
            messages = self._build_message_history(conversation)

            # 流式生成响应
            response_content = ""
            async for chunk in self._stream_chat(provider, model, messages, temperature, max_tokens):
                response_content += chunk
                yield chunk

            # 保存AI响应
            if response_content:
                await self.add_message(conversation_id, "assistant", response_content)
                logger.info(f"Conversation {conversation_id}: Generated {len(response_content)} characters")

        except Exception as e:
            error_message = f"Error in chat_stream: {str(e)}"
            logger.error(error_message)
            yield f"[ERROR] {error_message}"

    async def chat_sync(
        self,
        conversation_id: str,
        user_message: str,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """同步对话（一次性返回完整响应）"""
        try:
            # 加载对话历史
            conversation = await self._load_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")

            # 添加用户消息
            user_msg = await self.add_message(conversation_id, "user", user_message)

            # 构建消息历史
            messages = self._build_message_history(conversation)

            # 生成响应
            response_content = await self._generate_chat_response(
                provider, model, messages, temperature, max_tokens
            )

            # 保存AI响应
            ai_msg = await self.add_message(conversation_id, "assistant", response_content)

            return {
                "conversation_id": conversation_id,
                "user_message": user_msg,
                "ai_response": ai_msg,
                "total_messages": len(conversation["messages"]) + 2  # +2 for the new messages
            }

        except Exception as e:
            logger.error(f"Error in chat_sync: {str(e)}")
            raise

    async def get_conversation_history(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话历史"""
        conversation = await self._load_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        return conversation

    async def list_conversations(self) -> List[Dict[str, Any]]:
        """列出所有对话"""
        conversations = []
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith(".json"):
                    conversation_id = filename[:-5]  # Remove .json extension
                    conversation = await self._load_conversation(conversation_id)
                    if conversation:
                        # 返回摘要信息
                        summary = {
                            "conversation_id": conversation_id,
                            "created_at": conversation.get("created_at"),
                            "last_updated": conversation.get("last_updated"),
                            "message_count": len(conversation.get("messages", [])),
                            "total_tokens": conversation.get("total_tokens", 0),
                            "preview": self._get_conversation_preview(conversation)
                        }
                        conversations.append(summary)
        except Exception as e:
            logger.error(f"Error listing conversations: {str(e)}")

        # 按最后更新时间排序
        conversations.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return conversations

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        try:
            file_path = os.path.join(self.storage_dir, f"{conversation_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted conversation: {conversation_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        return False

    # Private helper methods

    def _build_message_history(self, conversation: Dict[str, Any]) -> List[Dict[str, str]]:
        """构建用于API的消息历史"""
        messages = [{"role": "system", "content": conversation["system_prompt"]}]

        for msg in conversation["messages"]:
            if msg["role"] in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        return messages

    async def _stream_chat(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int]
    ) -> AsyncGenerator[str, None]:
        """流式生成聊天响应"""
        if provider == "deepseek":
            async for chunk in self._stream_deepseek(messages, model):  # Removed temperature and max_tokens
                yield chunk
        elif provider == "openai":
            async for chunk in self._stream_openai(messages, model, temperature, max_tokens):
                yield chunk
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def _generate_chat_response(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int]
    ) -> str:
        """生成同步聊天响应"""
        if provider == "deepseek":
            return await self._generate_deepseek(messages, model)  # Removed temperature and max_tokens
        elif provider == "openai":
            return await self._generate_openai(messages, model, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def _stream_deepseek(
        self,
        messages: List[Dict[str, str]],
        model: str
        # temperature: float,  # Removed unused parameter
        # max_tokens: Optional[int]  # Removed unused parameter
    ) -> AsyncGenerator[str, None]:
        """DeepSeek流式响应 - 完全按照用户提供的简洁示例"""
        if not self.deepseek_api_key:
            raise ValueError("DeepSeek API key not configured")

        try:
            # 简洁的模型名称映射
            if "deepseek-chat" in model or "deepseek-v3" in model:
                model_name = "deepseek-chat"
            elif "deepseek-reasoner" in model or "deepseek-r1" in model:
                model_name = "deepseek-reasoner"
            else:
                model_name = model

            # 完全按照用户示例的客户端创建
            client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )

            # 完全按照用户示例的流式调用
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"DeepSeek streaming error: {str(e)}")
            yield f"Error: {str(e)}"

    async def _generate_deepseek(
        self,
        messages: List[Dict[str, str]],
        model: str
        # temperature: float,  # Removed unused parameter
        # max_tokens: Optional[int]  # Removed unused parameter
    ) -> str:
        """DeepSeek同步响应 - 完全按照用户提供的简洁示例"""
        if not self.deepseek_api_key:
            raise ValueError("DeepSeek API key not configured")

        try:
            # 简洁的模型名称映射
            if "deepseek-chat" in model or "deepseek-v3" in model:
                model_name = "deepseek-chat"
            elif "deepseek-reasoner" in model or "deepseek-r1" in model:
                model_name = "deepseek-reasoner"
            else:
                model_name = model

            # 完全按照用户示例的客户端创建
            client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )

            # 完全按照用户示例的同步调用
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=False
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DeepSeek generation error: {str(e)}")
            return f"Error: {str(e)}"

    async def _stream_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int]
    ) -> AsyncGenerator[str, None]:
        """OpenAI流式响应"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        try:
            client = OpenAI(api_key=self.openai_api_key)

            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error_msg = f"OpenAI streaming error: {str(e)}"
            logger.error(error_msg)
            yield f"[ERROR] {error_msg}"

    async def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int]
    ) -> str:
        """OpenAI同步响应"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        try:
            client = OpenAI(api_key=self.openai_api_key)

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            raise

    async def _load_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """加载对话数据"""
        try:
            file_path = os.path.join(self.storage_dir, f"{conversation_id}.json")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading conversation {conversation_id}: {str(e)}")
        return None

    async def _save_conversation(self, conversation_id: str, conversation_data: Dict[str, Any]):
        """保存对话数据"""
        try:
            file_path = os.path.join(self.storage_dir, f"{conversation_id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving conversation {conversation_id}: {str(e)}")
            raise

    def _get_conversation_preview(self, conversation: Dict[str, Any]) -> str:
        """获取对话预览"""
        messages = conversation.get("messages", [])
        if not messages:
            return "No messages"

        # 找到第一条用户消息作为预览
        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"][:50]
                return content + "..." if len(msg["content"]) > 50 else content

        return "Empty conversation"


# 全局实例
conversation_service = ConversationService()


# 示例用法和测试函数
async def demo_conversation():
    """演示对话功能"""
    print("=== DeepSeek异步对话演示 ===")

    try:
        # 1. 开始新对话
        conv_id = await conversation_service.start_conversation(
            "You are a helpful AI assistant specializing in programming and technology."
        )
        print(f"Started conversation: {conv_id}")

        # 2. 流式对话
        print("\n--- 流式对话测试 ---")
        user_message = "请解释什么是异步编程"
        print(f"User: {user_message}")
        print("Assistant: ", end="", flush=True)

        async for chunk in conversation_service.chat_stream(
            conv_id, user_message, provider="deepseek", model="deepseek-chat"
        ):
            print(chunk, end="", flush=True)
        print()

        # 3. 同步对话
        print("\n--- 同步对话测试 ---")
        user_message2 = "能举个Python异步编程的简单例子吗？"
        print(f"User: {user_message2}")

        result = await conversation_service.chat_sync(
            conv_id, user_message2, provider="deepseek", model="deepseek-chat"
        )
        print(f"Assistant: {result['ai_response']['content']}")

        # 4. 获取对话历史
        print("\n--- 对话历史 ---")
        history = await conversation_service.get_conversation_history(conv_id)
        print(f"Total messages: {len(history['messages'])}")
        print(f"Total tokens: {history['total_tokens']}")

        # 5. 列出所有对话
        print("\n--- 对话列表 ---")
        conversations = await conversation_service.list_conversations()
        for conv in conversations:
            print(f"ID: {conv['conversation_id'][:8]}... - {conv['preview']}")

    except Exception as e:
        print(f"Demo error: {str(e)}")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_conversation())
