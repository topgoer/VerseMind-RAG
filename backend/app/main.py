import logging
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging based on environment variable
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level_map = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
log_level = log_level_map.get(log_level_str, logging.INFO)

logging.basicConfig(level=log_level)
logging.info(f"Logging level set to: {log_level_str}")

# 创建一个将标准输出重定向到日志系统的处理程序
class PrintToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''
        
    def write(self, buf):
        for line in buf.rstrip().splitlines():
            if line.strip() and '[ChunkService' in line:
                self.logger.log(self.level, line.rstrip())
    
    def flush(self):
        pass

# 创建一个专门用于捕获 ChunkService 输出的日志器
chunk_logger = logging.getLogger('ChunkService')
chunk_logger.setLevel(logging.WARNING)  # 只显示警告和错误

# 重定向标准输出，只捕获 ChunkService 相关的打印内容
sys.stdout = PrintToLogger(chunk_logger, logging.DEBUG)

# Set the global logging level to WARNING to suppress all INFO and DEBUG logs unless explicitly enabled
logging.getLogger().setLevel(logging.WARNING)

# Ensure all component-specific logging levels are set to WARNING
logging.getLogger("app.services.load_service").setLevel(logging.WARNING)
logging.getLogger("app.services.parse_service").setLevel(logging.WARNING)
logging.getLogger("app.services.chunk_service").setLevel(logging.WARNING)
logging.getLogger("app.services.embed_service").setLevel(logging.WARNING)
logging.getLogger("core.config").setLevel(logging.WARNING)
logging.getLogger("ChunkService").setLevel(logging.WARNING)
logging.getLogger("SearchService").setLevel(logging.WARNING)  # Changed from INFO to WARNING to hide search results

# 导入API路由
from app.api import documents, chunks, parse, embeddings, index, search, generate, config as config_api, debug
from app.api import debug_storage

# 创建FastAPI应用
app = FastAPI(
    title="VerseMind-RAG API",
    description="Where Poetry Meets AI - 检索增强生成系统API",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    # 定义所有必要的目录路径 - 保持唯一性
    required_dirs = [
        # 原始文档
        "storage/documents",
        # 数据处理流程目录
        "backend/01-loaded_docs",
        "backend/02-chunked-docs", 
        "backend/03-parsed-docs",
        "backend/04-embedded-docs",
        # 索引与结果存储
        "backend/storage/indices",
        "backend/storage/results"
    ]
    
    # 创建所有必要的目录
    for dir_path in required_dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            logging.error(f"[startup] Failed to create directory: {dir_path}. Error: {e}")

    # Suppress unnecessary logs unless there is an error
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("[core.config]: Initialized settings. Effective paths:")
        logging.debug("  EMBEDDINGS_DIR='%s'", os.getenv('EMBEDDINGS_DIR', 'backend/04-embedded-docs'))
        logging.debug("  INDICES_DIR='%s'", os.getenv('INDICES_DIR', 'backend/storage/indices'))
        logging.debug("  DOCUMENTS_DIR='%s'", os.getenv('DOCUMENTS_DIR', 'backend/01-loaded_docs'))
        logging.debug("  CHUNKS_DIR='%s'", os.getenv('CHUNKS_DIR', 'backend/02-chunked-docs'))
        logging.debug("  PARSED_DIR='%s'", os.getenv('PARSED_DIR', 'backend/03-parsed-docs'))

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
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
api_router.include_router(debug_storage.router, prefix="/debug", tags=["debug"])

# 将路由添加到应用
app.include_router(api_router, prefix="/api")
app.include_router(config_api.router, prefix="/api")
app.include_router(index.router, prefix="/api/indices")
app.include_router(embeddings.router, prefix="/api/embeddings")
app.include_router(search.router, prefix="/api/search")

# 根路由
@app.get("/")
async def root():
    return {
        "message": "欢迎使用VerseMind-RAG API",
        "version": "0.1.0",
        "status": "运行中",
        "docs_url": "/docs"
    }
