from fastapi import APIRouter, HTTPException, Body
from typing import Optional

from app.services.generate_service import GenerateService

router = APIRouter()
generate_service = GenerateService()


@router.post("")
@router.post("/text")
async def generate_text(
    search_id: str = Body(None),
    prompt: str = Body(...),
    provider: str = Body(...),
    model: str = Body(...),
    temperature: float = Body(0.7),
    max_tokens: Optional[int] = Body(None),
    image_data: Optional[str] = Body(None),
    document_data: Optional[str] = Body(None),
    document_text: Optional[str] = Body(None),
    document_type: Optional[str] = Body(None),
    document_name: Optional[str] = Body(None),
):
    """
    基于检索结果生成文本，可选择包含图片数据或文档数据
    """
    # 只用 config，不传 max_tokens 给服务层
    try:
        result = generate_service.generate_text(
            search_id,
            prompt,
            provider,
            model,
            temperature,
            image_data=image_data,
            document_data=document_data,
            document_text=document_text,
            document_type=document_type,
            document_name=document_name,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本生成失败: {str(e)}")


@router.post("/from_search")
async def generate_from_search(
    search_id: str = Body(...),
    prompt: str = Body(...),
    provider: str = Body(...),
    model: str = Body(...),
    temperature: float = Body(0.7),
    max_tokens: Optional[int] = Body(None),
    top_p: float = Body(1.0),
    stream: bool = Body(False),
    image_data: Optional[str] = Body(None),
    document_data: Optional[str] = Body(None),
    document_text: Optional[str] = Body(None),
    document_type: Optional[str] = Body(None),
    document_name: Optional[str] = Body(None),
):
    """
    基于搜索结果生成文本

    参数:
        search_id: 搜索结果ID
        prompt: 生成提示
        provider: 模型提供商
        model: 模型名称
        temperature: 温度参数        max_tokens: 最大生成令牌数
        top_p: 采样阈值
        stream: 是否流式返回
        image_data: 可选的base64编码图片数据
        document_data: 可选的base64编码文档数据
        document_text: 可选的文档文本内容
        document_type: 可选的文档类型
        document_name: 可选的文档名称
    """
    try:
        # 使用与generate_text相同的服务方法，但确保search_id不为空
        if not search_id:
            raise ValueError("搜索结果ID不能为空")

        result = generate_service.generate_text(
            search_id,
            prompt,
            provider,
            model,
            temperature,
            image_data=image_data,
            document_data=document_data,
            document_text=document_text,
            document_type=document_type,
            document_name=document_name,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"基于搜索结果生成文本失败: {str(e)}"
        )


@router.get("/models")
async def get_generation_models():
    """
    获取可用的生成模型列表
    """
    return generate_service.get_generation_models()
