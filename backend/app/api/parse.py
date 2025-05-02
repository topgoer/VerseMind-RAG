from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Dict, List, Optional
import os

from app.services.parse_service import ParseService

router = APIRouter()
parse_service = ParseService()

@router.post("/{document_id}")
async def parse_document(
    document_id: str,
    strategy: str = Body(...),
    extract_tables: bool = Body(False),
    extract_images: bool = Body(False)
):
    """
    解析文档结构，包括段落、表格和标题
    """
    try:
        result = parse_service.parse_document(document_id, strategy, extract_tables, extract_images)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")
