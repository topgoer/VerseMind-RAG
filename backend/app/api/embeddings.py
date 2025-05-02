from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Dict, List, Optional
import os

from app.services.embed_service import EmbedService

router = APIRouter()
embed_service = EmbedService()

@router.post("/create")
async def create_embeddings(
    document_id: str = Body(...),
    provider: str = Body(...),
    model: str = Body(...)
):
    """
    将文本块转换为向量表示
    """
    try:
        result = embed_service.create_embeddings(document_id, provider, model)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"嵌入生成失败: {str(e)}")

@router.get("/models")
async def get_embedding_models():
    """
    获取可用的嵌入模型列表
    """
    return embed_service.get_embedding_models()
