#!/usr/bin/env python3
"""
WSL Process Monitor - MySQL统一服务器
支持MySQL数据库和多级缓存的完整服务器实现
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

# 添加路径
project_root = os.path.dirname(__file__)
backend_path = os.path.join(project_root, "backend", "app")
sys.path.insert(0, backend_path)

# 导入配置
try:
    from config import get_config, load_config_from_file
    load_config_from_file()  # 尝试加载配置文件
    config = get_config()
    print(f"✅ 配置加载成功，数据库类型: {config.database.type}")
except ImportError:
    print("⚠️ 配置模块不可用，使用默认配置")
    config = None

# 导入依赖
from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# 根据配置选择数据库
database_manager = None
database_type = "sqlite"

if config and config.is_mysql_enabled():
    try:
        from mysql_database import MySQLDatabaseManager
        database_manager = MySQLDatabaseManager(
            host=config.database.mysql_host,
            port=config.database.mysql_port,
            user=config.database.mysql_user,
            password=config.database.mysql_password,
            database=config.database.mysql_database
        )
        database_type = "mysql"
        print("✅ 使用MySQL数据库 + 多级缓存")
    except ImportError as e:
        print(f"⚠️ MySQL依赖未安装: {e}")
        print("请运行: pip install aiomysql")
        print("回退到SQLite数据库")

if database_manager is None:
    # 使用SQLite作为回退
    import aiosqlite
    from database import DatabaseManager
    database_manager = DatabaseManager()
    database_type = "sqlite"
    print("✅ 使用SQLite数据库")

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
wsl_service = WSLService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动WSL Process Monitor Backend (MySQL版本)...")
    
    try:
        await database_manager.initialize()
        logger.info(f"✅ {database_type.upper()}数据库初始化完成")
        
        await database_manager.record_performance_metric("server_start", 1.0)
        
        # 如果是MySQL，显示缓存统计
        if database_type == "mysql":
            cache_stats = await database_manager.get_cache_statistics()
            logger.info(f"📊 缓存统计: {cache_stats}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        raise
    finally:
        logger.info("🛑 关闭WSL Process Monitor Backend...")
        await database_manager.record_performance_metric("server_stop", 1.0)
        
        if hasattr(database_manager, 'cleanup'):
            await database_manager.cleanup()

# 创建FastAPI应用
app = FastAPI(
    title="WSL Process Monitor API - MySQL统一版本",
    description="高性能WSL进程监控工具，支持MySQL数据库和多级缓存",
    version="2.1.0",
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
    cache_info = {}
    if database_type == "mysql" and hasattr(database_manager, 'get_cache_statistics'):
        try:
            cache_info = await database_manager.get_cache_statistics()
        except:
            cache_info = {"error": "无法获取缓存统计"}
    
    return {
        "message": "WSL Process Monitor API - MySQL统一版本",
        "version": "2.1.0",
        "database_type": database_type,
        "features": [
            "MySQL数据库支持" if database_type == "mysql" else "SQLite数据库",
            "多级缓存系统 (L1内存+L2磁盘+L3Redis模拟)" if database_type == "mysql" else "基础缓存",
            "性能监控",
            "实时WebSocket",
            "配置化管理"
        ],
        "cache_statistics": cache_info,
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "distros": "/api/distros",
            "processes": "/api/processes/{distro_name}",
            "system_status": "/api/system/status",
            "cache_stats": "/api/cache/stats" if database_type == "mysql" else None
        }
    }

@app.get("/health")
async def health():
    """健康检查"""
    try:
        # 检查数据库连接
        if database_type == "mysql":
            async with database_manager.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
        else:
            async with database_manager.get_connection() as db:
                await db.execute("SELECT 1")
        
        wsl_available = await wsl_service.is_wsl_available()
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0",
            "database": f"{database_type}_connected",
            "wsl_available": wsl_available
        }
        
        # 添加缓存信息
        if database_type == "mysql":
            try:
                cache_stats = await database_manager.get_cache_statistics()
                health_data["cache_levels"] = len(cache_stats.get("cache_levels", {}))
                health_data["total_cache_keys"] = (
                    cache_stats.get("total_l1_keys", 0) + 
                    cache_stats.get("total_l3_keys", 0)
                )
            except:
                health_data["cache_status"] = "error"
        
        return health_data
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail="服务不健康")

@app.get("/api/cache/stats")
async def get_cache_stats():
    """获取缓存统计（仅MySQL）"""
    if database_type != "mysql":
        raise HTTPException(status_code=404, detail="缓存统计仅在MySQL模式下可用")
    
    try:
        stats = await database_manager.get_cache_statistics()
        return ApiResponse(
            success=True,
            data=stats,
            timestamp=datetime.now().isoformat()
        ).dict()
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/distros")
async def get_distros():
    """获取WSL发行版列表"""
    try:
        logger.info("API调用: 获取WSL发行版列表")
        
        # 尝试从缓存获取
        cache_key = "distros_list"
        cached_data = await database_manager.get_cached_data(cache_key)
        
        if cached_data is not None:
            logger.info("从缓存获取发行版列表")
            return ApiResponse(
                success=True,
                data=cached_data,
                timestamp=datetime.now().isoformat()
            ).dict()
        
        if not await wsl_service.is_wsl_available():
            raise HTTPException(
                status_code=503,
                detail="WSL不可用，请确保WSL已正确安装并启动"
            )
        
        distros = await wsl_service.get_distros()
        logger.info(f"获取到 {len(distros)} 个发行版")
        
        # 缓存结果
        await database_manager.set_cached_data(cache_key, distros)
        
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
        
        # 尝试从缓存获取
        cache_key = f"processes_{distro_name}"
        cached_data = await database_manager.get_cached_data(cache_key)
        
        if cached_data is not None:
            logger.info(f"从缓存获取 {distro_name} 进程列表")
            processing_time = time.time() - start_time
            await database_manager.record_performance_metric("process_fetch_time_cached", processing_time)
            return ApiResponse(
                success=True,
                data=cached_data,
                timestamp=datetime.now().isoformat()
            ).dict()
        
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
        
        result_data = {
            "processes": processes,
            "statistics": statistics,
            "count": total_processes,
            "distro": distro_name,
            "cache_source": "database"
        }
        
        # 缓存结果
        await database_manager.set_cached_data(cache_key, result_data)
        
        # 记录性能指标
        await database_manager.record_performance_metric("process_fetch_time", processing_time)
        await database_manager.record_performance_metric("process_count", total_processes)
        
        # 如果是MySQL，记录进程历史
        if database_type == "mysql" and hasattr(database_manager, 'record_process_history'):
            await database_manager.record_process_history(distro_name, processes)
        
        return ApiResponse(
            success=True,
            data=result_data,
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
        
        system_data = {
            "wsl_available": wsl_available,
            "total_distros": len(distros),
            "running_distros": len(running_distros),
            "distros": distros,
            "database_type": database_type,
            "system_time": datetime.now().isoformat()
        }
        
        # 添加缓存信息
        if database_type == "mysql":
            try:
                cache_stats = await database_manager.get_cache_statistics()
                system_data["cache_statistics"] = cache_stats
            except:
                system_data["cache_statistics"] = {"error": "无法获取缓存统计"}
        
        return ApiResponse(
            success=True,
            data=system_data,
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
            "data": {
                "message": f"已连接到 {distro_name}",
                "distro": distro_name,
                "database_type": database_type
            },
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
                        "count": total_processes,
                        "database_type": database_type
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send_json(message)
                
                # 如果是MySQL，异步记录进程历史
                if database_type == "mysql" and hasattr(database_manager, 'record_process_history'):
                    asyncio.create_task(database_manager.record_process_history(distro_name, processes))
                
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
    print(f"🚀 启动WSL Process Monitor - {database_type.upper()}版本")
    print(f"📊 数据库类型: {database_type}")
    if database_type == "mysql":
        print("🔄 多级缓存: L1内存 + L2磁盘 + L3Redis模拟")
    
    uvicorn.run(
        "mysql_unified_server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
