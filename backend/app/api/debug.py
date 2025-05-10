from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, Any, List, Optional
import os
import json

from app.services.search_service import SearchService
from app.services.embed_service import EmbedService

router = APIRouter()
search_service = SearchService()
embed_service = EmbedService()

@router.get("/dump-files/{index_id}")
async def dump_file_locations(index_id: str):
    """调试端点：转储索引和嵌入文件的结构，以便诊断问题"""
    try:
        if not hasattr(search_service, "debug_dump_files"):
            return {
                "error": "SearchService does not have debug_dump_files method",
                "directories": {
                    "indices_dir": search_service.indices_dir,
                    "alt_indices_dir": getattr(search_service, "alt_indices_dir", "Not available"),
                    "embeddings_dir": search_service.embeddings_dir,
                    "alt_embeddings_dir": getattr(search_service, "alt_embeddings_dir", "Not available")
                }
            }
            
        return search_service.debug_dump_files(index_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调试错误: {str(e)}")

@router.get("/list-embeddings")
async def list_embeddings(document_id: Optional[str] = None):
    """列出所有可用的嵌入文件"""
    try:
        return embed_service.list_embeddings(document_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出嵌入失败: {str(e)}")

@router.get("/list-indices")
async def list_indices():
    """列出所有可用的索引文件"""
    try:
        indices_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')), 'backend', 'storage', 'indices')
        results = []
        
        if os.path.exists(indices_dir):
            for filename in os.listdir(indices_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(indices_dir, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            
                        results.append({
                            "filename": filename,
                            "index_id": data.get("index_id", ""),
                            "document_id": data.get("document_id", ""),
                            "embedding_id": data.get("embedding_id", ""),
                            "timestamp": data.get("timestamp", ""),
                        })
                    except Exception as e:
                        results.append({
                            "filename": filename,
                            "error": str(e)
                        })
        
        return {
            "indices_dir": indices_dir,
            "exists": os.path.exists(indices_dir),
            "indices": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出索引失败: {str(e)}")

@router.get("/paths")
async def get_paths():
    """获取系统使用的所有路径"""
    # 获取基本目录
    storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    
    # 搜索服务路径
    search_indices_dir = getattr(search_service, "indices_dir", "Not available")
    search_alt_indices_dir = getattr(search_service, "alt_indices_dir", "Not available")
    search_embeddings_dir = getattr(search_service, "embeddings_dir", "Not available")
    search_alt_embeddings_dir = getattr(search_service, "alt_embeddings_dir", "Not available")
    
    # 嵌入服务路径
    embed_indices_dir = getattr(embed_service, "indices_dir", "Not available")
    embed_embeddings_dir = getattr(embed_service, "embeddings_dir", "Not available")
    
    # 检查目录存在性
    paths = {
        "storage_dir": storage_dir,
        "search_service": {
            "indices_dir": search_indices_dir,
            "exists": os.path.exists(search_indices_dir),
            "alt_indices_dir": search_alt_indices_dir,
            "alt_exists": os.path.exists(search_alt_indices_dir),
            "embeddings_dir": search_embeddings_dir,
            "exists": os.path.exists(search_embeddings_dir),
            "alt_embeddings_dir": search_alt_embeddings_dir,
            "alt_exists": os.path.exists(search_alt_embeddings_dir)
        },
        "embed_service": {
            "indices_dir": embed_indices_dir,
            "exists": os.path.exists(embed_indices_dir),
            "embeddings_dir": embed_embeddings_dir,
            "exists": os.path.exists(embed_embeddings_dir)
        },
        "all_indices": [],
        "all_embeddings": []
    }
    
    # 查找所有索引文件
    for dir_path in [search_indices_dir, search_alt_indices_dir, embed_indices_dir]:
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if filename.endswith('.json'):
                    paths["all_indices"].append({
                        "dir": dir_path,
                        "filename": filename,
                    })
    
    # 查找所有嵌入文件
    for dir_path in [search_embeddings_dir, search_alt_embeddings_dir, embed_embeddings_dir]:
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if filename.endswith('.json'):
                    paths["all_embeddings"].append({
                        "dir": dir_path,
                        "filename": filename,
                    })
    
    return paths
