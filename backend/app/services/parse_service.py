import os
import json
import datetime
import uuid
from typing import Dict, List, Any, Optional, Tuple
import re
import logging
import pandas as pd  # added for table parsing
from app.core.logger import get_logger_with_env_level

# Initialize logger using the environment-based configuration
logger = get_logger_with_env_level(__name__)

class ParseService:
    """文档解析服务，支持全文、分页、标题结构解析"""
    
    def __init__(self, chunks_dir=None, parsed_dir=None):
        # Update directories according to the naming convention using pathlib for consistency
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.storage_dir = str(project_root)
        self.documents_dir = str(project_root / 'storage' / 'documents')
        
        # Use absolute paths with project_root as base directory
        self.chunks_dir = chunks_dir or str(project_root / 'backend' / '02-chunked-docs')  
        self.parsed_dir = parsed_dir or str(project_root / 'backend' / '03-parsed-docs')
        
        # Create directories if they don't exist
        os.makedirs(self.documents_dir, exist_ok=True)
        os.makedirs(self.chunks_dir, exist_ok=True)
        os.makedirs(self.parsed_dir, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"ParseService initialized. Documents_dir: {self.documents_dir}, Chunks_dir: {self.chunks_dir}, Parsed_dir: {self.parsed_dir}") # Added log

    def parse_document(self,
                       document_id: str,
                       strategy: str,
                       page_map: List[Dict[str, Any]] = None,
                       extract_tables: bool = False,
                       extract_images: bool = False) -> Dict[str, Any]:
        """
        解析文档结构，支持直接传入 page_map

        参数:
            document_id: 文档ID
            strategy: 解析策略 ("full_text", "by_page", "by_heading", "text_and_tables")
            page_map: 可选页面映射列表，每项包含 {"text": ..., "page": ...}
            extract_tables: 是否提取表格
            extract_images: 是否提取图像
        返回:
            包含解析结果的字典
        """
        self.logger.debug(f"Starting parse_document for document_id: {document_id} with strategy: {strategy}")
        
        # 验证文档存在并获取路径
        document_path = self._validate_document_exists(document_id)
        
        # 获取分块数据
        chunk_data = self._get_chunk_data(document_id, page_map)
        
        # 生成元数据
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        parse_id = str(uuid.uuid4())[:8]
        metadata = self._create_metadata(document_path, chunk_data, strategy, timestamp)
        
        # 根据策略解析文档
        parsed_content = self._parse_content_by_strategy(strategy, chunk_data)
        
        # 提取表格和图像
        tables, images = self._extract_media_content(document_path, extract_tables, extract_images)
        
        # 构建结果
        result = self._build_parse_result(metadata, parsed_content, tables, images)
        
        # 计算统计数据
        stats = self._calculate_content_statistics(strategy, parsed_content, tables, images)
        
        # 保存结果文件
        result_file = self._save_parse_result(document_id, timestamp, result)
        
        # 返回最终结果
        return self._build_final_response(document_id, parse_id, strategy, timestamp, 
                                         result_file, stats, parsed_content)

    def _get_sample_content(self, parsed_content, strategy, max_items=10):
        """获取解析内容的样本，用于前端展示"""
        if strategy in ["full_text", "by_page", "by_heading"]:
            return self._get_structured_sample(parsed_content, max_items)
        elif strategy == "text_and_tables":
            return self._get_mixed_content_sample(parsed_content, max_items)
        return []

    def _get_structured_sample(self, parsed_content, max_items):
        """获取结构化内容的样本"""
        if not isinstance(parsed_content, dict):
            return []
        
        sample = []
        
        # 添加标题
        if "title" in parsed_content and parsed_content["title"]:
            sample.append({
                "type": "heading",
                "level": 1,
                "text": parsed_content["title"]
            })
        
        # 添加章节内容
        sections = parsed_content.get("sections", [])
        max_sections = max_items // 2
        
        for i, section in enumerate(sections):
            if i >= max_sections:
                break
            
            self._add_section_sample(sample, section, i)
        
        return sample
    
    def _add_section_sample(self, sample, section, section_index):
        """添加章节样本内容"""
        # 添加章节标题
        sample.append({
            "type": "heading",
            "level": section.get("level", 1),
            "text": section.get("title", f"Section {section_index+1}")
        })
        
        # 添加段落样本
        self._add_paragraphs_sample(sample, section.get("paragraphs", []), max_paragraphs=2)
        
        # 添加子章节样本
        self._add_subsections_sample(sample, section.get("subsections", []), section_index)
    
    def _add_paragraphs_sample(self, sample, paragraphs, max_paragraphs):
        """添加段落样本"""
        for j, para in enumerate(paragraphs):
            if j >= max_paragraphs:
                break
            sample.append({
                "type": "paragraph",
                "text": para.get("text", "")
            })
    
    def _add_subsections_sample(self, sample, subsections, section_index):
        """添加子章节样本"""
        for k, subsection in enumerate(subsections):
            if k >= 1:  # 每节最多1个子节
                break
            
            # 添加子章节标题
            sample.append({
                "type": "heading",
                "level": subsection.get("level", 2),
                "text": subsection.get("title", f"Subsection {section_index+1}.{k+1}")
            })
            
            # 添加子章节段落
            self._add_paragraphs_sample(sample, subsection.get("paragraphs", []), max_paragraphs=1)
    
    def _get_mixed_content_sample(self, parsed_content, max_items):
        """获取混合内容（文本和表格）的样本"""
        sample = []
        
        for i, item in enumerate(parsed_content):
            if i >= max_items:
                break
            
            item_type = item.get("type")
            if item_type == "text":
                sample.append({
                    "type": "paragraph",
                    "text": item.get("content", "").strip()[:200]  # 限制长度
                })
            elif item_type == "table":
                sample.append({
                    "type": "table",
                    "text": "表格数据"  # 简化表格表示
                })
        
        return sample

    def list_parsed(self, document_id: str):
        """
        列出指定文档的所有解析结果
        """
        self.logger.debug(f"Listing parsed results for document_id: {document_id} in directory: {self.parsed_dir}") # Added log
        parsed_dir = self.parsed_dir
        os.makedirs(parsed_dir, exist_ok=True)
        results = []
        for fname in os.listdir(parsed_dir):
            if fname.startswith(document_id) and fname.endswith(".json"):
                with open(os.path.join(parsed_dir, fname), "r", encoding="utf-8") as f:
                    results.append(json.load(f))
        self.logger.debug(f"Found {len(results)} parsed files for document_id: {document_id}") # Added log
        return results

    def _find_document(self, document_id: str) -> Optional[str]:
        """查找指定ID的文档路径"""
        self.logger.debug(f"Searching for document with ID: {document_id} in {self.documents_dir}") # Added log
        if os.path.exists(self.documents_dir):
            for filename in os.listdir(self.documents_dir):
                if document_id in filename:
                    self.logger.debug(f"Found document: {filename}") # Added log
                    return os.path.join(self.documents_dir, filename)
                    
        # If not found in documents_dir, try the storage/documents directory
        storage_dir = os.path.join(self.storage_dir, 'storage', 'documents')
        if os.path.exists(storage_dir) and storage_dir != self.documents_dir:
            self.logger.debug(f"Trying alternative directory: {storage_dir}")
            for filename in os.listdir(storage_dir):
                if document_id in filename:
                    self.logger.debug(f"Found document in storage/documents: {filename}")
                    return os.path.join(storage_dir, filename)
                    
        self.logger.warning(f"Document with ID: {document_id} not found in {self.documents_dir} or alternative locations") # Added log
        return None
    
    def _find_chunk_file(self, document_id: str) -> Optional[str]:
        """查找指定文档的分块文件"""
        self.logger.debug(f"Searching for chunk file for document ID: {document_id}")
        
        # Try all possible locations for chunk files
        search_paths = [
            self.chunks_dir,                                            # Primary path (backend/02-chunked-docs)
            os.path.join(self.storage_dir, 'backend', '02-chunked-docs'),  # Backend folder path
            os.path.join(self.storage_dir, '02-chunked-docs'),          # Root directory path
            os.path.join(self.storage_dir, 'backend/02-chunked-docs'),  # Alt path format
            os.path.join(os.path.dirname(__file__), '../../../../backend/02-chunked-docs') # Absolute path
        ]
        
        # Log all search paths
        for i, path in enumerate(search_paths):
            self.logger.debug(f"Search path {i+1}: {path}")
            if os.path.exists(path):
                self.logger.debug(f"Path {i+1} exists")
            else:
                self.logger.debug(f"Path {i+1} does NOT exist")
        
        # Search through all possible locations
        for i, path in enumerate(search_paths):
            is_alternative = (i > 0)  # First path is primary, others are alternatives
            self.logger.debug(f"Searching in {'alternative' if is_alternative else 'primary'} path: {path}")
            
            chunk_file = self._search_chunk_file_in_directory(document_id, path, is_alternative=is_alternative)
            if chunk_file:
                self.logger.info(f"Found chunk file at: {chunk_file}")
                return chunk_file
        
        self.logger.error(f"No chunk file found for document ID: {document_id} in any location")
        return None
    
    def _search_chunk_file_in_directory(self, document_id: str, directory: str, is_alternative: bool = False) -> Optional[str]:
        """在指定目录中搜索分块文件"""
        if not self._validate_search_directory(directory, is_alternative):
            return None
        
        newest_chunk_file = None
        newest_time = 0
        
        if is_alternative:
            self.logger.debug(f"Checking alternative chunks directory: {directory}")
        
        try:
            files = self._get_directory_files(directory)
            
            # First try: find by filename
            newest_chunk_file, newest_time = self._find_chunk_by_filename(
                document_id, directory, files, newest_time
            )
            
            # Second try: find by metadata
            if not newest_chunk_file:
                newest_chunk_file, newest_time = self._find_chunk_by_metadata(
                    document_id, directory, files, newest_time
                )
                
        except Exception as e:
            self.logger.error(f"Error searching for chunk files in {directory}: {e}")
        
        if newest_chunk_file:
            self._log_found_chunk(newest_chunk_file, is_alternative)
            return newest_chunk_file
        
        if not is_alternative:
            self.logger.warning(f"Chunk file for document ID: {document_id} not found in {directory} or alternative locations")
        
        return None
        
    def _validate_search_directory(self, directory: str, is_alternative: bool) -> bool:
        """Validate if directory should be searched"""
        if not os.path.exists(directory):
            self.logger.warning(f"Directory does not exist: {directory}")
            return False
        
        if is_alternative and directory == self.chunks_dir:
            return False
            
        return True
        
    def _get_directory_files(self, directory: str) -> List[str]:
        """Get list of files from directory"""
        files = os.listdir(directory)
        self.logger.debug(f"Found {len(files)} files in {directory}")
        return files
        
    def _find_chunk_by_filename(self, document_id: str, directory: str, files: List[str], newest_time: float) -> Tuple[Optional[str], float]:
        """Find chunk file by checking if document_id appears in filename"""
        from app.services.chunk_service import CHUNKS_JSON_SUFFIX
        newest_chunk_file = None
        
        for filename in files:
            if document_id in filename:
                filepath = os.path.join(directory, filename)
                self.logger.debug(f"Found potential chunk file: {filepath}")
                
                if os.path.exists(filepath) and filename.endswith(CHUNKS_JSON_SUFFIX):
                    file_mtime = os.path.getmtime(filepath)
                    
                    if file_mtime > newest_time:
                        newest_time = file_mtime
                        newest_chunk_file = filepath
                        self.logger.debug(f"Set as newest chunk file: {filepath}")
                        
        return newest_chunk_file, newest_time
    
    def _find_chunk_by_metadata(self, document_id: str, directory: str, files: List[str], newest_time: float) -> Tuple[Optional[str], float]:
        """Find chunk file by loading each file and checking metadata"""
        from app.services.chunk_service import CHUNKS_JSON_SUFFIX
        newest_chunk_file = None
        
        for filename in files:
            if filename.endswith(CHUNKS_JSON_SUFFIX):
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("document_id") == document_id:
                            file_mtime = os.path.getmtime(filepath)
                            if file_mtime > newest_time:
                                newest_time = file_mtime
                                newest_chunk_file = filepath
                                self.logger.debug(f"Found chunk file by metadata: {filepath}")
                except Exception as e:
                    self.logger.warning(f"Error checking chunk file metadata for {filepath}: {e}")
                    
        return newest_chunk_file, newest_time
    
    def _log_found_chunk(self, chunk_file: str, is_alternative: bool) -> None:
        """Log information about found chunk file"""
        location_type = "alternative location" if is_alternative else "primary location"
        self.logger.debug(f"Found chunk file in {location_type}: {os.path.basename(chunk_file)}")
    
    def _is_valid_chunk_file(self, filename: str, document_id: str) -> bool:
        """检查文件名是否为有效的分块文件"""
        from app.services.chunk_service import CHUNKS_JSON_SUFFIX
        
        # First check if the file has the correct suffix
        if not filename.endswith(CHUNKS_JSON_SUFFIX):
            return False
        
        # Check if document_id appears directly in the filename
        if document_id in filename:
            return True
            
        # If document_id is not in the filename, try to load the file and check its metadata
        try:
            # We need to use the current directory being searched, not always self.chunks_dir
            # This will be handled by the calling function (_search_chunk_file_in_directory)
            # which passes the full filepath
            return False
        except Exception as e:
            self.logger.warning(f"Error checking chunk file metadata: {e}")
            
        return False
    
    def _parse_full_text(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """全文解析"""
        self.logger.debug("Parsing full text.") # Added log
        # 从分块数据中提取所有文本
        chunks = chunk_data.get("chunks", [])
        
        # 按照起始位置排序块
        sorted_chunks = sorted(chunks, key=lambda x: x.get("start_pos", 0))
        
        # 提取文档标题（假设第一个块的第一行是标题）
        title = ""
        if sorted_chunks:
            first_chunk = sorted_chunks[0]
            content = first_chunk.get("content", "")
            lines = content.split("\n")
            if lines:
                title = lines[0]
        
        # 构建段落列表
        paragraphs = []
        for i, chunk in enumerate(sorted_chunks):
            content = chunk.get("content", "")
            paras = [p for p in content.split("\n") if p.strip()]
            
            # 跳过第一个块的第一行（标题）
            start_idx = 1 if i == 0 else 0
            
            for j, para in enumerate(paras[start_idx:], start=start_idx):
                paragraphs.append({
                    "id": f"p{len(paragraphs)}",
                    "text": para
                })
        
        # 构建结构化内容
        return {
            "title": title,
            "sections": [
                {
                    "id": "section_1",
                    "title": "全文",
                    "level": 1,
                    "paragraphs": paragraphs
                }
            ]
        }
    
    def _parse_by_page(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """按页面解析"""
        self.logger.debug("Parsing by page.")
        
        chunks = chunk_data.get("chunks", [])
        
        # 按页面分组
        pages = self._group_chunks_by_page(chunks)
        
        # 提取文档标题
        title = self._extract_title_from_first_page(pages)
        
        # 构建章节列表（每页一个章节）
        sections = self._build_page_sections(pages)
        
        return {
            "title": title,
            "sections": sections
        }
    
    def _parse_by_heading(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """按标题结构解析"""
        self.logger.debug("Parsing by heading.")
        
        # 从分块数据中提取所有文本
        chunks = chunk_data.get("chunks", [])
        sorted_chunks = sorted(chunks, key=lambda x: x.get("start_pos", 0))
        
        # 提取文档标题
        title = self._extract_document_title(sorted_chunks)
        
        # 解析章节结构
        sections = self._parse_sections_by_heading(sorted_chunks)
        
        # 如果没有识别到任何章节，创建默认章节
        if not sections:
            sections = [self._create_default_section(sorted_chunks, title)]
        
        return {
            "title": title,
            "sections": sections
        }
    
    def _parse_text_and_tables(self, chunk_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        文本与表格混合解析，基于‘|’或制表符识别表格行
        """
        self.logger.debug("Parsing text and tables.") # Added log
        parsed = []
        for chunk in chunk_data.get("chunks", []):
            text = chunk.get("content", "")
            page = chunk.get("page")
            if '|' in text or '\t' in text:
                # 简单表格拆分
                rows = [row.strip().split('|') for row in text.splitlines() if '|' in row]
                df = pd.DataFrame(rows)
                parsed.append({"type": "table", "page": page, "content": df.to_dict(orient='records')})
            else:
                parsed.append({"type": "text", "page": page, "content": text})
        return parsed

    def _is_heading_level1(self, text: str) -> bool:
        """判断是否为一级标题"""
        # 以#开头
        if text.startswith("# "):
            return True
        
        # 全大写且较短
        if text.isupper() and len(text) < 50:
            return True
        
        # 数字开头的章节标题（如"1. 引言"）
        if re.match(r"^\d+\.?\s+\w+", text) and len(text) < 50:
            return True
        
        return False
    
    def _is_heading_level2(self, text: str) -> bool:
        """判断是否为二级标题"""
        # 以##开头
        if text.startswith("## "):
            return True
        
        # 数字开头的小节标题（如"1.1 背景"）
        if re.match(r"^\d+\.\d+\.?\s+\w+", text) and len(text) < 50:
            return True
        
        return False
    
    def _extract_tables(self, document_path: str) -> List[Dict[str, Any]]:
        """提取文档中的表格"""
        # 这里是简化的实现，实际应根据文件类型使用不同的方法
        self.logger.debug(f"Extracting tables from: {document_path}")
        file_ext = os.path.splitext(document_path)[1].lower()
        
        # 示例表格数据 - 合并重复的PDF和DOCX逻辑
        tables = []
        
        if file_ext in ['.pdf', '.docx']:
            # PDF和DOCX表格提取逻辑（当前为示例实现）
            tables.append({
                "id": "table_1",
                "section_id": "section_0",
                "caption": "表1：示例表格",
                "data": [
                    ["列1", "列2", "列3"],
                    ["数据1", "数据2", "数据3"],
                    ["数据4", "数据5", "数据6"]
                ]
            })
        
        return tables
    
    def _extract_images(self, document_path: str) -> List[Dict[str, Any]]:
        """提取文档中的图像"""
        # 这里是简化的实现，实际应根据文件类型使用不同的方法
        self.logger.debug(f"Extracting images from: {document_path}")
        file_ext = os.path.splitext(document_path)[1].lower()
        
        # 示例图像数据 - 合并重复的PDF和DOCX逻辑
        images = []
        
        if file_ext in ['.pdf', '.docx']:
            # PDF和DOCX图像提取逻辑（当前为示例实现）
            images.append({
                "id": "image_1",
                "section_id": "section_0",
                "caption": "图1：示例图像",
                "path": "/storage/images/placeholder.png"
            })
        
        return images

    def _validate_document_exists(self, document_id: str) -> str:
        """验证文档存在并返回文档路径"""
        document_path = self._find_document(document_id)
        if not document_path:
            self.logger.error(f"Document not found for ID: {document_id}")
            raise FileNotFoundError(f"找不到ID为{document_id}的文档")
        
        self.logger.debug(f"Document path: {document_path}")
        return document_path
    
    def _get_chunk_data(self, document_id: str, page_map: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取分块数据"""
        if page_map is not None:
            return self._create_chunk_data_from_page_map(page_map)
        
        # First try to find the chunk file
        chunk_file = self._find_chunk_file(document_id)
        if not chunk_file:
            self._handle_missing_chunk_file(document_id)
        
        # Now load the chunk data
        return self._load_chunk_file(chunk_file, document_id)
        
    def _create_chunk_data_from_page_map(self, page_map: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create chunk data from provided page map"""
        self.logger.info("Using provided page_map for parsing.")
        return {
            "chunks": [
                {
                    "content": p["text"], 
                    "page": p.get("page"),
                    "start_pos": None, 
                    "end_pos": None
                } for p in page_map
            ]
        }
        
    def _handle_missing_chunk_file(self, document_id: str) -> None:
        """Handle the case when chunk file is not found"""
        # Get search paths
        search_paths = self._get_chunk_search_paths()
        
        # Build error message
        error_msg = self._build_chunk_error_message(document_id, search_paths)
            
        self.logger.error(error_msg)
        raise FileNotFoundError(f"请先对文档ID {document_id} 进行分块处理 (Please chunk document ID {document_id} first)")
        
    def _get_chunk_search_paths(self) -> List[str]:
        """Get all the paths where we search for chunk files"""
        return [
            self.chunks_dir,
            os.path.join(self.storage_dir, 'backend', '02-chunked-docs'),
            os.path.join(self.storage_dir, '02-chunked-docs'),
            os.path.join(self.storage_dir, 'backend/02-chunked-docs')
        ]
        
    def _build_chunk_error_message(self, document_id: str, search_paths: List[str]) -> str:
        """Build detailed error message for missing chunk file"""
        error_msg = f"Chunk file not found for document ID: {document_id}. Please chunk the document first.\n"
        error_msg += "Locations searched:\n"
        
        # Add search paths to error message
        for path in search_paths:
            if os.path.exists(path):
                error_msg += f" - {path} (exists)\n"
            else:
                error_msg += f" - {path} (does not exist)\n"
        
        # Add information about files in chunks_dir
        if os.path.exists(self.chunks_dir):
            files = os.listdir(self.chunks_dir)
            error_msg += f"\nFiles in {self.chunks_dir} ({len(files)} files):\n"
            for i, f in enumerate(files[:10]):  # Show only first 10 files
                error_msg += f" - {f}\n"
            if len(files) > 10:
                error_msg += f" - ... and {len(files) - 10} more files\n"
        
        return error_msg
    
    def _load_chunk_file(self, chunk_file: str, document_id: str) -> Dict[str, Any]:
        """Load chunk data from file"""
        try:
            self.logger.info(f"Loading chunk data from: {chunk_file}")
            with open(chunk_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading chunk data from {chunk_file}: {str(e)}")
            raise FileNotFoundError(f"Error loading chunk data for document ID {document_id}: {str(e)}")
    
    def _create_metadata(self, document_path: str, chunk_data: Dict[str, Any], strategy: str, timestamp: str) -> Dict[str, Any]:
        """创建元数据"""
        # 提取文档名称（不带扩展名）
        filename = os.path.basename(document_path)
        document_name = os.path.splitext(filename)[0]
        
        # 如果文件名包含时间戳和ID，尝试提取原始名称
        parts = document_name.split('_')
        if len(parts) >= 3:
            # 检查倒数第二个部分是否为时间戳格式
            if len(parts[-2]) == 15 and parts[-2][8] == '_' and parts[-2][:8].isdigit() and parts[-2][9:].isdigit():
                # 倒数第三个部分以前为原始文件名
                document_name = '_'.join(parts[:-2])
        
        metadata = {
            "filename": filename,
            "document_name": document_name,
            "total_pages": len(set(c.get("page") for c in chunk_data.get("chunks", []))),
            "parsing_method": strategy,
            "timestamp": timestamp
        }
        self.logger.debug(f"Generated metadata: {metadata}")
        return metadata
    
    def _parse_content_by_strategy(self, strategy: str, chunk_data: Dict[str, Any]) -> Any:
        """根据策略解析内容"""
        strategy_map = {
            "full_text": self._parse_full_text,
            "by_page": self._parse_by_page,
            "by_heading": self._parse_by_heading,
            "text_and_tables": self._parse_text_and_tables
        }
        
        if strategy not in strategy_map:
            self.logger.error(f"Unsupported parsing strategy: {strategy}")
            raise ValueError(f"不支持的解析策略: {strategy}")
        
        return strategy_map[strategy](chunk_data)
    
    def _extract_media_content(self, document_path: str, extract_tables: bool, extract_images: bool) -> tuple:
        """提取表格和图像内容"""
        self.logger.info(f"Extract tables: {extract_tables}, Extract images: {extract_images}")
        tables = self._extract_tables(document_path) if extract_tables else []
        images = self._extract_images(document_path) if extract_images else []
        return tables, images
    
    def _build_parse_result(self, metadata: Dict[str, Any], parsed_content: Any, tables: List, images: List) -> Dict[str, Any]:
        """构建解析结果"""
        result = {
            "metadata": metadata,
            "content": parsed_content
        }
        if tables:
            result["tables"] = tables
        if images:
            result["images"] = images
        return result
    
    def _calculate_content_statistics(self, strategy: str, parsed_content: Any, tables: List, images: List) -> Dict[str, int]:
        """计算内容统计数据"""
        total_paragraphs = 0
        total_sections = 0
        
        if strategy in ["full_text", "by_page", "by_heading"]:
            if isinstance(parsed_content, dict) and "sections" in parsed_content:
                total_sections = len(parsed_content["sections"])
                for section in parsed_content["sections"]:
                    total_paragraphs += len(section.get("paragraphs", []))
                    for subsection in section.get("subsections", []):
                        total_sections += 1
                        total_paragraphs += len(subsection.get("paragraphs", []))
        elif strategy == "text_and_tables":
            total_paragraphs = sum(1 for item in parsed_content if item.get("type") == "text")

        total_tables = len(tables)
        if strategy == "text_and_tables":
            total_tables += sum(1 for item in parsed_content if item.get("type") == "table")

        return {
            "total_sections": total_sections,
            "total_paragraphs": total_paragraphs,
            "total_tables": total_tables,
            "total_images": len(images)
        }
    
    def _save_parse_result(self, document_id: str, timestamp: str, result: Dict[str, Any]) -> str:
        """保存解析结果文件"""
        # 从元数据中获取文档名称
        document_name = result.get("metadata", {}).get("document_name", "")
        
        # 使用文档名称和ID生成文件名
        if document_name:
            result_file = f"{document_name}_{document_id}_{timestamp}_parsed.json"
        else:
            result_file = f"{document_id}_{timestamp}_parsed.json"
            
        result_path = os.path.join(self.parsed_dir, result_file)
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Successfully parsed document {document_id}. Result saved to: {result_path}")
        return result_file
    
    def _build_final_response(self, document_id: str, parse_id: str, strategy: str, timestamp: str,
                             result_file: str, stats: Dict[str, int], parsed_content: Any) -> Dict[str, Any]:
        """构建最终响应"""
        # 从文件名中提取文档名称（如果存在）
        document_name = ""
        if "_" in result_file:
            parts = result_file.split('_')
            if len(parts) > 2:  # 确保至少有文档名_ID_时间戳格式
                # 文档名在倒数第三个部分之前
                document_id_index = -3
                # 检查文档ID是否在文件名中
                for i, part in enumerate(parts):
                    if part == document_id:
                        document_id_index = i
                        break
                # 文档名是ID之前的所有部分
                if document_id_index > 0:
                    document_name = "_".join(parts[:document_id_index])
                
        return {
            "document_id": document_id,
            "document_name": document_name,
            "parse_id": parse_id,
            "strategy": strategy,
            "timestamp": timestamp,
            "result_file": result_file,
            "total_sections": stats["total_sections"],
            "total_paragraphs": stats["total_paragraphs"],
            "total_tables": stats["total_tables"],
            "total_images": stats["total_images"],
            "message": f"文档解析成功，已存储为 {result_file}",
            "parsed_content": self._get_sample_content(parsed_content, strategy)
        }
    
    def _extract_document_title(self, sorted_chunks):
        """提取文档标题"""
        if not sorted_chunks:
            return ""
        
        first_chunk = sorted_chunks[0]
        content = first_chunk.get("content", "")
        lines = content.split("\n")
        return lines[0] if lines else ""
    
    def _parse_sections_by_heading(self, sorted_chunks):
        """解析章节结构"""
        sections = []
        current_section = None
        current_subsection = None
        
        for chunk in sorted_chunks:
            content = chunk.get("content", "")
            lines = content.split("\n")
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if self._is_heading_level1(line):
                    current_section, current_subsection = self._handle_level1_heading(
                        line, sections, current_section)
                elif current_section and self._is_heading_level2(line):
                    current_subsection = self._handle_level2_heading(
                        line, current_section, len(sections))
                elif current_section:
                    self._add_paragraph_to_section(
                        line, current_section, current_subsection, len(sections))
        
        # 添加最后一个章节
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _handle_level1_heading(self, line, sections, current_section):
        """处理一级标题"""
        # 保存前一个章节
        if current_section:
            sections.append(current_section)
        
        # 创建新章节
        new_section = {
            "id": f"section_{len(sections)}",
            "title": line,
            "level": 1,
            "paragraphs": [],
            "subsections": []
        }
        return new_section, None
    
    def _handle_level2_heading(self, line, current_section, section_count):
        """处理二级标题"""
        subsection = {
            "id": f"section_{section_count}_{len(current_section['subsections'])}",
            "title": line,
            "level": 2,
            "paragraphs": []
        }
        current_section["subsections"].append(subsection)
        return subsection
    
    def _add_paragraph_to_section(self, line, current_section, current_subsection, section_count):
        """添加段落到章节"""
        if current_subsection:
            subsection_index = len(current_section['subsections']) - 1
            paragraph_count = len(current_subsection['paragraphs'])
            current_subsection["paragraphs"].append({
                "id": f"p{section_count}_{subsection_index}_{paragraph_count}",
                "text": line
            })
        else:
            paragraph_count = len(current_section['paragraphs'])
            current_section["paragraphs"].append({
                "id": f"p{section_count}_{paragraph_count}",
                "text": line
            })
    
    def _create_default_section(self, sorted_chunks, title):
        """创建默认章节"""
        paragraphs = []
        for i, chunk in enumerate(sorted_chunks):
            content = chunk.get("content", "")
            paras = [p for p in content.split("\n") if p.strip()]
            
            # 跳过第一个块的第一行（标题）
            start_idx = 1 if i == 0 else 0
            
            for para in paras[start_idx:]:
                paragraphs.append({
                    "id": f"p{len(paragraphs)}",
                    "text": para
                })
        
        return {
            "id": "section_0",
            "title": "文档内容",
            "level": 1,
            "paragraphs": paragraphs,
            "subsections": []
        }
    
    def _group_chunks_by_page(self, chunks):
        """按页面分组chunks"""
        pages = {}
        for chunk in chunks:
            page_num = chunk.get("page", 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(chunk)
        return pages
    
    def _extract_title_from_first_page(self, pages):
        """从第一页提取文档标题"""
        if 1 not in pages or not pages[1]:
            return ""
        
        first_chunk = sorted(pages[1], key=lambda x: x.get("start_pos", 0))[0]
        content = first_chunk.get("content", "")
        lines = content.split("\n")
        return lines[0] if lines else ""
    
    def _build_page_sections(self, pages):
        """构建页面章节列表"""
        sections = []
        for page_num in sorted(pages.keys()):
            page_chunks = sorted(pages[page_num], key=lambda x: x.get("start_pos", 0))
            paragraphs = self._build_page_paragraphs(page_chunks, page_num)
            
            sections.append({
                "id": f"section_{page_num}",
                "title": f"第 {page_num} 页",
                "level": 1,
                "paragraphs": paragraphs
            })
        return sections
    
    def _build_page_paragraphs(self, page_chunks, page_num):
        """构建页面段落列表"""
        paragraphs = []
        for i, chunk in enumerate(page_chunks):
            content = chunk.get("content", "")
            paras = [p for p in content.split("\n") if p.strip()]
            
            # 跳过第一页第一个块的第一行（标题）
            start_idx = 1 if page_num == 1 and i == 0 else 0
            
            for para in paras[start_idx:]:
                paragraphs.append({
                    "id": f"p{page_num}_{len(paragraphs)}",
                    "text": para
                })
        return paragraphs
