from fastapi import UploadFile
from pathlib import Path
import os
import fitz  # PyMuPDF
from docx import Document as DocxDocument  # Updated import for python-docx
import datetime
import uuid
import logging
from pypdf import PdfReader  # added multi-library support
from app.core.logger import get_logger_with_env_level

# Initialize logger using the environment-based configuration
logger = get_logger_with_env_level(__name__)

class LoadService:
    """文档加载服务，支持PDF、DOCX、TXT、Markdown格式"""

    def __init__(self, storage_dir="storage/documents", documents_dir=None):
        # Ensure storage directory is absolute, based on project root
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        abs_storage = project_root / storage_dir
        self.storage_dir = str(abs_storage)

        # Store relative path but use absolute when needed
        self.documents_dir = "backend/01-loaded_docs" if documents_dir is None else documents_dir
        # Also create a full absolute path to avoid path resolution issues
        self.abs_documents_dir = str(project_root / self.documents_dir)
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.abs_documents_dir, exist_ok=True)

        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s'))
        if not self.logger.hasHandlers():
            self.logger.addHandler(handler)
        self.logger.debug(f"[LoadService] storage_dir set to: {self.storage_dir}")
        self.logger.debug(f"[LoadService] documents_dir set to: {self.documents_dir} (absolute: {self.abs_documents_dir})")
        self.total_pages = 0
        self.current_page_map = []

    async def load_document(
        self,
        file: UploadFile,
        description: str = None,
        method: str = "pymupdf",
        strategy: str = None
    ):
        """
        加载文档并提取基本信息，文件保存为“原始文件名_日期时间_ID.后缀”，便于区分和溯源
        """
        # 检查文件类型
        orig_filename = os.path.splitext(file.filename)[0]
        file_ext = os.path.splitext(file.filename)[1].lower()
        self.logger.debug(f"[load_document] Received file: {file.filename}, ext: {file_ext}")

        # 生成唯一文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        self.logger.debug(f"[load_document] Generated unique_id: {unique_id}")
        # 新文件名：原始文件名_时间戳_ID.后缀，保留原始名
        safe_filename = f"{orig_filename}_{timestamp}_{unique_id}{file_ext}"

        # 保存文件
        file_path = os.path.join(self.storage_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            await file.seek(0)  # 重置文件指针以便后续处理
        self.logger.debug(f"[load_document] Saved file to: {file_path}, size: {os.path.getsize(file_path)} bytes")

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
            try:
                # use multi-library PDF loader
                text = self.load_pdf(
                    file_path,
                    method=method,
                    strategy=strategy
                )
            except Exception as e:
                self.logger.error(f"Failed to load PDF {file.filename}: {str(e)}")
                raise ValueError(f"Failed to process PDF: {str(e)}")
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
            self.logger.debug(f"[load_document] Loading DOCX: {file_path}")
            docx_info = self._extract_docx_info(file_path)
            doc_info["metadata"] = docx_info["metadata"]
            doc_info["preview"] = docx_info["preview"]
        elif file_ext in ['.txt', '.md']:
            self.logger.debug(f"[load_document] Loading TXT/MD: {file_path}")
            text_info = self._extract_text_info(file_path)
            doc_info["preview"] = text_info["preview"]
        elif file_ext == '.csv':
            self.logger.debug(f"[load_document] Loading CSV: {file_path}")
            try:
                import csv
                with open(file_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    preview_text = '\n'.join([', '.join(row) for row in rows[:5]])
            except Exception as e:
                self.logger.error(f"Failed to load CSV {file.filename}: {str(e)}")
                raise ValueError(f"Failed to process CSV: {str(e)}")

            doc_info.update({
                "metadata": {},
                "preview": preview_text,
                "row_count": len(rows),
                "column_count": len(rows[0]) if rows else 0
            })

        self.logger.debug(f"[load_document] Returning doc_info: {doc_info['filename']} (ID: {doc_info['id']})")
        self.save_document_json(doc_info)  # 自动保存为JSON
        return doc_info

    def load_pdf(
        self,
        file_path: str,
        method: str = "pymupdf",
        strategy: str = None
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
                # Only pass the strategy parameter that's actually used
                return self._load_with_unstructured(
                    file_path,
                    strategy=strategy
                )
            else:
                raise ValueError(f"Unsupported loading method: {method}")
        except Exception as e:
            self.logger.error(f"Error loading PDF with {method}: {str(e)}")
            raise IOError(f"PDF processing failed with {method}: {str(e)}")

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
            doc = DocxDocument(file_path)

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

    def _extract_file_info(self, filename):
        """从文件名中提取文件信息"""
        file_path = os.path.join(self.storage_dir, filename)
        if not os.path.isfile(file_path):
            return None

        file_ext = os.path.splitext(filename)[1][1:] if os.path.splitext(filename)[1] else ""
        file_base = os.path.splitext(filename)[0]
        return file_path, file_ext, file_base

    def _extract_document_id_and_name(self, filename, file_base):
        """从文件基本名称中提取文档ID和显示名称"""
        parts = file_base.split('_')
        # Extract unique ID (last part after underscore)
        unique_id = parts[-1] if len(parts) >= 3 else file_base
        # Use original filename for display if available
        orig_filename = '_'.join(parts[:-2]) if len(parts) >= 3 else filename
        return unique_id, orig_filename

    def _format_upload_time(self, stat, filename):
        """格式化上传时间"""
        try:
            return datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OverflowError, OSError) as e:
            self.logger.warning(f"Error formatting timestamp for {filename}: {str(e)}")
            return "Unknown"

    def _create_document_info(self, filename):
        """为单个文件创建文档信息"""
        file_info = self._extract_file_info(filename)
        if not file_info:
            return None

        file_path, file_ext, file_base = file_info
        stat = os.stat(file_path)

        unique_id, orig_filename = self._extract_document_id_and_name(filename, file_base)
        upload_time = self._format_upload_time(stat, filename)

        document = {
            "id": unique_id,
            "filename": orig_filename,
            "path": file_path,
            "size": stat.st_size,
            "upload_time": upload_time,
            "file_type": file_ext
        }

        self.logger.debug(f"Added document: id={unique_id}, name={orig_filename}")
        return document

    def get_document_list(self):
        """获取已上传文档列表（真实目录，无任何硬编码示例数据）"""
        documents = []
        self.logger.debug(f"Reading document list from storage directory: {self.storage_dir}")

        if not os.path.exists(self.storage_dir):
            self.logger.warning(f"Storage directory does not exist: {self.storage_dir}")
            return documents

        try:
            files = os.listdir(self.storage_dir)
            self.logger.debug(f"Found {len(files)} files in storage directory")

            for filename in files:
                try:
                    doc_info = self._create_document_info(filename)
                    if doc_info:
                        documents.append(doc_info)
                except Exception as e:
                    self.logger.error(f"Error processing file {filename}: {str(e)}")
                    # Continue with next file

            # No longer need to check for duplicate backend/backend folder
            # since it has been cleaned up in the cleanup-backend-duplicate.ps1 script

            self.logger.debug(f"Returning {len(documents)} documents from storage directory")
            return documents

        except Exception as e:
            self.logger.error(f"Error listing documents: {str(e)}")
            raise

    def get_document_by_id(self, document_id):
        """获取指定文档的详细信息"""
        filename, file_path, file_ext = self._find_document_file(document_id)
        if filename and file_path:  # Check if both filename and file_path are valid
            doc_info = self._create_basic_doc_info(document_id, filename, file_path, file_ext)
            self._enrich_doc_info_by_type(doc_info, file_path, file_ext)
            return doc_info
        return None

    def _find_document_file(self, document_id):
        """查找指定ID的文档文件"""
        if not os.path.exists(self.storage_dir):
            return None, None, None  # Return a tuple with None values for consistency

        self.logger.debug(f"Looking for document with ID: {document_id}")

        for filename in os.listdir(self.storage_dir):
            # 检查文件名末尾是否包含document_id (应该是具有文件名_时间戳_ID的格式)
            file_info = self._extract_file_info(filename)
            if not file_info:
                continue

            file_path, _, file_base = file_info
            unique_id, _ = self._extract_document_id_and_name(filename, file_base)

            self.logger.debug(f"Checking file {filename}, extracted ID: {unique_id}")

            # Check if ID matches exactly
            if unique_id == document_id:
                self.logger.debug(f"Found matching file: {filename}")
                return filename, file_path, os.path.splitext(filename)[1].lower()

        self.logger.debug(f"No matching file found for document ID: {document_id}")
        return None, None, None  # Return a tuple with None values for consistency

    def _create_basic_doc_info(self, document_id, filename, file_path, file_ext):
        """创建基本的文档信息字典"""
        # 从文件名解析信息
        parts = filename.split("_")
        timestamp = parts[0] + "_" + parts[1] if len(parts) >= 3 else ""

        return {
            "id": document_id,
            "filename": filename,
            "path": file_path,
            "size": os.path.getsize(file_path),
            "upload_time": timestamp,
            "file_type": file_ext[1:],  # 去掉点号
        }

    def _enrich_doc_info_by_type(self, doc_info, file_path, file_ext):
        """根据文件类型丰富文档信息"""
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

    def delete_document(self, document_id):
        """删除指定文档"""
        self.logger.info(f"Attempting to delete document with ID: {document_id}")
        filename, file_path, file_ext = self._find_document_file(document_id)

        self.logger.debug(f"Document search results: filename={filename}, path={file_path}, ext={file_ext}")

        if file_path:
            try:
                os.remove(file_path)
                self.logger.info(f"Successfully deleted document: {file_path}")
                return True
            except Exception as e:
                self.logger.error(f"Error deleting document {file_path}: {str(e)}")
                return False

        # List all files in directory for debugging
        if os.path.exists(self.storage_dir):
            self.logger.debug(f"Files in storage directory: {os.listdir(self.storage_dir)}")

        self.logger.warning(f"Could not find document with ID {document_id} to delete")
        return False

    def _load_with_unstructured(self, file_path: str, strategy: str = "fast") -> str:
        """
        使用unstructured库加载PDF文档。

        参数:
            file_path (str): PDF文件路径
            strategy (str): 处理策略, 'fast', 'hi_res', 或 'ocr_only'

        返回:
            str: 提取的文本内容
        """
        try:
            # lazy import to prevent import errors if dependencies missing
            from unstructured.partition.pdf import partition_pdf

            # Use strategy parameter directly in the partition_pdf call
            # 使用strategy参数直接调用partition_pdf
            elements = partition_pdf(file_path, strategy=strategy)
            text = "\n".join([str(el) for el in elements])

            # Create a simple page map (assuming each element is from a page)
            page_texts = {}
            for i, element in enumerate(elements):
                page_num = getattr(element, "metadata", {}).get("page_number", 1)
                if page_num not in page_texts:
                    page_texts[page_num] = []
                page_texts[page_num].append(str(element))

            # Set total pages and page map
            self.total_pages = max(page_texts.keys()) if page_texts else 0
            self.current_page_map = [
                {"text": "\n".join(texts), "page": page}
                for page, texts in page_texts.items()
            ]

            return text

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
        import importlib.util
        if importlib.util.find_spec("pdfplumber") is None:
            self.logger.error("pdfplumber not installed. Please run 'pip install pdfplumber'")
            raise ImportError("pdfplumber module not found")

        import pdfplumber  # type: ignore # Pylance doesn't see this import

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

    def _load_with_pypdf(self, file_path: str) -> str:
        """
        使用PyPDF库加载PDF文档。
        返回提取的文本内容，并更新 self.total_pages 和 self.current_page_map。
        """
        text_blocks = []
        try:
            pdf = PdfReader(file_path)
            self.total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    text_blocks.append({
                        "text": text.strip(),
                        "page": page_num
                    })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            self.logger.error(f"PyPDF error: {str(e)}")
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

        # Always use absolute path to avoid path resolution issues
        documents_dir = self.abs_documents_dir
        self.logger.debug(f"[save_document_json] Using absolute path: {documents_dir}")
        os.makedirs(documents_dir, exist_ok=True)

        # 生成文件名：原始名+时间戳+id.json
        base_name = os.path.splitext(doc_info.get("saved_as") or doc_info.get("filename"))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = doc_info.get("id", "")
        json_filename = f"{base_name}_{timestamp}_{unique_id}.json"
        json_path = os.path.join(documents_dir, json_filename)
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
