from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional
import os
import logging

from app.services.chunk_service import ChunkService

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()
chunk_service = ChunkService()


@router.post("/create")
async def create_chunks(
    document_id: str = Body(...),
    strategy: str = Body(...),
    chunk_size: int = Body(1000),
    overlap: int = Body(200),
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
        raise HTTPException(
            status_code=404, detail=f"Chunk result file not found for id: {chunk_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete chunk result: {str(e)}"
        )


@router.get("/list")
async def list_all_chunks(document_id: Optional[str] = Query(None)):
    """
    获取所有分块结果，可选择按文档ID过滤
    """
    try:
        # Get a list of all files in the chunks directory for debugging
        chunks_dir = chunk_service.chunks_dir
        if os.path.exists(chunks_dir):
            files_in_dir = os.listdir(chunks_dir)
            logger.info(f"[list_all_chunks] Files in chunks directory: {files_in_dir}")
        else:
            logger.warning(
                f"[list_all_chunks] Chunks directory doesn't exist: {chunks_dir}"
            )

        # Get chunks from service
        chunks = chunk_service.get_document_chunks(document_id or "")

        logger.info(
            f"[list_all_chunks] Found {len(chunks)} chunks for document_id: '{document_id or 'All'}'"
        )
        if chunks:
            for i, chunk in enumerate(chunks[:3]):  # Log first 3 chunks
                logger.info(
                    f"[list_all_chunks] Chunk {i + 1}: id={chunk.get('id')}, document_id={chunk.get('document_id')}, document_name={chunk.get('document_name')}"
                )

        return chunks
    except Exception as e:
        import traceback

        logger.error(f"[list_all_chunks] Error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to list chunks: {str(e)}")
