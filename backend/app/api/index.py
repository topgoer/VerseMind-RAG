from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Dict, List, Optional
import os

from app.services.index_service import IndexService

router = APIRouter()
index_service = IndexService()

@router.post("/create")
async def create_index(
    document_id: str = Body(...),
    vector_db: str = Body(...),
    collection_name: str = Body(...),
    index_name: str = Body(...),
    version: str = Body("1.0")
):
    """
    创建向量索引
    """
    try:
        result = index_service.create_index(document_id, vector_db, collection_name, index_name, version)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引创建失败: {str(e)}")

@router.get("/list")
async def list_indices():
    """
    获取所有索引列表
    """
    return index_service.list_indices()

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
