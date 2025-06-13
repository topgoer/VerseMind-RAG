"""
对话API端点：支持异步流式对话和会话管理
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)
router = APIRouter()
# 创建对话服务实例
conversation_service = ConversationService()


@router.post("/start")
async def start_conversation(
    system_prompt: Optional[str] = Body(None, description="系统提示词")
):
    """开始新的对话会话"""
    try:
        conversation_id = await conversation_service.start_conversation(system_prompt)
        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": "Conversation started successfully"
        }
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream/{conversation_id}")
async def chat_stream(
    conversation_id: str,
    message: str = Body(..., description="用户消息"),
    provider: str = Body("deepseek", description="AI提供商"),
    model: str = Body("deepseek-chat", description="模型名称"),
    temperature: float = Body(0.7, description="温度参数"),
    max_tokens: Optional[int] = Body(None, description="最大令牌数")
):
    """流式对话响应"""
    try:
        async def generate():
            async for chunk in conversation_service.chat_stream(
                conversation_id=conversation_id,
                user_message=message,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                # 发送Server-Sent Events格式的数据
                yield f"data: {chunk}\n\n"

            # 发送结束信号
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat stream: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/sync/{conversation_id}")
async def chat_sync(
    conversation_id: str,
    message: str = Body(..., description="用户消息"),
    provider: str = Body("deepseek", description="AI提供商"),
    model: str = Body("deepseek-chat", description="模型名称"),
    temperature: float = Body(0.7, description="温度参数"),
    max_tokens: Optional[int] = Body(None, description="最大令牌数")
):
    """同步对话响应"""
    try:
        result = await conversation_service.chat_sync(
            conversation_id=conversation_id,
            user_message=message,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """获取对话历史"""
    try:
        history = await conversation_service.get_conversation_history(conversation_id)
        return {
            "success": True,
            "data": history
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_conversations():
    """列出所有对话"""
    try:
        conversations = await conversation_service.list_conversations()
        return {
            "success": True,
            "data": conversations
        }
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    try:
        success = await conversation_service.delete_conversation(conversation_id)
        if success:
            return {
                "success": True,
                "message": "Conversation deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/{conversation_id}")
async def add_message(
    conversation_id: str,
    role: str = Body(..., description="消息角色: user, assistant, system"),
    content: str = Body(..., description="消息内容")
):
    """向对话添加消息"""
    try:
        message = await conversation_service.add_message(conversation_id, role, content)
        return {
            "success": True,
            "data": message
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 健康检查和测试端点
@router.get("/health")
async def conversation_health():
    """对话服务健康检查"""
    return {
        "status": "healthy",
        "service": "conversation_service",
        "endpoints": [
            "POST /start - 开始对话",
            "POST /chat/stream/{id} - 流式对话",
            "POST /chat/sync/{id} - 同步对话",
            "GET /history/{id} - 获取历史",
            "GET /list - 列出对话",
            "DELETE /{id} - 删除对话",
            "POST /message/{id} - 添加消息"
        ]
    }


@router.post("/test")
async def test_conversation(
    provider: str = Body("deepseek", description="测试的AI提供商"),
    model: str = Body("deepseek-chat", description="测试的模型"),
    message: str = Body("Hello! This is a test message.", description="测试消息")
):
    """测试对话功能"""
    try:
        # 创建测试对话
        conversation_id = await conversation_service.start_conversation(
            "You are a helpful assistant for testing purposes."
        )

        # 发送测试消息
        result = await conversation_service.chat_sync(
            conversation_id=conversation_id,
            user_message=message,
            provider=provider,
            model=model,
            temperature=0.7
        )

        return {
            "success": True,
            "test_result": {
                "conversation_id": conversation_id,
                "user_message": message,
                "ai_response": result["ai_response"]["content"],
                "provider": provider,
                "model": model
            }
        }
    except Exception as e:
        logger.error(f"Error in test conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
