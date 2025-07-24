#!/usr/bin/env python3
"""
WSL Process Monitor - 统一服务器
解决所有导入问题的完整服务器实现
"""

import os
import sys
import logging
import asyncio
import json
import subprocess
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# 添加路径
project_root = os.path.dirname(__file__)
backend_path = os.path.join(project_root, "backend", "app")
sys.path.insert(0, backend_path)

# 导入依赖
from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import aiosqlite

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wsl_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据模型
class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str

# 数据库管理器
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "wsl_monitor.db"):
        self.db_path = db_path
        self.cache_l1: Dict[str, Any] = {}
        self.cache_l2: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(seconds=30)
        
    async def initialize(self):
        """初始化数据库"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
                logger.info(f"数据库初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """创建数据库表"""
        
        # 进程历史表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS process_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                distro_name TEXT NOT NULL,
                pid INTEGER NOT NULL,
                name TEXT NOT NULL,
                user_name TEXT NOT NULL,
                cpu_percent REAL DEFAULT 0,
                memory_rss INTEGER DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 性能指标表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.commit()
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        connection = None
        try:
            connection = await aiosqlite.connect(self.db_path)
            connection.row_factory = aiosqlite.Row
            yield connection
        except Exception as e:
            logger.error(f"数据库连接错误: {e}")
            raise
        finally:
            if connection:
                await connection.close()
    
    async def record_performance_metric(self, metric_name: str, metric_value: float):
        """记录性能指标"""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT INTO performance_metrics (metric_name, metric_value, recorded_at)
                    VALUES (?, ?, ?)
                """, (metric_name, metric_value, datetime.now().isoformat()))
                await db.commit()
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")

