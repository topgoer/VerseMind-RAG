from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import os

from app.services.load_service import LoadService

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
    allowed_extensions = [".pdf", ".docx", ".txt", ".md"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的文件类型。请上传PDF、DOCX、TXT或Markdown文件。")
    
    # 使用服务处理文件上传
    result = await load_service.load_document(file, description)
    return result

@router.get("/list")
async def list_documents():
    """
    获取已上传文档列表
    """
    return load_service.get_document_list()

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
    success = load_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"找不到ID为{document_id}的文档")
    return {"message": f"文档 {document_id} 已成功删除"}
