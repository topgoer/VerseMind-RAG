from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Dict, List, Optional
import os

from app.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()

@router.post("/{index_id}")
async def search(
    index_id: str,
    query: str = Body(...),
    top_k: int = Body(3),
    similarity_threshold: float = Body(0.7),
    min_chars: int = Body(100)
):
    """
    执行语义搜索
    """
    try:
        result = search_service.search(index_id, query, top_k, similarity_threshold, min_chars)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
