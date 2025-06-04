from fastapi import APIRouter, HTTPException, Body, Depends, Query
from typing import Dict, List, Any, Optional
import os
import logging

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

@router.get("/list")
async def list_embeddings(document_id: Optional[str] = Query(None, description="Optional document ID to filter embeddings")):
    """
    获取所有嵌入向量的列表，可选择按文档ID过滤
    """
    try:
        # Add request logging
        logging.debug(f"Handling embeddings/list request, document_id={document_id}")
        
        result = embed_service.list_embeddings(document_id)
        
        # Add response logging
        embedding_count = len(result) if isinstance(result, list) else 0
        logging.debug(f"Returning {embedding_count} embeddings in response")
        
        # Ensure we return a valid list
        if not isinstance(result, list):
            logging.warning(f"list_embeddings did not return a list: {type(result)}")
            return []
        
        return result
    except Exception as e:
        logging.error(f"Error handling embeddings/list request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取嵌入列表失败: {str(e)}")

@router.delete("/{embedding_id}")
async def delete_embedding(embedding_id: str):
    """
    删除指定ID的嵌入向量
    """
    try:
        result = embed_service.delete_embedding(embedding_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除嵌入失败: {str(e)}")
