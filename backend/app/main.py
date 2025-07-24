"""
WSL Process Monitor Backend - 统一优化版本
高性能FastAPI应用入口点，集成数据库和多级缓存
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 配置结构化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wsl_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

try:
    from shared.types import ApiResponse
except ImportError:
    # 如果无法导入共享类型，使用本地定义
    from pydantic import BaseModel
    from typing import Optional, Union

    class ApiResponse(BaseModel):
        success: bool
        data: Optional[Union[dict, list]] = None
        error: Optional[str] = None
        timestamp: str

# 导入数据库和优化服务
try:
    from .database import db_manager, get_database
    from .services.wsl_service import WSLService
    from .services.optimized_process_service import OptimizedProcessService
    from .api.routes import router as api_router
    from .api.websocket import websocket_endpoint
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from database import db_manager, get_database
    from services.wsl_service import WSLService
    from services.optimized_process_service import OptimizedProcessService
    from api.routes import router as api_router
    from api.websocket import websocket_endpoint

# 全局服务实例
wsl_service = WSLService()
process_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global process_service

    # 启动时初始化
    logger.info("🚀 启动WSL Process Monitor Backend...")

    try:
        # 初始化数据库
        await db_manager.initialize()
        logger.info("✅ 数据库初始化完成")

        # 初始化优化进程服务
        process_service = OptimizedProcessService(wsl_service, db_manager)
        logger.info("✅ 优化进程服务初始化完成")

        # 记录启动指标
        await db_manager.record_performance_metric("server_start", 1.0, "count")

        yield

    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        raise
    finally:
        # 关闭时清理
        logger.info("🛑 关闭WSL Process Monitor Backend...")

        if process_service:
            await process_service.cleanup()

        await db_manager.record_performance_metric("server_stop", 1.0, "count")
        logger.info("✅ 应用清理完成")

# 创建FastAPI应用实例
app = FastAPI(
    title="WSL Process Monitor API - 统一优化版本",
    description="高性能WSL进程监控工具的后端API，支持多级缓存和数据库持久化",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)  # 压缩响应

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 依赖注入
async def get_process_service() -> OptimizedProcessService:
    """获取进程服务实例"""
    if process_service is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    return process_service

async def get_wsl_service() -> WSLService:
    """获取WSL服务实例"""
    return wsl_service

# 注册API路由
app.include_router(api_router, prefix="/api")


# WebSocket端点
@app.websocket("/ws/processes/{distro_name}")
async def websocket_processes(websocket: WebSocket, distro_name: str):
    """WebSocket端点：实时进程数据推送"""
    await websocket_endpoint(websocket, distro_name)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "WSL Process Monitor API - 统一优化版本",
        "version": "2.0.0",
        "features": [
            "多级缓存系统",
            "数据库持久化",
            "性能监控",
            "高并发处理",
            "实时WebSocket"
        ],
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "distros": "/api/distros",
            "processes": "/api/processes/{distro_name}",
            "kill_process": "/api/processes/{distro_name}/kill",
            "performance": "/api/performance",
            "system_status": "/api/system/status"
        },
        "websocket": {
            "processes": "/ws/processes/{distro_name}",
            "description": "实时进程数据推送"
        }
    }

@app.get("/health")
async def health():
    """健康检查"""
    try:
        # 检查数据库连接
        async with db_manager.get_connection() as db:
            await db.execute("SELECT 1")

        # 检查WSL可用性
        wsl_available = await wsl_service.is_wsl_available()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "database": "connected",
            "wsl_available": wsl_available
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail="服务不健康")

@app.get("/api/performance")
async def get_performance_metrics(
    process_svc: OptimizedProcessService = Depends(get_process_service)
):
    """获取性能指标"""
    try:
        summary = process_svc.get_performance_summary()

        return ApiResponse(
            success=True,
            data=summary,
            timestamp=datetime.now().isoformat()
        ).dict()

    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return ApiResponse(
        success=True,
        data={
            "status": "healthy",
            "service": "WSL Process Monitor Backend",
            "version": "1.0.0",
            "uptime": "running"
        },
        timestamp=datetime.now().isoformat()
    ).dict()


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False,
            error=f"Internal server error: {str(exc)}",
            timestamp=datetime.now().isoformat()
        ).dict()
    )


# 404处理器
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404错误处理"""
    return JSONResponse(
        status_code=404,
        content=ApiResponse(
            success=False,
            error="Endpoint not found",
            timestamp=datetime.now().isoformat()
        ).dict()
    )


if __name__ == "__main__":
    # 开发环境启动配置
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
