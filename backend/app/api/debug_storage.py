from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import json
from app.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()

@router.get("/search-results/{filename}")
async def get_search_results(filename: str) -> Dict[str, Any]:
    """获取特定的搜索结果文件内容"""
    try:
        results_dir = search_service.results_dir
        search_file_path = os.path.join(results_dir, filename)
        
        if not os.path.exists(search_file_path):
            raise HTTPException(status_code=404, detail=f"搜索结果文件不存在: {filename}")
            
        try:
            with open(search_file_path, 'r', encoding='utf-8') as f:
                search_data = json.load(f)
                return search_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取搜索结果文件失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索结果失败: {str(e)}")

@router.get("/storage-info")
async def get_storage_info() -> Dict[str, Any]:
    """获取系统中各种向量数据库和嵌入向量的存储位置信息"""
    try:
        # 获取基础存储目录
        indices_dir = search_service.indices_dir
        embeddings_dir = search_service.embeddings_dir
        results_dir = search_service.results_dir
          # 获取默认相似度阈值设置
        default_similarity_threshold = 0.5  # 默认值设置为0.5，避免过于严格的匹配要求
          # 尝试从最近的搜索结果中获取实际的相似度阈值
        recent_search_file = None
        if os.path.exists(results_dir):
            SEARCH_PREFIX = "search_"
            JSON_EXT = ".json"
            search_files = [f for f in os.listdir(results_dir) 
                           if f.startswith(SEARCH_PREFIX) and f.endswith(JSON_EXT)]
            if search_files:
                # 按时间戳排序获取最新的搜索结果
                search_files.sort(reverse=True)
                recent_search_file = os.path.join(results_dir, search_files[0])
                try:
                    with open(recent_search_file, 'r', encoding='utf-8') as f:
                        search_data = json.load(f)
                        if 'similarity_threshold' in search_data:
                            default_similarity_threshold = search_data['similarity_threshold']
                except Exception as e:
                    print(f"读取最近搜索结果文件失败: {e}")
        
        # 添加调试日志
        print(f"DEBUG: indices_dir: {indices_dir}")
        print(f"DEBUG: embeddings_dir: {embeddings_dir}")
        print(f"DEBUG: results_dir: {results_dir}")
        
        # 获取向量数据库特定目录
        vector_db_paths = {}
        
        # FAISS 数据库路径
        faiss_dir = os.path.join(indices_dir, "faiss")
        if os.path.exists(faiss_dir):
            vector_db_paths["FAISS"] = faiss_dir
        
        # Chroma 数据库路径 
        chroma_dir = os.path.join(indices_dir, "chroma")
        if os.path.exists(chroma_dir):
            vector_db_paths["Chroma"] = chroma_dir
              # 统计索引文件数量
        total_indices = 0
        if os.path.exists(indices_dir):
            for filename in os.listdir(indices_dir):
                if filename.endswith(".json"):
                    total_indices += 1
        
        # 统计嵌入文件数量
        total_embeddings = 0
        if os.path.exists(embeddings_dir):
            for filename in os.listdir(embeddings_dir):
                if filename.endswith(".json"):
                    total_embeddings += 1
                    
        # 检查向量数据库目录是否存在
        print(f"DEBUG: 检查FAISS目录是否存在: {os.path.join(indices_dir, 'faiss')}, 结果: {os.path.exists(os.path.join(indices_dir, 'faiss'))}")
        print(f"DEBUG: 检查Chroma目录是否存在: {os.path.join(indices_dir, 'chroma')}, 结果: {os.path.exists(os.path.join(indices_dir, 'chroma'))}")
        # 尝试列出向量数据库目录下的文件
        try:
            if os.path.exists(os.path.join(indices_dir, "faiss")):
                print(f"DEBUG: FAISS目录内容: {os.listdir(os.path.join(indices_dir, 'faiss'))}")
            if os.path.exists(os.path.join(indices_dir, "chroma")):
                print(f"DEBUG: Chroma目录内容: {os.listdir(os.path.join(indices_dir, 'chroma'))}")
        except Exception as e:
            print(f"DEBUG: 列出向量数据库目录内容时出错: {str(e)}")
            
        # 如果向量数据库目录都不存在，尝试列出storage/vector_db下的内容
        vector_db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "storage", "vector_db")
        if os.path.exists(vector_db_dir):
            print(f"DEBUG: storage/vector_db目录存在: {vector_db_dir}")
            print(f"DEBUG: storage/vector_db目录内容: {os.listdir(vector_db_dir)}")
        else:
            print(f"DEBUG: storage/vector_db目录不存在: {vector_db_dir}")
            
        result = {
            "indices_dir": indices_dir,
            "embeddings_dir": embeddings_dir,
            "results_dir": results_dir,
            "vector_db_paths": vector_db_paths,
            "total_indices": total_indices,
            "total_embeddings": total_embeddings,
            "similarity_threshold": default_similarity_threshold,
            "recent_search": os.path.basename(recent_search_file) if 'recent_search_file' in locals() and recent_search_file else None
        }
        print(f"DEBUG: 返回结果: {result}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存储信息失败: {str(e)}")

@router.get("/search-files")
async def get_search_files_by_index(index_id: str = None):
    """获取指定index_id的所有搜索结果文件，按时间戳排序"""
    try:
        results_dir = search_service.results_dir
        SEARCH_PREFIX = "search_"
        JSON_EXT = ".json"
        
        if not os.path.exists(results_dir):
            return []
        
        # 获取所有搜索结果文件
        all_search_files = [f for f in os.listdir(results_dir) 
                           if f.startswith(SEARCH_PREFIX) and f.endswith(JSON_EXT)]
        
        # 如果没有指定index_id，返回所有搜索结果文件
        if not index_id:
            # 按时间戳排序（最新的在前）
            all_search_files.sort(reverse=True)
            return all_search_files[:20]  # 限制返回数量
        
        # 如果指定了index_id，需要读取每个文件来检查index_id
        matching_files = []
        for filename in all_search_files:
            try:
                file_path = os.path.join(results_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('index_id') == index_id:
                        # 记录文件名和时间戳，用于排序
                        timestamp = data.get('timestamp', '')
                        matching_files.append((filename, timestamp))
            except Exception as e:
                # 如果读取文件失败，跳过这个文件
                continue
        
        # 按时间戳排序（最新的在前）
        matching_files.sort(key=lambda x: x[1], reverse=True)
        
        # 只返回文件名列表
        return [f[0] for f in matching_files]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索结果文件列表失败: {str(e)}")
