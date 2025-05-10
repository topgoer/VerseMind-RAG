from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Dict, List, Optional
import os

from app.services.chunk_service import ChunkService

router = APIRouter()
chunk_service = ChunkService()

@router.post("/create")
async def create_chunks(
    document_id: str = Body(...),
    strategy: str = Body(...),
    chunk_size: int = Body(1000),
    overlap: int = Body(200)
):
    """
    根据指定策略将文档分块
    """
    try:
        result = chunk_service.create_chunks(document_id, strategy, chunk_size, overlap)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分块处理失败: {str(e)}")

@router.get("/{document_id}")
async def get_document_chunks(document_id: str):
    """
    获取指定文档的分块结果
    """
    chunks = chunk_service.get_document_chunks(document_id)
    # 修改：找不到分块时返回空列表而不是报404
    if not chunks:
        return []
    return chunks

@router.delete("/{chunk_id}")
async def delete_chunk_result(chunk_id: str):
    """
    删除指定的分块结果文件
    """
    try:
        result_message = chunk_service.delete_chunk_result(chunk_id)
        return {"message": result_message}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Chunk result file not found for id: {chunk_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chunk result: {str(e)}")
