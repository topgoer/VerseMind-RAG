from fastapi import UploadFile
from pathlib import Path
import os
import fitz  # PyMuPDF
from docx import Document
import datetime
import uuid
import logging  # for debugging logs
from pypdf import PdfReader  # added multi-library support

class LoadService:
    """文档加载服务，支持PDF、DOCX、TXT、Markdown格式"""
    
    def __init__(self, storage_dir="storage/documents"):
        # Ensure storage directory is absolute, based on project root
        from pathlib import Path
        import logging
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        abs_storage = project_root / storage_dir
        self.storage_dir = str(abs_storage)
        self.documents_dir = self.storage_dir  # Add documents_dir for compatibility with tests
        os.makedirs(self.storage_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s'))
        if not self.logger.hasHandlers():
            self.logger.addHandler(handler)
        self.logger.info(f"[LoadService] storage_dir set to: {self.storage_dir}")
        self.total_pages = 0
        self.current_page_map = []
    
    async def load_document(
        self,
        file: UploadFile,
        description: str = None,
        method: str = "pymupdf",
        strategy: str = None,
        chunking_strategy: str = None,
        chunking_options: dict = None
    ):
        """
        加载文档并提取基本信息，文件保存为“原始文件名_日期时间_ID.后缀”，便于区分和溯源
        """
        # 检查文件类型
        orig_filename = os.path.splitext(file.filename)[0]
        file_ext = os.path.splitext(file.filename)[1].lower()
        self.logger.info(f"[load_document] Received file: {file.filename}, ext: {file_ext}")
        
        # 生成唯一文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        self.logger.info(f"[load_document] Generated unique_id: {unique_id}")
        # 新文件名：原始文件名_时间戳_ID.后缀，保留原始名
        safe_filename = f"{orig_filename}_{timestamp}_{unique_id}{file_ext}"
        
        # 保存文件
        file_path = os.path.join(self.storage_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            await file.seek(0)  # 重置文件指针以便后续处理
        self.logger.info(f"[load_document] Saved file to: {file_path}, size: {os.path.getsize(file_path)} bytes")
        
        # 提取文档信息
        doc_info = {
            "id": unique_id,
            "filename": file.filename,  # 用户上传时的原始文件名
            "saved_as": safe_filename,  # 实际保存的文件名
            "path": file_path,
            "size": os.path.getsize(file_path),
            "description": description,
            "upload_time": timestamp,
            "file_type": file_ext[1:],  # 去掉点号
            "metadata": {},
            "preview": None
        }
        
        # 根据文件类型提取或加载信息
        if file_ext == '.pdf':
            self.logger.debug(f"[load_document] Loading PDF: {file_path} with method={method}")
            # use multi-library PDF loader
            text = self.load_pdf(
                file_path,
                method=method,
                strategy=strategy,
                chunking_strategy=chunking_strategy,
                chunking_options=chunking_options or {}
            )
            self.logger.debug(f"[load_document] PDF loaded, page_count={self.total_pages}")
            # Limit preview to first 50 words
            words = text.split()
            preview_text = " ".join(words[:50])
            if len(words) > 50:
                preview_text += "..."
            
            doc_info.update({
                "metadata": {},
                "preview": preview_text,
                "page_map": self.current_page_map,
                "page_count": self.total_pages,
                "text": text
            })
        elif file_ext == '.docx':
            self.logger.info(f"[load_document] Loading DOCX: {file_path}")
            docx_info = self._extract_docx_info(file_path)
            doc_info["metadata"] = docx_info["metadata"]
            doc_info["preview"] = docx_info["preview"]
        elif file_ext in ['.txt', '.md']:
            self.logger.info(f"[load_document] Loading TXT/MD: {file_path}")
            text_info = self._extract_text_info(file_path)
            doc_info["preview"] = text_info["preview"]
        
        self.logger.info(f"[load_document] Returning doc_info: {doc_info['filename']} (ID: {doc_info['id']})")
        self.save_document_json(doc_info)  # 自动保存为JSON
        return doc_info
    
    def load_pdf(
        self,
        file_path: str,
        method: str = "pymupdf",
        strategy: str = None,
        chunking_strategy: str = None,
        chunking_options: dict = None
    ) -> str:
        """
        加载PDF文档，支持多种库和策略，记录 page_map 和 total_pages
        """
        try:
            if method == 'pymupdf':
                return self._load_with_pymupdf(file_path)
            elif method == 'pypdf':
                return self._load_with_pypdf(file_path)
            elif method == 'pdfplumber':
                return self._load_with_pdfplumber(file_path)
            elif method == 'unstructured':
                return self._load_with_unstructured(
                    file_path,
                    strategy=strategy,
                    chunking_strategy=chunking_strategy,
                    chunking_options=chunking_options
                )
            else:
                raise ValueError(f"Unsupported loading method: {method}")
        except Exception as e:
            self.logger.error(f"Error loading PDF with {method}: {str(e)}")
            raise

    def get_total_pages(self) -> int:
        """获取当前加载文档的总页数"""
        return self.total_pages

    def get_page_map(self) -> list:
        """获取当前文档的页面映射信息"""
        return self.current_page_map

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
        """获取已上传文档列表（真实目录，无任何硬编码示例数据）"""
        documents = []
        if os.path.exists(self.storage_dir):
            for filename in os.listdir(self.storage_dir):
                file_path = os.path.join(self.storage_dir, filename)
                if os.path.isfile(file_path):
                    file_ext = os.path.splitext(filename)[1][1:]  # 去掉点号
                    stat = os.stat(file_path)
                    documents.append({
                        "id": os.path.splitext(filename)[0],
                        "filename": filename,
                        "path": file_path,
                        "size": stat.st_size,
                        "upload_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
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

    def _load_with_unstructured(self, file_path: str, strategy: str = "fast", chunking_strategy: str = "basic", chunking_options: dict = None) -> str:
        """
        使用unstructured库加载PDF文档。
        """
        try:
            # lazy import to prevent import errors if dependencies missing
            from unstructured.partition.pdf import partition_pdf
            strategy_params = {
                "fast": {"strategy": "fast"},
                "hi_res": {"strategy": "hi_res"},
                "ocr_only": {"strategy": "ocr_only"}
            }
            # Prepare chunking parameters based on strategy
            # ...existing code...
        except Exception as e:
            # Log and propagate errors from unstructured loading
            self.logger.error(f"Unstructured loading error: {e}")
            raise

    def _load_with_pdfplumber(self, file_path: str) -> str:
        """
        使用pdfplumber库加载PDF文档。
        适合需要处理表格或需要文本位置信息的场景。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        # lazy import pdfplumber to avoid import errors at startup
        try:
            import pdfplumber
        except ImportError as e:
            self.logger.error(f"pdfplumber import error: {e}")
            raise

        text_blocks = []
        try:
            with pdfplumber.open(file_path) as pdf:
                self.total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_blocks.append({
                            "text": page_text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            self.logger.error(f"pdfplumber error: {str(e)}")
            raise

    def _load_with_pymupdf(self, file_path: str) -> str:
        """
        使用PyMuPDF库加载PDF文档。
        返回提取的文本内容，并更新 self.total_pages 和 self.current_page_map。
        """
        import fitz
        text_blocks = []
        try:
            with fitz.open(file_path) as doc:
                self.total_pages = len(doc)
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text("text")
                    if text.strip():
                        text_blocks.append({
                            "text": text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            self.logger.error(f"PyMuPDF error: {str(e)}")
            raise

    def save_document_json(self, doc_info: dict) -> str:
        """
        保存加载后的文档信息为标准JSON文件，便于后续分块、解析等处理。
        参数:
            doc_info (dict): load_document 返回的文档信息字典
        返回:
            str: 保存的JSON文件路径
        """
        import json
        from datetime import datetime
        os.makedirs("01-loaded_docs", exist_ok=True)
        # 生成文件名：原始名+时间戳+id.json
        base_name = os.path.splitext(doc_info.get("saved_as") or doc_info.get("filename"))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = doc_info.get("id", "")
        json_filename = f"{base_name}_{timestamp}_{unique_id}.json"
        json_path = os.path.join("01-loaded_docs", json_filename)
        # 只保留主要字段
        save_data = {
            k: v for k, v in doc_info.items() if k in [
                "id", "filename", "saved_as", "path", "size", "description", "upload_time", "file_type", "metadata", "preview", "page_map", "page_count", "text"
            ]
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        self.logger.debug(f"[save_document_json] Saved JSON to: {json_path}")
        return json_path
