from fastapi import UploadFile
import os
import fitz  # PyMuPDF
from docx import Document
import datetime
import uuid

class LoadService:
    """文档加载服务，支持PDF、DOCX、TXT、Markdown格式"""
    
    def __init__(self, storage_dir="storage/documents"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    async def load_document(self, file: UploadFile, description: str = None):
        """
        加载文档并提取基本信息
        """
        # 检查文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        # 生成唯一文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{timestamp}_{unique_id}{file_ext}"
        
        # 保存文件
        file_path = os.path.join(self.storage_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            await file.seek(0)  # 重置文件指针以便后续处理
        
        # 提取文档信息
        doc_info = {
            "id": unique_id,
            "filename": file.filename,
            "saved_as": safe_filename,
            "path": file_path,
            "size": os.path.getsize(file_path),
            "description": description,
            "upload_time": timestamp,
            "file_type": file_ext[1:],  # 去掉点号
            "metadata": {},
            "preview": None
        }
        
        # 根据文件类型提取额外信息
        if file_ext == '.pdf':
            pdf_info = self._extract_pdf_info(file_path)
            doc_info["metadata"] = pdf_info["metadata"]
            doc_info["preview"] = pdf_info["preview"]
            doc_info["page_count"] = pdf_info["page_count"]
        elif file_ext == '.docx':
            docx_info = self._extract_docx_info(file_path)
            doc_info["metadata"] = docx_info["metadata"]
            doc_info["preview"] = docx_info["preview"]
        elif file_ext in ['.txt', '.md']:
            text_info = self._extract_text_info(file_path)
            doc_info["preview"] = text_info["preview"]
        
        return doc_info
    
    def _extract_pdf_info(self, file_path):
        """提取PDF文档信息"""
        try:
            doc = fitz.open(file_path)
            
            # 提取元数据
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", "")
            }
            
            # 提取第一页文本作为预览
            preview = ""
            if doc.page_count > 0:
                first_page = doc[0]
                preview = first_page.get_text()
                if len(preview) > 500:
                    preview = preview[:500] + "..."
            
            return {
                "metadata": metadata,
                "preview": preview,
                "page_count": doc.page_count
            }
        except Exception as e:
            return {
                "metadata": {"error": str(e)},
                "preview": "无法提取PDF预览",
                "page_count": 0
            }
    
    def _extract_docx_info(self, file_path):
        """提取DOCX文档信息"""
        try:
            doc = Document(file_path)
            
            # 提取元数据
            core_properties = doc.core_properties
            metadata = {
                "title": core_properties.title or "",
                "author": core_properties.author or "",
                "subject": core_properties.subject or "",
                "keywords": core_properties.keywords or "",
                "created": str(core_properties.created) if core_properties.created else "",
                "modified": str(core_properties.modified) if core_properties.modified else "",
                "last_modified_by": core_properties.last_modified_by or ""
            }
            
            # 提取文本作为预览
            preview = "\n".join([para.text for para in doc.paragraphs[:10]])
            if len(preview) > 500:
                preview = preview[:500] + "..."
            
            return {
                "metadata": metadata,
                "preview": preview
            }
        except Exception as e:
            return {
                "metadata": {"error": str(e)},
                "preview": "无法提取DOCX预览"
            }
    
    def _extract_text_info(self, file_path):
        """提取TXT/MD文档信息"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read(1000)  # 读取前1000个字符
                preview = text
                if len(text) == 1000:
                    preview = text + "..."
            
            return {
                "preview": preview
            }
        except Exception as e:
            return {
                "preview": f"无法提取文本预览: {str(e)}"
            }
    
    def get_document_list(self):
        """获取已上传文档列表"""
        documents = []
        
        if os.path.exists(self.storage_dir):
            for filename in os.listdir(self.storage_dir):
                file_path = os.path.join(self.storage_dir, filename)
                if os.path.isfile(file_path):
                    # 从文件名解析信息
                    parts = filename.split("_")
                    if len(parts) >= 3:
                        timestamp = parts[0] + "_" + parts[1]
                        unique_id = parts[2].split(".")[0]
                        file_ext = os.path.splitext(filename)[1][1:]  # 去掉点号
                        
                        documents.append({
                            "id": unique_id,
                            "filename": filename,
                            "path": file_path,
                            "size": os.path.getsize(file_path),
                            "upload_time": timestamp,
                            "file_type": file_ext
                        })
        
        return documents
    
    def get_document_by_id(self, document_id):
        """获取指定文档的详细信息"""
        if os.path.exists(self.storage_dir):
            for filename in os.listdir(self.storage_dir):
                if document_id in filename:
                    file_path = os.path.join(self.storage_dir, filename)
                    file_ext = os.path.splitext(filename)[1].lower()
                    
                    # 从文件名解析信息
                    parts = filename.split("_")
                    if len(parts) >= 3:
                        timestamp = parts[0] + "_" + parts[1]
                        
                        doc_info = {
                            "id": document_id,
                            "filename": filename,
                            "path": file_path,
                            "size": os.path.getsize(file_path),
                            "upload_time": timestamp,
                            "file_type": file_ext[1:],  # 去掉点号
                        }
                        
                        # 根据文件类型提取额外信息
                        if file_ext == '.pdf':
                            pdf_info = self._extract_pdf_info(file_path)
                            doc_info["metadata"] = pdf_info["metadata"]
                            doc_info["preview"] = pdf_info["preview"]
                            doc_info["page_count"] = pdf_info["page_count"]
                        elif file_ext == '.docx':
                            docx_info = self._extract_docx_info(file_path)
                            doc_info["metadata"] = docx_info["metadata"]
                            doc_info["preview"] = docx_info["preview"]
                        elif file_ext in ['.txt', '.md']:
                            text_info = self._extract_text_info(file_path)
                            doc_info["preview"] = text_info["preview"]
                        
                        return doc_info
        
        return None
    
    def delete_document(self, document_id):
        """删除指定文档"""
        if os.path.exists(self.storage_dir):
            for filename in os.listdir(self.storage_dir):
                if document_id in filename:
                    file_path = os.path.join(self.storage_dir, filename)
                    os.remove(file_path)
                    return True
        
        return False
