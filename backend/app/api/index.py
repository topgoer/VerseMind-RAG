from fastapi import APIRouter, HTTPException, Body, Depends, Query
from typing import Dict, List, Optional
import os

from app.services.index_service import IndexService
from app.core.config import settings  # Changed import to use app.core.config

router = APIRouter()
# Pass the configured embeddings and indices directories to the service
index_service = IndexService(
    embeddings_dir=settings.EMBEDDINGS_DIR, 
    indices_dir=settings.INDICES_DIR
)

@router.post("/create")
async def create_index(
    document_id: str = Body(...),
    vector_db: str = Body(...),
    collection_name: str = Body(...),
    index_name: str = Body(...),
    embedding_id: str = Body(...),  # Added embedding_id
    version: str = Body("1.0")
):
    """
    创建向量索引
    """
    print(f"[API LOG /api/index/create] Received: document_id='{document_id}', vector_db='{vector_db}', collection_name='{collection_name}', index_name='{index_name}', embedding_id='{embedding_id}', version='{version}'")
    try:
        # Pass embedding_id to the service layer
        result = index_service.create_index(document_id, vector_db, collection_name, index_name, embedding_id, version)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引创建失败: {str(e)}")

@router.get("/list")
async def list_indices(document_id: Optional[str] = Query(None)):
    """
    获取所有索引列表，可选按文档ID过滤
    """
    try:
        indices = index_service.list_indices()
        if document_id:
            indices = [idx for idx in indices if idx.get("document_id") == document_id]
        return indices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取索引列表失败: {str(e)}")

@router.put("/{index_id}")
async def update_index(
    index_id: str,
    version: str = Body(...)
):
    """
    更新索引版本
    """
    try:
        result = index_service.update_index(index_id, version)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引更新失败: {str(e)}")

@router.delete("/{index_id}")
async def delete_index(index_id: str):
    """
    删除指定的索引
    """
    try:
        result = index_service.delete_index(index_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引删除失败: {str(e)}")
