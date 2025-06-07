from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional

from app.services.index_service import IndexService

router = APIRouter()
# Initialize the index service which now gets settings internally
index_service = IndexService()


@router.post("/create")
async def create_index(
    document_id: str = Body(...),
    embedding_id: str = Body(...),
    vector_db: Optional[str] = Body(
        None
    ),  # Optional, will use default from config if not provided
    collection_name: Optional[str] = Body(
        None
    ),  # Optional, will auto-generate if not provided
    index_name: Optional[str] = Body(
        None
    ),  # Optional, will auto-generate if not provided
    version: str = Body("1.0"),
):
    """
    创建向量索引

    - document_id: 文档ID（必填）
    - embedding_id: 嵌入ID（必填）
    - vector_db: 向量数据库类型，默认使用配置中的值
    - collection_name: 集合名称，默认自动生成
    - index_name: 索引名称，默认自动生成
    - version: 索引版本，默认为"1.0"
    """
    print(
        f"[API LOG /api/index/create] Received: document_id='{document_id}', vector_db='{vector_db}', collection_name='{collection_name}', index_name='{index_name}', embedding_id='{embedding_id}', version='{version}'"
    )
    try:
        # Use defaults from config if parameters are not provided
        result = index_service.create_index(
            document_id=document_id,
            embedding_id=embedding_id,
            vector_db=vector_db,
            collection_name=collection_name,
            index_name=index_name,
            version=version,
        )
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
    except FileNotFoundError:
        # If indices directory doesn't exist, return empty array instead of 404
        return []
    except Exception as e:
        # Log the error but return empty array instead of 500 error
        # This prevents frontend initialization errors
        print(f"[API ERROR] Error listing indices: {str(e)}")
        return []


@router.put("/{index_id}")
async def update_index(index_id: str, version: str = Body(...)):
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
