"""
Financial Reporting Agent - FastAPI应用入口
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from contextlib import asynccontextmanager

# 导入API路由
from src.api.endpoints.summary import router as summary_router
from src.api.endpoints.database import router as database_router
from src.api.endpoints.visualization import router as visualization_router
from src.api.endpoints.reporting import router as reporting_router
from src.api.endpoints.workflow import router as workflow_router

# 导入配置
from src.config import get_settings

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# 创建必要的目录
def create_directories():
    """创建必要的目录结构"""
    directories = [
        settings.INPUT_DATA_DIR,
        settings.PROCESSED_DATA_DIR,
        os.path.join(settings.PROCESSED_DATA_DIR, "summary"),
        os.path.join(settings.PROCESSED_DATA_DIR, "database"),
        os.path.join(settings.PROCESSED_DATA_DIR, "visualization"),
        os.path.join(settings.PROCESSED_DATA_DIR, "reports"),
        os.path.join(settings.PROCESSED_DATA_DIR, "workflow"),
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# 使用lifespan上下文管理器替代on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("应用启动中...")
    create_directories()
    logger.info("目录结构已创建")
    
    yield  # 这里是应用运行期间
    
    # 关闭时执行
    logger.info("应用关闭中...")

# 创建FastAPI应用
app = FastAPI(
    title="Financial Reporting Agent",
    description="财务数据处理和报告生成系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,  # 使用lifespan上下文管理器
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(summary_router, prefix="/finance/summary", tags=["数据汇总"])
app.include_router(database_router, prefix="/finance/database", tags=["财务数据库"])
app.include_router(visualization_router, prefix="/finance/visualization", tags=["可视化"])
app.include_router(reporting_router, prefix="/finance/reporting", tags=["分析报告"])
app.include_router(workflow_router, prefix="/finance/workflow", tags=["一体化工作流"])


# 根端点
@app.get("/")
async def root():
    """根端点，提供API信息"""
    return {
        "message": "Financial Reporting Agent API",
        "version": "1.0.0",
        "docs_url": "/docs",
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

# 直接运行此文件时的入口点
if __name__ == "__main__":
    import uvicorn
    create_directories()
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)