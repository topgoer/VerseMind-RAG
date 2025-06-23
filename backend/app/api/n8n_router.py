"""
# N8N工作流触发器API路由
# 用于触发微信公众号文章下载的n8n工作流
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import httpx

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/v1/n8n", tags=["n8n"])

# 常量定义
N8N_DOWNLOAD_DIR = "D:/n8n-local-files"

# 简单的内存任务状态存储
task_status_store = {}

class TaskStatus:
    def __init__(self, task_id: str, biz: str):
        self.task_id = task_id
        self.biz = biz
        self.status = "running"  # running, completed, failed
        self.created_at = datetime.now()
        self.completed_at = None
        self.files = []
        self.message = "任务正在执行中..."

class WechatDownloadRequest(BaseModel):
    """微信公众号下载请求模型"""
    biz: str = Field(..., description="微信公众号的biz参数", min_length=1)

class WechatDownloadResponse(BaseModel):
    """微信公众号下载响应模型"""
    success: bool
    message: str
    task_id: Optional[str] = None

async def trigger_n8n_workflow(biz: str) -> Dict[str, Any]:
    """
    触发n8n工作流的异步函数

    Args:
        biz: 微信公众号的biz参数

    Returns:
        Dict: n8n工作流的响应结果

    Raises:
        HTTPException: 当n8n工作流调用失败时
    """
    # 从环境变量获取配置
    n8n_webhook_url = os.getenv("N8N_WECHAT_DOWNLOAD_URL")
    jizhile_api_key = os.getenv("JIZHILE_API_KEY")

    if not n8n_webhook_url:
        logger.error("N8N_WECHAT_DOWNLOAD_URL环境变量未设置")
        raise HTTPException(
            status_code=500,
            detail="N8N工作流URL未配置，请联系管理员"
        )

    if not jizhile_api_key:
        logger.error("JIZHILE_API_KEY环境变量未设置")
        raise HTTPException(
            status_code=500,
            detail="极致了API密钥未配置，请联系管理员"
        )

    # 准备发送给n8n的数据
    payload = {
        "biz": biz,
        "jizhile_key": jizhile_api_key
    }

    try:
        # 调用n8n的webhook
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"正在调用n8n工作流: {n8n_webhook_url}")
            logger.info(f"发送数据: biz={biz}")

            response = await client.post(
                n8n_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析响应
            result = response.json()
            logger.info(f"n8n工作流响应: {result}")

            return result

    except httpx.TimeoutException:
        logger.error(f"调用n8n工作流超时: {n8n_webhook_url}")
        raise HTTPException(
            status_code=504,
            detail="n8n工作流调用超时，请稍后重试"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"n8n工作流返回错误状态: {e.response.status_code}")
        logger.error(f"错误响应内容: {e.response.text}")
        raise HTTPException(
            status_code=502,
            detail=f"n8n工作流执行失败: HTTP {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"调用n8n工作流时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"调用n8n工作流时发生错误: {str(e)}"
        )

@router.post("/trigger-wechat-download", response_model=WechatDownloadResponse)
async def trigger_wechat_download(
    request: WechatDownloadRequest,
    background_tasks: BackgroundTasks
) -> WechatDownloadResponse:
    """
    触发微信公众号文章下载工作流

    Args:
        request: 包含biz参数的请求体
        background_tasks: FastAPI后台任务管理器

    Returns:
        WechatDownloadResponse: 包含任务状态的响应
    """
    try:
        logger.info(f"收到微信公众号下载请求: biz={request.biz}")

        # 验证biz参数格式（基本验证）
        if not request.biz.strip():
            raise HTTPException(
                status_code=400,
                detail="biz参数不能为空"
            )

        # 调用n8n工作流
        await trigger_n8n_workflow(request.biz.strip())

        # 生成任务ID（可以使用UUID或其他方式）
        import uuid
        task_id = str(uuid.uuid4())

        # 存储任务状态
        task_status_store[task_id] = TaskStatus(task_id=task_id, biz=request.biz.strip())

        logger.info(f"微信公众号下载任务已启动: task_id={task_id}, biz={request.biz}")

        return WechatDownloadResponse(
            success=True,
            message="微信公众号文章下载任务已成功启动，请稍后查看下载结果",
            task_id=task_id
        )

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"处理微信公众号下载请求时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理请求时发生内部错误: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    健康检查接口

    Returns:
        Dict: 服务状态信息
    """
    return {
        "status": "healthy",
        "service": "n8n-integration",
        "version": "1.0.0"
    }

