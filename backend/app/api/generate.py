from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Dict, List, Optional
import os

from app.services.generate_service import GenerateService

router = APIRouter()
generate_service = GenerateService()

@router.post("")
@router.post("/text")
async def generate_text(
    search_id: str = Body(None),
    prompt: str = Body(...),
    provider: str = Body(...),
    model: str = Body(...),
    temperature: float = Body(0.7),
    max_tokens: Optional[int] = Body(None)
):
    """
    基于检索结果生成文本
    """
    # 只用 config，不传 max_tokens 给服务层
    try:
        result = generate_service.generate_text(search_id, prompt, provider, model, temperature)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本生成失败: {str(e)}")

@router.post("/from_search")
async def generate_from_search(
    search_id: str = Body(...),
    prompt: str = Body(...),
    provider: str = Body(...),
    model: str = Body(...),
    temperature: float = Body(0.7),
    max_tokens: Optional[int] = Body(None),
    top_p: float = Body(1.0),
    stream: bool = Body(False)
):
    """
    基于搜索结果生成文本
    
    参数:
        search_id: 搜索结果ID
        prompt: 生成提示
        provider: 模型提供商
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大生成令牌数
        top_p: 采样阈值
        stream: 是否流式返回
    """
    try:
        # 使用与generate_text相同的服务方法，但确保search_id不为空
        if not search_id:
            raise ValueError("搜索结果ID不能为空")
            
        result = generate_service.generate_text(search_id, prompt, provider, model, temperature)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"基于搜索结果生成文本失败: {str(e)}")

@router.get("/models")
async def get_generation_models():
    """
    获取可用的生成模型列表
    """
    return generate_service.get_generation_models()
