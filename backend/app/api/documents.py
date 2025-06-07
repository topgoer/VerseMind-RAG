from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import os
import logging

from app.services.load_service import LoadService

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()
load_service = LoadService()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None)
):
    """
    上传文档文件（PDF、DOCX、TXT、Markdown）
    """
    # 检查文件类型
    allowed_extensions = [".pdf", ".docx", ".txt", ".md", ".csv"]
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的文件类型。请上传PDF、DOCX、TXT或Markdown文件。")

    # 使用服务处理文件上传
    try:
        result = await load_service.load_document(file, description)
        return result
    except Exception as e:
        # Log the error and return a proper JSON response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Document upload error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Document processing failed: {str(e)}"}
        )

@router.get("/list")
async def list_documents():
    """
    获取已上传文档列表
    """
    try:
        documents = load_service.get_document_list()
        print(f"List documents API returning {len(documents)} documents")
        return documents
    except Exception as e:
        import traceback
        print(f"Error in list_documents: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")

@router.get("/{document_id}")
async def get_document(document_id: str):
    """
    获取指定文档的详细信息
    """
    document = load_service.get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"找不到ID为{document_id}的文档")
    return document

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    删除指定文档
    """
    # Log the request for debugging
    logger.info(f"Received request to delete document with ID: {document_id}")

    success = load_service.delete_document(document_id)
    if not success:
        logger.warning(f"Document deletion failed for ID: {document_id}")
        raise HTTPException(status_code=404, detail=f"找不到ID为{document_id}的文档")

    logger.info(f"Document with ID {document_id} successfully deleted")
    return {"message": f"文档 {document_id} 已成功删除"}

# New endpoint to download documents
@router.get("/{document_id}/download")
async def download_document(document_id: str):
    """
    Download a document by ID
    """
    document = load_service.get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = document["path"]
    filename = document["filename"]
    return FileResponse(path=file_path, media_type="application/octet-stream", filename=filename)
