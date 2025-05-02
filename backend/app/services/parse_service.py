import os
import json
import datetime
import uuid
from typing import Dict, List, Any, Optional
import re

class ParseService:
    """文档解析服务，支持全文、分页、标题结构解析"""
    
    def __init__(self, documents_dir="storage/documents", chunks_dir="storage/chunks"):
        self.documents_dir = documents_dir
        self.chunks_dir = chunks_dir
        os.makedirs(chunks_dir, exist_ok=True)
    
    def parse_document(self, document_id: str, strategy: str, extract_tables: bool = False, extract_images: bool = False) -> Dict[str, Any]:
        """
        解析文档结构
        
        参数:
            document_id: 文档ID
            strategy: 解析策略 ("full_text", "by_page", "by_heading")
            extract_tables: 是否提取表格
            extract_images: 是否提取图像
        
        返回:
            包含解析结果的字典
        """
        # 检查文档是否存在
        document_path = self._find_document(document_id)
        if not document_path:
            raise FileNotFoundError(f"找不到ID为{document_id}的文档")
        
        # 检查是否已有分块
        chunk_file = self._find_chunk_file(document_id)
        if not chunk_file:
            raise FileNotFoundError(f"请先对文档ID {document_id} 进行分块处理")
        
        # 读取分块数据
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunk_data = json.load(f)
        
        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        parse_id = str(uuid.uuid4())[:8]
        
        # 根据策略解析文档
        parsed_content = {}
        if strategy == "full_text":
            parsed_content = self._parse_full_text(chunk_data)
        elif strategy == "by_page":
            parsed_content = self._parse_by_page(chunk_data)
        elif strategy == "by_heading":
            parsed_content = self._parse_by_heading(chunk_data)
        else:
            raise ValueError(f"不支持的解析策略: {strategy}")
        
        # 提取表格（如果需要）
        tables = []
        if extract_tables:
            tables = self._extract_tables(document_path)
        
        # 提取图像（如果需要）
        images = []
        if extract_images:
            images = self._extract_images(document_path)
        
        # 构建完整的解析结果
        result = {
            "document_id": document_id,
            "parse_id": parse_id,
            "timestamp": timestamp,
            "strategy": strategy,
            "extract_tables": extract_tables,
            "extract_images": extract_images,
            "structure": parsed_content
        }
        
        if tables:
            result["tables"] = tables
        
        if images:
            result["images"] = images
        
        # 保存解析结果
        result_file = f"{document_id}_{timestamp}_parsed.json"
        result_path = os.path.join(self.chunks_dir, result_file)
        
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return {
            "document_id": document_id,
            "parse_id": parse_id,
            "timestamp": timestamp,
            "strategy": strategy,
            "extract_tables": extract_tables,
            "extract_images": extract_images,
            "result_file": result_file
        }
    
    def _find_document(self, document_id: str) -> Optional[str]:
        """查找指定ID的文档路径"""
        if os.path.exists(self.documents_dir):
            for filename in os.listdir(self.documents_dir):
                if document_id in filename:
                    return os.path.join(self.documents_dir, filename)
        return None
    
    def _find_chunk_file(self, document_id: str) -> Optional[str]:
        """查找指定文档的分块文件"""
        if os.path.exists(self.chunks_dir):
            for filename in os.listdir(self.chunks_dir):
                if filename.startswith(document_id) and filename.endswith("_chunks.json"):
                    return os.path.join(self.chunks_dir, filename)
        return None
    
    def _parse_full_text(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """全文解析"""
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
