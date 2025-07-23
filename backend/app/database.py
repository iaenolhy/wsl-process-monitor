#!/usr/bin/env python3
"""
数据库配置和连接管理
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import logging
import aiosqlite
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器 - 支持SQLite和多级缓存"""
    
    def __init__(self, db_path: str = "wsl_monitor.db"):
        self.db_path = db_path
        self.connection_pool: Dict[str, aiosqlite.Connection] = {}
        self.cache_l1: Dict[str, Any] = {}  # 内存缓存
        self.cache_l2: Dict[str, Any] = {}  # 磁盘缓存
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(seconds=30)  # 缓存TTL
        
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
                memory_percent REAL DEFAULT 0,
                status TEXT DEFAULT '',
                command TEXT DEFAULT '',
                start_time TEXT DEFAULT '',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_process_history_distro_time
            ON process_history(distro_name, recorded_at)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_process_history_pid_distro
            ON process_history(pid, distro_name)
        """)
        
        # 系统统计表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                distro_name TEXT NOT NULL,
                total_processes INTEGER DEFAULT 0,
                running_processes INTEGER DEFAULT 0,
                total_cpu_percent REAL DEFAULT 0,
                total_memory_mb REAL DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_system_stats_distro_time
            ON system_stats(distro_name, recorded_at)
        """)
        
        # 操作日志表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                distro_name TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                target_pid INTEGER,
                signal_type TEXT,
                success BOOLEAN DEFAULT FALSE,
                message TEXT DEFAULT '',
                user_agent TEXT DEFAULT '',
                ip_address TEXT DEFAULT '',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_operation_logs_distro_time
            ON operation_logs(distro_name, recorded_at)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_operation_logs_type_time
            ON operation_logs(operation_type, recorded_at)
        """)
        
        # 性能监控表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT DEFAULT '',
                tags TEXT DEFAULT '{}',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_performance_metrics_name_time
            ON performance_metrics(metric_name, recorded_at)
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
    
    async def save_process_history(self, distro_name: str, processes: List[Dict[str, Any]]):
        """保存进程历史数据"""
        try:
            async with self.get_connection() as db:
                # 批量插入进程数据
                process_data = []
                for process in processes:
                    process_data.append((
                        distro_name,
                        process.get('pid', 0),
                        process.get('name', ''),
                        process.get('user', ''),
                        process.get('cpu_percent', 0),
                        process.get('rss', 0),
                        process.get('memory_percent', 0),
                        process.get('stat', ''),
                        process.get('command', ''),
                        process.get('start', ''),
                        datetime.now().isoformat()
                    ))
                
                await db.executemany("""
                    INSERT INTO process_history 
                    (distro_name, pid, name, user_name, cpu_percent, memory_rss, 
                     memory_percent, status, command, start_time, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, process_data)
                
                await db.commit()
                
                # 清理旧数据（保留最近24小时）
                cutoff_time = datetime.now() - timedelta(hours=24)
                await db.execute("""
                    DELETE FROM process_history 
                    WHERE recorded_at < ?
                """, (cutoff_time.isoformat(),))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"保存进程历史失败: {e}")
    
    async def save_system_stats(self, distro_name: str, stats: Dict[str, Any]):
        """保存系统统计数据"""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT INTO system_stats 
                    (distro_name, total_processes, running_processes, 
                     total_cpu_percent, total_memory_mb, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    distro_name,
                    stats.get('total_processes', 0),
                    stats.get('running_processes', 0),
                    stats.get('total_cpu_percent', 0),
                    stats.get('total_memory_mb', 0),
                    datetime.now().isoformat()
                ))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"保存系统统计失败: {e}")
    
    async def log_operation(self, distro_name: str, operation_type: str, 
                           target_pid: Optional[int] = None, signal_type: Optional[str] = None,
                           success: bool = False, message: str = "", 
                           user_agent: str = "", ip_address: str = ""):
        """记录操作日志"""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT INTO operation_logs 
                    (distro_name, operation_type, target_pid, signal_type, 
                     success, message, user_agent, ip_address, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    distro_name, operation_type, target_pid, signal_type,
                    success, message, user_agent, ip_address,
                    datetime.now().isoformat()
                ))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")
    
    async def record_performance_metric(self, metric_name: str, metric_value: float, 
                                      metric_unit: str = "", tags: Dict[str, Any] = None):
        """记录性能指标"""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT INTO performance_metrics 
                    (metric_name, metric_value, metric_unit, tags, recorded_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    metric_name, metric_value, metric_unit,
                    json.dumps(tags or {}), datetime.now().isoformat()
                ))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
    
    # 多级缓存方法
    def _get_cache_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        return f"{prefix}:{':'.join(map(str, args))}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache_timestamps:
            return False
        
        return datetime.now() - self.cache_timestamps[cache_key] < self.cache_ttl
    
    async def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """获取缓存数据（L1 -> L2）"""
        # L1缓存（内存）
        if cache_key in self.cache_l1 and self._is_cache_valid(cache_key):
            return self.cache_l1[cache_key]
        
        # L2缓存（磁盘）
        if cache_key in self.cache_l2 and self._is_cache_valid(cache_key):
            # 提升到L1缓存
            self.cache_l1[cache_key] = self.cache_l2[cache_key]
            return self.cache_l2[cache_key]
        
        return None
    
    async def set_cached_data(self, cache_key: str, data: Any):
        """设置缓存数据"""
        self.cache_l1[cache_key] = data
        self.cache_l2[cache_key] = data
        self.cache_timestamps[cache_key] = datetime.now()
        
        # 清理过期缓存
        await self._cleanup_expired_cache()
    
    async def _cleanup_expired_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if now - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            self.cache_l1.pop(key, None)
            self.cache_l2.pop(key, None)
            self.cache_timestamps.pop(key, None)

# 全局数据库实例
db_manager = DatabaseManager()

async def get_database() -> DatabaseManager:
    """依赖注入：获取数据库管理器"""
    return db_manager
