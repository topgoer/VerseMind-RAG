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
    max_tokens: int = Body(1024)
):
    """
    基于检索结果生成文本
    """
    try:
        result = generate_service.generate_text(search_id, prompt, provider, model, temperature, max_tokens)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本生成失败: {str(e)}")

@router.get("/models")
async def get_generation_models():
    """
    获取可用的生成模型列表
    """
    return generate_service.get_generation_models()
