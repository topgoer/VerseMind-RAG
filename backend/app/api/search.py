from fastapi import APIRouter, HTTPException, Body

from app.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()

@router.post("/")
async def search_endpoint(
    index_id_or_collection: str = Body(...),
    query: str = Body(...),
    top_k: int = Body(3),
    similarity_threshold: float = Body(0.5),
    min_chars: int = Body(100)
):
    """
    执行语义搜索（POST请求版本）- 支持索引ID或集合名称

    - index_id_or_collection: 索引ID或集合名称
    - query: 查询文本
    - top_k: 返回结果数量
    - similarity_threshold: 相似度阈值 (默认0.5)
    - min_chars: 最小字符数 (默认100)
    """
    try:
        result = search_service.search(index_id_or_collection, query, top_k, similarity_threshold, min_chars)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

# Keep the existing route for compatibility
@router.post("/{index_id}")
async def search_with_index(
    index_id: str,
    query: str = Body(...),
    top_k: int = Body(3),
    similarity_threshold: float = Body(0.5),
    min_chars: int = Body(100)
):
    """
    执行语义搜索（带路径参数版本）- 支持索引ID

    - index_id: 索引ID
    - query: 查询文本
    - top_k: 返回结果数量
    - similarity_threshold: 相似度阈值 (默认0.5)
    - min_chars: 最小字符数 (默认100)
    """
    try:
        result = search_service.search(index_id, query, top_k, similarity_threshold, min_chars)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

# Add a new route for collection search
@router.post("/collection/{collection_name}")
async def search_collection(
    collection_name: str,
    query: str = Body(...),
    top_k: int = Body(3),
    similarity_threshold: float = Body(0.5),
    min_chars: int = Body(100)
):
    """
    执行集合语义搜索（带路径参数版本）- 明确指定集合名称

    - collection_name: 集合名称
    - query: 查询文本
    - top_k: 返回结果数量
    - similarity_threshold: 相似度阈值 (默认0.5)
    - min_chars: 最小字符数 (默认100)
    """
    try:
        result = search_service.search(collection_name, query, top_k, similarity_threshold, min_chars)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.get("/debug/{index_id}")
async def debug_search(index_id: str):
    """
    调试端点，输出索引和嵌入文件信息
    """
    try:
        # 使用我们添加的调试函数
        if hasattr(search_service, 'debug_dump_files'):
            result = search_service.debug_dump_files(index_id)
            return result
        else:
            return {
                "error": "调试功能不可用，请确保SearchService类中包含debug_dump_files方法",
                "index_id": index_id
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调试失败: {str(e)}")
