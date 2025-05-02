import os
import json
import datetime
import uuid
from typing import List, Dict, Any, Optional

class ChunkService:
    """文档分块服务，支持按字数、段落、标题等策略进行切分"""
    
    def __init__(self, documents_dir="storage/documents", chunks_dir="storage/chunks"):
        self.documents_dir = documents_dir
        self.chunks_dir = chunks_dir
        os.makedirs(chunks_dir, exist_ok=True)
    
    def create_chunks(self, document_id: str, strategy: str, chunk_size: int = 1000, overlap: int = 200) -> Dict[str, Any]:
        """
        根据指定策略将文档分块
        
        参数:
            document_id: 文档ID
            strategy: 分块策略 ("char_count", "paragraph", "heading")
            chunk_size: 块大小（字符数）
            overlap: 重叠大小（字符数）
        
        返回:
            包含分块结果的字典
        """
        # 检查文档是否存在
        document_path = self._find_document(document_id)
        if not document_path:
            raise FileNotFoundError(f"找不到ID为{document_id}的文档")
        
        # 读取文档内容
        file_ext = os.path.splitext(document_path)[1].lower()
        text_content = self._extract_text(document_path, file_ext)
        
        # 根据策略分块
        chunks = []
        if strategy == "char_count":
            chunks = self._chunk_by_char_count(text_content, chunk_size, overlap)
        elif strategy == "paragraph":
            chunks = self._chunk_by_paragraph(text_content, chunk_size, overlap)
        elif strategy == "heading":
            chunks = self._chunk_by_heading(text_content, chunk_size, overlap)
        else:
            raise ValueError(f"不支持的分块策略: {strategy}")
        
        # 生成唯一ID和时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        chunk_id = str(uuid.uuid4())[:8]
        
        # 为每个块添加元数据
        for i, chunk in enumerate(chunks):
            chunk["chunk_id"] = f"{chunk_id}_{i}"
            chunk["document_id"] = document_id
            
        # 保存分块结果
        result = {
            "document_id": document_id,
            "chunk_id": chunk_id,
            "timestamp": timestamp,
            "strategy": strategy,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "total_chunks": len(chunks),
            "chunks": chunks
        }
        
        result_file = f"{document_id}_{timestamp}_chunks.json"
        result_path = os.path.join(self.chunks_dir, result_file)
        
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return {
            "document_id": document_id,
            "chunk_id": chunk_id,
            "timestamp": timestamp,
            "strategy": strategy,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "total_chunks": len(chunks),
            "result_file": result_file
        }
    
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """获取指定文档的所有分块结果"""
        chunk_files = []
        
        if os.path.exists(self.chunks_dir):
            for filename in os.listdir(self.chunks_dir):
                if filename.startswith(document_id) and filename.endswith("_chunks.json"):
                    file_path = os.path.join(self.chunks_dir, filename)
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        chunk_data = json.load(f)
                    
                    chunk_files.append({
                        "file": filename,
                        "path": file_path,
                        "timestamp": chunk_data.get("timestamp", ""),
                        "strategy": chunk_data.get("strategy", ""),
                        "total_chunks": chunk_data.get("total_chunks", 0)
                    })
        
        return chunk_files
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """获取指定ID的分块结果"""
        if os.path.exists(self.chunks_dir):
            for filename in os.listdir(self.chunks_dir):
                if filename.endswith("_chunks.json"):
                    file_path = os.path.join(self.chunks_dir, filename)
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        chunk_data = json.load(f)
                        
                    # 检查是否包含指定ID的块
                    if chunk_data.get("chunk_id") == chunk_id:
                        return chunk_data
                    
                    # 检查子块
                    for chunk in chunk_data.get("chunks", []):
                        if chunk.get("chunk_id") == chunk_id:
                            return chunk
        
        return None
    
    def _find_document(self, document_id: str) -> Optional[str]:
        """查找指定ID的文档路径"""
        if os.path.exists(self.documents_dir):
            for filename in os.listdir(self.documents_dir):
                if document_id in filename:
                    return os.path.join(self.documents_dir, filename)
        return None
    
    def _extract_text(self, file_path: str, file_ext: str) -> str:
        """从文档中提取文本内容"""
        if file_ext == '.pdf':
            return self._extract_text_from_pdf(file_path)
        elif file_ext == '.docx':
            return self._extract_text_from_docx(file_path)
        elif file_ext in ['.txt', '.md']:
            return self._extract_text_from_text_file(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """从PDF文件中提取文本"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            raise Exception(f"PDF文本提取失败: {str(e)}")
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """从DOCX文件中提取文本"""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            raise Exception(f"DOCX文本提取失败: {str(e)}")
    
    def _extract_text_from_text_file(self, file_path: str) -> str:
        """从文本文件中提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"文本文件读取失败: {str(e)}")
    
    def _chunk_by_char_count(self, text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """按字符数分块"""
        chunks = []
        
        # 确保重叠不超过块大小
        if overlap >= chunk_size:
            overlap = chunk_size // 2
        
        # 计算起始位置
        start_positions = list(range(0, len(text), chunk_size - overlap))
        
        for i, start in enumerate(start_positions):
            # 计算结束位置
            end = min(start + chunk_size, len(text))
            
            # 如果是最后一个块且太小，则合并到前一个块
            if end == len(text) and end - start < chunk_size // 2 and i > 0:
                continue
            
            # 提取文本块
            chunk_text = text[start:end]
            
            # 估计页码（简化处理）
            estimated_page = i // 3 + 1  # 假设每页约3个块
            
            chunks.append({
                "content": chunk_text,
                "start_pos": start,
                "end_pos": end,
                "page": estimated_page
            })
            
            # 如果已经到达文本末尾，结束循环
            if end == len(text):
                break
        
        return chunks
    
    def _chunk_by_paragraph(self, text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """按段落分块"""
        # 分割段落
        paragraphs = [p for p in text.split('\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        current_start = 0
        start_pos = 0
        
        for para in paragraphs:
            # 如果添加这个段落会超过块大小，且当前块不为空，则保存当前块
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                # 估计页码
                estimated_page = len(chunks) // 3 + 1  # 假设每页约3个块
                
                chunks.append({
                    "content": current_chunk,
                    "start_pos": start_pos,
                    "end_pos": start_pos + len(current_chunk),
                    "page": estimated_page
                })
                
                # 计算新的起始位置，考虑重叠
                overlap_chars = min(overlap, len(current_chunk))
                current_start = current_start + len(current_chunk) - overlap_chars
                start_pos = current_start
                
                # 重置当前块，可能包含前一个块的结尾（重叠部分）
                if overlap_chars > 0:
                    current_chunk = current_chunk[-overlap_chars:] + "\n" + para
                else:
                    current_chunk = para
            else:
                # 添加段落到当前块
                if current_chunk:
                    current_chunk += "\n" + para
                else:
                    current_chunk = para
        
        # 添加最后一个块
        if current_chunk:
            estimated_page = len(chunks) // 3 + 1
            chunks.append({
                "content": current_chunk,
                "start_pos": start_pos,
                "end_pos": start_pos + len(current_chunk),
                "page": estimated_page
            })
        
        return chunks
    
    def _chunk_by_heading(self, text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """按标题分块"""
        # 简单的标题检测（以#开头的行或者全大写的短行）
        lines = text.split('\n')
        sections = []
        current_section = {"title": "", "content": ""}
        
        for line in lines:
            # 检测是否为标题
            is_heading = (line.startswith('#') or 
                         (line.isupper() and len(line) < 100 and line.strip()))
            
            if is_heading:
                # 保存前一个章节
                if current_section["content"]:
                    sections.append(current_section)
                
                # 开始新章节
                current_section = {"title": line, "content": ""}
            else:
                # 添加内容到当前章节
                if current_section["content"]:
                    current_section["content"] += "\n" + line
                else:
                    current_section["content"] = line
        
        # 添加最后一个章节
        if current_section["content"]:
            sections.append(current_section)
        
        # 将章节转换为块
        chunks = []
        start_pos = 0
        
        for i, section in enumerate(sections):
            section_text = section["title"] + "\n" + section["content"]
            
            # 如果章节太大，进一步分块
            if len(section_text) > chunk_size:
                # 使用字符分块方法处理大章节
                sub_chunks = self._chunk_by_char_count(section_text, chunk_size, overlap)
                
                # 调整起始位置
                for sub_chunk in sub_chunks:
                    sub_chunk["start_pos"] += start_pos
                    sub_chunk["end_pos"] += start_pos
                    sub_chunk["page"] = i + 1  # 假设每个章节对应一页
                
                chunks.extend(sub_chunks)
            else:
                # 章节足够小，直接作为一个块
                chunks.append({
                    "content": section_text,
                    "start_pos": start_pos,
                    "end_pos": start_pos + len(section_text),
                    "page": i + 1  # 假设每个章节对应一页
                })
            
            # 更新起始位置
            start_pos += len(section_text) + 1  # +1 for newline
        
        return chunks
