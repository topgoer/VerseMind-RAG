from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import os

# 导入API路由
from app.api import documents, chunks, parse, embeddings, index, search, generate, config as config_api

# 创建FastAPI应用
app = FastAPI(
    title="VerseMind-RAG API",
    description="Where Poetry Meets AI - 检索增强生成系统API",
    version="0.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建API路由
api_router = APIRouter()

# 添加各模块路由
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chunks.router, prefix="/chunks", tags=["chunks"])
api_router.include_router(parse.router, prefix="/parse", tags=["parse"])
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["embeddings"])
api_router.include_router(index.router, prefix="/index", tags=["index"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])

# 将路由添加到应用
app.include_router(api_router, prefix="/api")
app.include_router(config_api.router, prefix="/api")

# 创建必要的存储目录
@app.on_event("startup")
async def startup_event():
    os.makedirs("storage/documents", exist_ok=True)
    os.makedirs("storage/chunks", exist_ok=True)
    os.makedirs("storage/embeddings", exist_ok=True)
    os.makedirs("storage/indices", exist_ok=True)
    os.makedirs("storage/results", exist_ok=True)

# 根路由
@app.get("/")
async def root():
    return {
        "message": "欢迎使用VerseMind-RAG API",
        "version": "0.1.0",
        "status": "运行中",
        "docs_url": "/docs"
    }
