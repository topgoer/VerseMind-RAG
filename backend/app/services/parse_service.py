import os
import json
import datetime
import uuid
from typing import Dict, List, Any, Optional
import re
import logging  # added for logging
import pandas as pd  # added for table parsing

class ParseService:
    """文档解析服务，支持全文、分页、标题结构解析"""
    
    def __init__(self):
        # Update directories according to the naming convention
        self.storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.documents_dir = os.path.join(self.storage_dir, 'storage', 'documents')
        # Fix paths to use backend directory structure
        self.chunks_dir = os.path.join(self.storage_dir, 'backend', '02-chunked-docs')
        self.parsed_dir = os.path.join(self.storage_dir, 'backend', '03-parsed-docs')
        
        # Create directories if they don't exist
        os.makedirs(self.documents_dir, exist_ok=True)
        os.makedirs(self.chunks_dir, exist_ok=True)
        os.makedirs(self.parsed_dir, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"ParseService initialized. Documents_dir: {self.documents_dir}, Chunks_dir: {self.chunks_dir}, Parsed_dir: {self.parsed_dir}") # Added log

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
        self.logger.info(f"Starting parse_document for document_id: {document_id} with strategy: {strategy}") # Added log
        # 检查文档是否存在
        document_path = self._find_document(document_id)
        if not document_path:
            self.logger.error(f"Document not found for ID: {document_id}") # Added log
            raise FileNotFoundError(f"找不到ID为{document_id}的文档")
        
        self.logger.debug(f"Document path: {document_path}") # Added log

        # 读取分块数据或使用 page_map
        if page_map is not None:
            self.logger.info("Using provided page_map for parsing.") # Added log
            chunk_data = {"chunks": [{"content": p["text"], "page": p.get("page"),
                                       "start_pos": None, "end_pos": None} for p in page_map]}
        else:
            chunk_file = self._find_chunk_file(document_id)
            if not chunk_file:
                self.logger.error(f"Chunk file not found for document ID: {document_id}. Please chunk the document first.") # Added log
                raise FileNotFoundError(f"请先对文档ID {document_id} 进行分块处理")
            self.logger.info(f"Loading chunk data from: {chunk_file}") # Added log
            with open(chunk_file, "r", encoding="utf-8") as f:
                chunk_data = json.load(f)

        # 生成唯一ID和时间戳，准备 metadata
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        parse_id = str(uuid.uuid4())[:8]
        metadata = {
            "filename": os.path.basename(document_path),
            "total_pages": len(set(c.get("page") for c in chunk_data.get("chunks", []))),
            "parsing_method": strategy,
            "timestamp": timestamp
        }
        self.logger.debug(f"Generated metadata: {metadata}") # Added log

        # 根据策略解析文档
        if strategy == "full_text":
            parsed_content = self._parse_full_text(chunk_data)
        elif strategy == "by_page":
            parsed_content = self._parse_by_page(chunk_data)
        elif strategy == "by_heading":
            parsed_content = self._parse_by_heading(chunk_data)
        elif strategy == "text_and_tables":
            parsed_content = self._parse_text_and_tables(chunk_data)
        else:
            self.logger.error(f"Unsupported parsing strategy: {strategy}") # Added log
            raise ValueError(f"不支持的解析策略: {strategy}")

        # 可选：提取表格或图像
        self.logger.info(f"Extract tables: {extract_tables}, Extract images: {extract_images}") # Added log
        tables = self._extract_tables(document_path) if extract_tables else []
        images = self._extract_images(document_path) if extract_images else []

        # 构建响应结构，包含 metadata 和 content
        result = {
            "metadata": metadata,
            "content": parsed_content
        }
        if tables:
            result["tables"] = tables
        if images:
            result["images"] = images

        # 获取段落、表格和图像的统计数据
        total_paragraphs = 0
        total_sections = 0
        
        # 计算段落和章节总数
        if strategy in ["full_text", "by_page", "by_heading"]:
            if isinstance(parsed_content, dict) and "sections" in parsed_content:
                total_sections = len(parsed_content["sections"])
                for section in parsed_content["sections"]:
                    total_paragraphs += len(section.get("paragraphs", []))
                    # Count subsections if they exist
                    for subsection in section.get("subsections", []):
                        total_sections += 1
                        total_paragraphs += len(subsection.get("paragraphs", []))
        elif strategy == "text_and_tables":
            # 文本与表格混合解析的情况
            total_paragraphs = sum(1 for item in parsed_content if item.get("type") == "text")

        # 计算表格总数
        total_tables = len(tables)
        if strategy == "text_and_tables":
            total_tables += sum(1 for item in parsed_content if item.get("type") == "table")

        # 保存解析结果文件
        result_file = f"{document_id}_{timestamp}_parsed.json"
        result_path = os.path.join(self.parsed_dir, result_file)
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Successfully parsed document {document_id}. Result saved to: {result_path}") # Added log
        
        # 返回详细的解析结果，包括前端需要展示的数据
        parsed_result = {
            "document_id": document_id,
            "parse_id": parse_id,
            "strategy": strategy,
            "timestamp": timestamp,
            "result_file": result_file,
            "total_sections": total_sections,
            "total_paragraphs": total_paragraphs,
            "total_tables": total_tables,
            "total_images": len(images),
            "message": f"文档解析成功，已存储为 {result_file}",
            "parsed_content": self._get_sample_content(parsed_content, strategy)
        }
        return parsed_result

    def _get_sample_content(self, parsed_content, strategy, max_items=10):
        """获取解析内容的样本，用于前端展示"""
        sample = []
        
        if strategy in ["full_text", "by_page", "by_heading"]:
            if isinstance(parsed_content, dict):
                # 添加标题
                if "title" in parsed_content and parsed_content["title"]:
                    sample.append({
                        "type": "heading",
                        "level": 1,
                        "text": parsed_content["title"]
                    })
                
                # 添加部分章节的标题和段落
                for i, section in enumerate(parsed_content.get("sections", [])):
                    if i >= max_items // 2:
                        break
                    
                    # 添加章节标题
                    sample.append({
                        "type": "heading",
                        "level": section.get("level", 1),
                        "text": section.get("title", f"Section {i+1}")
                    })
                    
                    # 添加部分段落
                    paragraphs = section.get("paragraphs", [])
                    for j, para in enumerate(paragraphs):
                        if j >= 2:  # 每节最多2段
                            break
                        sample.append({
                            "type": "paragraph",
                            "text": para.get("text", "")
                        })
                    
                    # 添加部分子章节
                    for k, subsection in enumerate(section.get("subsections", [])):
                        if k >= 1:  # 每节最多1个子节
                            break
                        
                        # 添加子章节标题
                        sample.append({
                            "type": "heading",
                            "level": subsection.get("level", 2),
                            "text": subsection.get("title", f"Subsection {i+1}.{k+1}")
                        })
                        
                        # 添加部分段落
                        sub_paragraphs = subsection.get("paragraphs", [])
                        for l, para in enumerate(sub_paragraphs):
                            if l >= 1:  # 每子节最多1段
                                break
                            sample.append({
                                "type": "paragraph",
                                "text": para.get("text", "")
                            })
        
        elif strategy == "text_and_tables":
            # 文本与表格混合解析的情况
            for i, item in enumerate(parsed_content):
                if i >= max_items:
                    break
                
                if item.get("type") == "text":
                    sample.append({
                        "type": "paragraph",
                        "text": item.get("content", "").strip()[:200]  # 限制长度
                    })
                elif item.get("type") == "table":
                    sample.append({
                        "type": "table",
                        "text": "表格数据"  # 简化表格表示
                    })
        
        return sample

    def list_parsed(self, document_id: str):
        """
        列出指定文档的所有解析结果
        """
        self.logger.info(f"Listing parsed results for document_id: {document_id} in directory: {self.parsed_dir}") # Added log
        parsed_dir = self.parsed_dir
        os.makedirs(parsed_dir, exist_ok=True)
        results = []
        for fname in os.listdir(parsed_dir):
            if fname.startswith(document_id) and fname.endswith(".json"):
                with open(os.path.join(parsed_dir, fname), "r", encoding="utf-8") as f:
                    results.append(json.load(f))
        self.logger.info(f"Found {len(results)} parsed files for document_id: {document_id}") # Added log
        return results

    def _find_document(self, document_id: str) -> Optional[str]:
        """查找指定ID的文档路径"""
        self.logger.debug(f"Searching for document with ID: {document_id} in {self.documents_dir}") # Added log
        if os.path.exists(self.documents_dir):
            for filename in os.listdir(self.documents_dir):
                if document_id in filename:
                    self.logger.debug(f"Found document: {filename}") # Added log
                    return os.path.join(self.documents_dir, filename)
        self.logger.warning(f"Document with ID: {document_id} not found in {self.documents_dir}") # Added log
        return None
    
    def _find_chunk_file(self, document_id: str) -> Optional[str]:
        """查找指定文档的分块文件"""
        self.logger.debug(f"Searching for chunk file for document ID: {document_id} in {self.chunks_dir}") # Added log
        if os.path.exists(self.chunks_dir):
            for filename in os.listdir(self.chunks_dir):
                if filename.startswith(document_id) and filename.endswith("_chunks.json"):
                    self.logger.debug(f"Found chunk file: {filename}") # Added log
                    return os.path.join(self.chunks_dir, filename)
        self.logger.warning(f"Chunk file for document ID: {document_id} not found in {self.chunks_dir}") # Added log
        return None
    
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
        self.logger.debug("Parsing by page.") # Added log
        # 从分块数据中提取所有文本
        chunks = chunk_data.get("chunks", [])
        
        # 按页面分组
        pages = {}
        for chunk in chunks:
            page_num = chunk.get("page", 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(chunk)
        
        # 提取文档标题（假设第一页的第一个块的第一行是标题）
        title = ""
        if 1 in pages and pages[1]:
            first_chunk = sorted(pages[1], key=lambda x: x.get("start_pos", 0))[0]
            content = first_chunk.get("content", "")
            lines = content.split("\n")
            if lines:
                title = lines[0]
        
        # 构建章节列表（每页一个章节）
        sections = []
        for page_num in sorted(pages.keys()):
            page_chunks = sorted(pages[page_num], key=lambda x: x.get("start_pos", 0))
            
            # 构建段落列表
            paragraphs = []
            for i, chunk in enumerate(page_chunks):
                content = chunk.get("content", "")
                paras = [p for p in content.split("\n") if p.strip()]
                
                # 跳过第一页第一个块的第一行（标题）
                start_idx = 1 if page_num == 1 and i == 0 else 0
                
                for j, para in enumerate(paras[start_idx:], start=start_idx):
                    paragraphs.append({
                        "id": f"p{page_num}_{len(paragraphs)}",
                        "text": para
                    })
            
            sections.append({
                "id": f"section_{page_num}",
                "title": f"第 {page_num} 页",
                "level": 1,
                "paragraphs": paragraphs
            })
        
        # 构建结构化内容
        return {
            "title": title,
            "sections": sections
        }
    
    def _parse_by_heading(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """按标题结构解析"""
        self.logger.debug("Parsing by heading.") # Added log
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
        
        # 识别标题和内容
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
                
                # 检测是否为一级标题
                if self._is_heading_level1(line):
                    # 保存前一个章节
                    if current_section:
                        sections.append(current_section)
                    
                    # 创建新章节
                    current_section = {
                        "id": f"section_{len(sections)}",
                        "title": line,
                        "level": 1,
                        "paragraphs": [],
                        "subsections": []
                    }
                    current_subsection = None
                
                # 检测是否为二级标题
                elif current_section and self._is_heading_level2(line):
                    # 创建新的子章节
                    current_subsection = {
                        "id": f"section_{len(sections)}_{len(current_section['subsections'])}",
                        "title": line,
                        "level": 2,
                        "paragraphs": []
                    }
                    current_section["subsections"].append(current_subsection)
                
                # 普通段落
                elif current_section:
                    if current_subsection:
                        current_subsection["paragraphs"].append({
                            "id": f"p{len(sections)}_{len(current_section['subsections'])-1}_{len(current_subsection['paragraphs'])}",
                            "text": line
                        })
                    else:
                        current_section["paragraphs"].append({
                            "id": f"p{len(sections)}_{len(current_section['paragraphs'])}",
                            "text": line
                        })
        
        # 添加最后一个章节
        if current_section:
            sections.append(current_section)
        
        # 如果没有识别到任何章节，创建一个默认章节
        if not sections:
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
            
            sections.append({
                "id": "section_0",
                "title": "文档内容",
                "level": 1,
                "paragraphs": paragraphs,
                "subsections": []
            })
        
        # 构建结构化内容
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
        self.logger.debug(f"Extracting tables from: {document_path}") # Added log
        file_ext = os.path.splitext(document_path)[1].lower()
        
        # 示例表格数据
        tables = []
        
        if file_ext == '.pdf':
            # PDF表格提取逻辑
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
        elif file_ext == '.docx':
            # DOCX表格提取逻辑
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
        self.logger.debug(f"Extracting images from: {document_path}") # Added log
        file_ext = os.path.splitext(document_path)[1].lower()
        
        # 示例图像数据
        images = []
        
        if file_ext == '.pdf':
            # PDF图像提取逻辑
            images.append({
                "id": "image_1",
                "section_id": "section_0",
                "caption": "图1：示例图像",
                "path": "/storage/images/placeholder.png"
            })
        elif file_ext == '.docx':
            # DOCX图像提取逻辑
            images.append({
                "id": "image_1",
                "section_id": "section_0",
                "caption": "图1：示例图像",
                "path": "/storage/images/placeholder.png"
            })
        
        return images