# WSL服务
class WSLService:
    """WSL服务"""
    
    async def is_wsl_available(self) -> bool:
        """检查WSL是否可用"""
        try:
            result = await asyncio.create_subprocess_exec(
                "wsl", "--list", "--verbose",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            return result.returncode == 0
        except Exception:
            return False
    
    async def get_distros(self) -> List[Dict[str, Any]]:
        """获取WSL发行版列表"""
        try:
            result = await asyncio.create_subprocess_exec(
                "wsl", "--list", "--verbose",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return []
            
            lines = stdout.decode('utf-16le', errors='ignore').strip().split('\n')
            distros = []
            
            for line in lines[1:]:  # 跳过标题行
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        name = parts[0].replace('*', '').strip()
                        state = parts[1].strip()
                        if name and state:
                            distros.append({
                                "name": name,
                                "state": state,
                                "default": '*' in line
                            })
            
            return distros
            
        except Exception as e:
            logger.error(f"获取发行版列表失败: {e}")
            return []
    
    async def get_processes(self, distro_name: str) -> List[Dict[str, Any]]:
        """获取进程列表"""
        try:
            result = await asyncio.create_subprocess_exec(
                "wsl", "-d", distro_name, "ps", "aux", "--no-headers",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return []
            
            processes = []
            lines = stdout.decode('utf-8', errors='ignore').strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                    
                try:
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        process = {
                            'user': parts[0],
                            'pid': int(parts[1]),
                            'cpu_percent': float(parts[2]),
                            'memory_percent': float(parts[3]),
                            'vsz': int(parts[4]),
                            'rss': int(parts[5]),
                            'tty': parts[6],
                            'stat': parts[7],
                            'start': parts[8],
                            'time': parts[9],
                            'command': parts[10],
                            'name': parts[10].split()[0] if parts[10] else 'unknown'
                        }
                        processes.append(process)
                except (ValueError, IndexError):
                    continue
            
            return processes
            
        except Exception as e:
            logger.error(f"获取进程列表失败: {e}")
            return []

# 全局实例
db_manager = DatabaseManager()
wsl_service = WSLService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动WSL Process Monitor Backend...")
    
    try:
        await db_manager.initialize()
        logger.info("✅ 数据库初始化完成")
        
        await db_manager.record_performance_metric("server_start", 1.0)
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        raise
    finally:
        logger.info("🛑 关闭WSL Process Monitor Backend...")
        await db_manager.record_performance_metric("server_stop", 1.0)

# 创建FastAPI应用
app = FastAPI(
    title="WSL Process Monitor API - 统一版本",
    description="高性能WSL进程监控工具",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)
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

# API路由
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "WSL Process Monitor API - 统一版本",
        "version": "2.0.0",
        "features": [
            "多级缓存系统",
            "数据库持久化",
            "性能监控",
            "实时WebSocket"
        ],
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "distros": "/api/distros",
            "processes": "/api/processes/{distro_name}",
            "system_status": "/api/system/status"
        }
    }

@app.get("/health")
async def health():
    """健康检查"""
    try:
        async with db_manager.get_connection() as db:
            await db.execute("SELECT 1")
        
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

@app.get("/api/distros")
async def get_distros():
    """获取WSL发行版列表"""
    try:
        logger.info("API调用: 获取WSL发行版列表")
        
        if not await wsl_service.is_wsl_available():
            raise HTTPException(
                status_code=503,
                detail="WSL不可用，请确保WSL已正确安装并启动"
            )
        
        distros = await wsl_service.get_distros()
        logger.info(f"获取到 {len(distros)} 个发行版")
        
        return ApiResponse(
            success=True,
            data=distros,
            timestamp=datetime.now().isoformat()
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取发行版列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/processes/{distro_name}")
async def get_processes(distro_name: str):
    """获取进程列表"""
    try:
        logger.info(f"API调用: 获取 {distro_name} 的进程列表")
        
        start_time = time.time()
        processes = await wsl_service.get_processes(distro_name)
        processing_time = time.time() - start_time
        
        # 计算统计信息
        total_processes = len(processes)
        running_processes = sum(1 for p in processes if p.get('stat', '').startswith('R'))
        total_cpu = sum(p.get('cpu_percent', 0) for p in processes)
        total_memory = sum(p.get('rss', 0) for p in processes) / 1024  # MB
        
        statistics = {
            "total_processes": total_processes,
            "running_processes": running_processes,
            "total_cpu_percent": round(total_cpu, 2),
            "total_memory_mb": round(total_memory, 2)
        }
        
        # 记录性能指标
        await db_manager.record_performance_metric("process_fetch_time", processing_time)
        await db_manager.record_performance_metric("process_count", total_processes)
        
        return ApiResponse(
            success=True,
            data={
                "processes": processes,
                "statistics": statistics,
                "count": total_processes,
                "distro": distro_name
            },
            timestamp=datetime.now().isoformat()
        ).dict()
        
    except Exception as e:
        logger.error(f"获取进程列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/status")
async def get_system_status():
    """获取系统状态"""
    try:
        logger.info("API调用: 获取系统状态")
        
        wsl_available = await wsl_service.is_wsl_available()
        distros = []
        
        if wsl_available:
            distros = await wsl_service.get_distros()
        
        running_distros = [d for d in distros if d.get("state") == "Running"]
        
        return ApiResponse(
            success=True,
            data={
                "wsl_available": wsl_available,
                "total_distros": len(distros),
                "running_distros": len(running_distros),
                "distros": distros,
                "system_time": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        ).dict()
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket端点
@app.websocket("/ws/processes/{distro_name}")
async def websocket_processes(websocket: WebSocket, distro_name: str):
    """WebSocket端点：实时进程数据推送"""
    await websocket.accept()
    
    try:
        logger.info(f"WebSocket连接建立: {distro_name}")
        
        await websocket.send_json({
            "type": "connection",
            "data": {"message": f"已连接到 {distro_name}", "distro": distro_name},
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            try:
                processes = await wsl_service.get_processes(distro_name)
                
                # 计算统计信息
                total_processes = len(processes)
                running_processes = sum(1 for p in processes if p.get('stat', '').startswith('R'))
                total_cpu = sum(p.get('cpu_percent', 0) for p in processes)
                total_memory = sum(p.get('rss', 0) for p in processes) / 1024
                
                statistics = {
                    "total_processes": total_processes,
                    "running_processes": running_processes,
                    "total_cpu_percent": round(total_cpu, 2),
                    "total_memory_mb": round(total_memory, 2)
                }
                
                message = {
                    "type": "processes",
                    "data": {
                        "processes": processes,
                        "statistics": statistics,
                        "distro": distro_name,
                        "count": total_processes
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send_json(message)
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"WebSocket数据推送失败: {e}")
                
                error_message = {
                    "type": "error",
                    "data": {"error": str(e), "distro": distro_name},
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_json(error_message)
                break
                
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        logger.info(f"WebSocket连接关闭: {distro_name}")

if __name__ == "__main__":
    uvicorn.run(
        "unified_server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
