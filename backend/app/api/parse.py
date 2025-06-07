from fastapi import APIRouter, HTTPException, Body
from typing import Dict, List, Any, Optional

from app.services.parse_service import ParseService

router = APIRouter()
parse_service = ParseService()

@router.post("/create")
async def create_parse(
    document_id: str = Body(...),
    strategy: str = Body(...),
    extract_tables: bool = Body(False),
    extract_images: bool = Body(False)
):
    """
    创建解析结果并持久化
    """
    try:
        result = parse_service.parse_document(
            document_id=document_id,
            strategy=strategy,
            extract_tables=extract_tables,
            extract_images=extract_images
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")

@router.post("/{document_id}")
async def parse_document(
    document_id: str,
    strategy: str = Body(...),
    page_map: Optional[List[Dict[str, Any]]] = Body(None),
    extract_tables: bool = Body(False),
    extract_images: bool = Body(False)
):
    """
    解析文档结构，包括段落、表格和标题
    """
    try:
        result = parse_service.parse_document(
            document_id=document_id,
            strategy=strategy,
            page_map=page_map,
            extract_tables=extract_tables,
            extract_images=extract_images
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")

@router.get("/list")
async def list_parsed(document_id: str):
    """
    获取指定文档的所有解析结果
    """
    try:
        results = parse_service.list_parsed(document_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取解析结果失败: {str(e)}")

@router.get("/{document_id}")
async def get_parsed_document(document_id: str):
    """
    获取指定文档的最新解析结果
    """
    try:
        results = parse_service.list_parsed(document_id)
        # Return the most recent parsing result if available
        if results and len(results) > 0:
            return results[0]
        else:
            raise HTTPException(status_code=404, detail=f"没有找到文档ID为{document_id}的解析结果")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取解析结果失败: {str(e)}")
