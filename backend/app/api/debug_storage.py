from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import json
from app.services.search_service import SearchService

# Constants
JSON_EXTENSION = ".json"
SEARCH_PREFIX = "search_"

router = APIRouter()
search_service = SearchService()


@router.get("/search-results/{filename}")
async def get_search_results(filename: str) -> Dict[str, Any]:
    """获取特定的搜索结果文件内容"""
    try:
        results_dir = search_service.results_dir
        search_file_path = os.path.join(results_dir, filename)

        if not os.path.exists(search_file_path):
            raise HTTPException(
                status_code=404, detail=f"搜索结果文件不存在: {filename}"
            )

        try:
            with open(search_file_path, "r", encoding="utf-8") as f:
                search_data = json.load(f)
                return search_data
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"读取搜索结果文件失败: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索结果失败: {str(e)}")


def _get_similarity_threshold_from_recent_search(results_dir: str) -> tuple[float, str]:
    """从最近的搜索结果中获取相似度阈值"""
    default_threshold = 0.5
    recent_search_file = None

    if not os.path.exists(results_dir):
        return default_threshold, recent_search_file

    search_files = [
        f
        for f in os.listdir(results_dir)
        if f.startswith(SEARCH_PREFIX) and f.endswith(JSON_EXTENSION)
    ]

    if not search_files:
        return default_threshold, recent_search_file

    search_files.sort(reverse=True)
    recent_search_file = os.path.join(results_dir, search_files[0])

    try:
        with open(recent_search_file, "r", encoding="utf-8") as f:
            search_data = json.load(f)
            threshold = search_data.get("similarity_threshold", default_threshold)
            return threshold, recent_search_file
    except Exception as e:
        print(f"读取最近搜索结果文件失败: {e}")
        return default_threshold, recent_search_file


def _get_vector_db_paths(indices_dir: str) -> Dict[str, str]:
    """获取向量数据库路径"""
    vector_db_paths = {}

    faiss_dir = os.path.join(indices_dir, "faiss")
    if os.path.exists(faiss_dir):
        vector_db_paths["FAISS"] = faiss_dir

    chroma_dir = os.path.join(indices_dir, "chroma")
    if os.path.exists(chroma_dir):
        vector_db_paths["Chroma"] = chroma_dir

    return vector_db_paths


def _count_files_with_extension(directory: str, extension: str) -> int:
    """统计指定目录中特定扩展名的文件数量"""
    if not os.path.exists(directory):
        return 0

    count = 0
    for filename in os.listdir(directory):
        if filename.endswith(extension):
            count += 1
    return count


def _log_debug_info(indices_dir: str, embeddings_dir: str, results_dir: str):
    """输出调试信息"""
    print(f"DEBUG: indices_dir: {indices_dir}")
    print(f"DEBUG: embeddings_dir: {embeddings_dir}")
    print(f"DEBUG: results_dir: {results_dir}")

    # 检查向量数据库目录
    faiss_dir = os.path.join(indices_dir, "faiss")
    chroma_dir = os.path.join(indices_dir, "chroma")

    print(
        f"DEBUG: 检查FAISS目录是否存在: {faiss_dir}, 结果: {os.path.exists(faiss_dir)}"
    )
    print(
        f"DEBUG: 检查Chroma目录是否存在: {chroma_dir}, 结果: {os.path.exists(chroma_dir)}"
    )

    # 列出目录内容
    _log_directory_contents(faiss_dir, "FAISS")
    _log_directory_contents(chroma_dir, "Chroma")

    # 检查storage/vector_db目录
    _check_storage_vector_db()


def _log_directory_contents(directory: str, db_type: str):
    """安全地列出目录内容"""
    try:
        if os.path.exists(directory):
            contents = os.listdir(directory)
            print(f"DEBUG: {db_type}目录内容: {contents}")
    except Exception as e:
        print(f"DEBUG: 列出{db_type}目录内容时出错: {str(e)}")


def _check_storage_vector_db():
    """检查storage/vector_db目录"""
    try:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        vector_db_dir = os.path.join(base_dir, "storage", "vector_db")

        if os.path.exists(vector_db_dir):
            print(f"DEBUG: storage/vector_db目录存在: {vector_db_dir}")
            print(f"DEBUG: storage/vector_db目录内容: {os.listdir(vector_db_dir)}")
        else:
            print(f"DEBUG: storage/vector_db目录不存在: {vector_db_dir}")
    except Exception as e:
        print(f"DEBUG: 检查storage/vector_db目录时出错: {str(e)}")


@router.get("/storage-info")
async def get_storage_info() -> Dict[str, Any]:
    """获取系统中各种向量数据库和嵌入向量的存储位置信息"""
    try:
        # 获取基础存储目录
        indices_dir = search_service.indices_dir
        embeddings_dir = search_service.embeddings_dir
        results_dir = search_service.results_dir

        # 获取相似度阈值和最近搜索文件
        similarity_threshold, recent_search_file = (
            _get_similarity_threshold_from_recent_search(results_dir)
        )

        # 输出调试信息
        _log_debug_info(indices_dir, embeddings_dir, results_dir)

        # 获取向量数据库路径
        vector_db_paths = _get_vector_db_paths(indices_dir)
        # 统计文件数量
        total_indices = _count_files_with_extension(indices_dir, JSON_EXTENSION)
        total_embeddings = _count_files_with_extension(embeddings_dir, JSON_EXTENSION)

        result = {
            "indices_dir": indices_dir,
            "embeddings_dir": embeddings_dir,
            "results_dir": results_dir,
            "vector_db_paths": vector_db_paths,
            "total_indices": total_indices,
            "total_embeddings": total_embeddings,
            "similarity_threshold": similarity_threshold,
            "recent_search": os.path.basename(recent_search_file)
            if recent_search_file
            else None,
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

        if not os.path.exists(results_dir):
            return []

        # 获取所有搜索结果文件
        all_search_files = [
            f
            for f in os.listdir(results_dir)
            if f.startswith(SEARCH_PREFIX) and f.endswith(JSON_EXTENSION)
        ]

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
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("index_id") == index_id:
                        # 记录文件名和时间戳，用于排序
                        timestamp = data.get("timestamp", "")
                        matching_files.append((filename, timestamp))
            except Exception:
                # 如果读取文件失败，跳过这个文件
                continue

        # 按时间戳排序（最新的在前）
        matching_files.sort(key=lambda x: x[1], reverse=True)

        # 只返回文件名列表
        return [f[0] for f in matching_files]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取搜索结果文件列表失败: {str(e)}"
        )