@router.get("/download-files", response_model=List[dict])
async def get_download_files():
    """
    获取n8n下载的文件列表
    """
    try:
        download_dir = N8N_DOWNLOAD_DIR
        if not os.path.exists(download_dir):
            return []

        files = []
        for filename in os.listdir(download_dir):
            file_path = os.path.join(download_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "path": file_path,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        # 按修改时间排序，最新的在前
        files.sort(key=lambda x: x["modified_at"], reverse=True)
        return files

    except Exception as e:
        logger.error(f"获取下载文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取下载文件列表失败: {str(e)}")

@router.get("/recent-downloads", response_model=List[dict])
async def get_recent_downloads(minutes: int = 10):
    """
    获取最近指定分钟内的下载文件
    """
    try:
        download_dir = N8N_DOWNLOAD_DIR
        if not os.path.exists(download_dir):
            logger.warning(f"下载目录不存在: {download_dir}")
            return []

        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_files = []

        logger.info(f"检查最近{minutes}分钟的下载文件，截止时间: {cutoff_time.isoformat()}")

        for filename in os.listdir(download_dir):
            file_path = os.path.join(download_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                modified_time = datetime.fromtimestamp(stat.st_mtime)

                if modified_time > cutoff_time:
                    file_info = {
                        "filename": filename,
                        "path": file_path,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": modified_time.isoformat()
                    }
                    recent_files.append(file_info)
                    logger.info(f"发现最近下载的文件: {filename}, 大小: {stat.st_size}字节, 修改时间: {modified_time.isoformat()}")

        # 按修改时间排序，最新的在前
        recent_files.sort(key=lambda x: x["modified_at"], reverse=True)

        if recent_files:
            logger.info(f"✅ 检测到 {len(recent_files)} 个最近下载的文件")
            for file in recent_files:
                logger.info(f"  - {file['filename']} ({file['size']} 字节)")
        else:
            logger.info(f"未检测到最近{minutes}分钟内的下载文件")

        return recent_files

    except Exception as e:
        logger.error(f"获取最近下载文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取最近下载文件失败: {str(e)}")

def _check_recent_files_for_task(task: TaskStatus) -> List[dict]:
    """
    检查任务相关的最近下载文件
    """
    recent_files = []
    download_dir = N8N_DOWNLOAD_DIR

    if not os.path.exists(download_dir):
        return recent_files

    cutoff_time = task.created_at

    for filename in os.listdir(download_dir):
        file_path = os.path.join(download_dir, filename)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            modified_time = datetime.fromtimestamp(stat.st_mtime)

            if modified_time > cutoff_time:
                recent_files.append({
                    "filename": filename,
                    "path": file_path,
                    "size": stat.st_size,
                    "modified_at": modified_time.isoformat()
                })

    return recent_files

def _update_task_completion(task: TaskStatus, task_id: str, recent_files: List[dict]) -> None:
    """
    更新任务完成状态
    """
    if recent_files and len(recent_files) > 0:
        task.status = "completed"
        task.completed_at = datetime.now()
        task.files = recent_files
        task.message = f"下载完成！共获取 {len(recent_files)} 个文件"

        logger.info(f"✅ 任务 {task_id} 已完成，检测到 {len(recent_files)} 个文件")
        for file in recent_files:
            logger.info(f"  📄 {file['filename']} ({file['size']} 字节)")

@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取指定任务的状态
    """
    try:
        if task_id not in task_status_store:
            raise HTTPException(status_code=404, detail="任务不存在")

        task = task_status_store[task_id]

        # 如果任务还在运行中，检查是否有新文件完成
        if task.status == "running":
            recent_files = _check_recent_files_for_task(task)
            _update_task_completion(task, task_id, recent_files)

        return {
            "task_id": task_id,
            "status": task.status,
            "biz": task.biz,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "message": task.message,
            "files": task.files,
            "completed": task.status in ["completed", "failed"]
        }

    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

