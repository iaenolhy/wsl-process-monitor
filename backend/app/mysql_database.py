#!/usr/bin/env python3
"""
MySQL数据库管理器 - 根据用户要求实现MySQL缓存多级缓存
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import pickle
import aiofiles
from contextlib import asynccontextmanager

# MySQL异步驱动
try:
    import aiomysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("⚠️ aiomysql未安装，请运行: pip install aiomysql")

logger = logging.getLogger(__name__)

class MySQLDatabaseManager:
    """MySQL数据库管理器 - 支持多级缓存"""
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 3306,
                 user: str = "root",
                 password: str = "",
                 database: str = "wsl_monitor",
                 cache_dir: str = "cache"):
        
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.cache_dir = cache_dir
        
        # 多级缓存
        self.cache_l1: Dict[str, Any] = {}  # L1: 内存缓存
        self.cache_l2_dir = os.path.join(cache_dir, "l2_cache")  # L2: 磁盘缓存
        self.cache_l3_redis: Dict[str, Any] = {}  # L3: Redis缓存（模拟）
        
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(seconds=30)
        
        # 连接池
        self.pool = None
        
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.cache_l2_dir, exist_ok=True)
        
    async def initialize(self):
        """初始化MySQL数据库和连接池"""
        if not MYSQL_AVAILABLE:
            raise ImportError("MySQL支持未安装，请运行: pip install aiomysql")
        
        try:
            # 创建连接池
            self.pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                charset='utf8mb4',
                autocommit=True,
                maxsize=10,
                minsize=1
            )
            
            # 创建数据库表
            await self._create_tables()
            logger.info(f"MySQL数据库初始化成功: {self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            logger.error(f"MySQL数据库初始化失败: {e}")
            # 如果MySQL不可用，回退到SQLite
            logger.info("回退到SQLite数据库...")
            from .database import DatabaseManager
            self.fallback_db = DatabaseManager()
            await self.fallback_db.initialize()
            raise
    
    async def _create_tables(self):
        """创建MySQL数据库表"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                
                # 进程历史表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS process_history (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        distro_name VARCHAR(100) NOT NULL,
                        pid INT NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        user_name VARCHAR(100) NOT NULL,
                        cpu_percent DECIMAL(5,2) DEFAULT 0,
                        memory_rss BIGINT DEFAULT 0,
                        memory_vsz BIGINT DEFAULT 0,
                        command TEXT,
                        status VARCHAR(10),
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_distro_time (distro_name, recorded_at),
                        INDEX idx_pid_time (pid, recorded_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 系统统计表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_stats (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        distro_name VARCHAR(100) NOT NULL,
                        total_processes INT DEFAULT 0,
                        running_processes INT DEFAULT 0,
                        total_cpu_percent DECIMAL(8,2) DEFAULT 0,
                        total_memory_mb DECIMAL(12,2) DEFAULT 0,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_distro_time (distro_name, recorded_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 操作日志表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS operation_logs (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        operation_type VARCHAR(50) NOT NULL,
                        distro_name VARCHAR(100),
                        target_pid INT,
                        operation_data JSON,
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        user_agent VARCHAR(255),
                        ip_address VARCHAR(45),
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_operation_time (operation_type, recorded_at),
                        INDEX idx_distro_time (distro_name, recorded_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 性能指标表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        metric_name VARCHAR(100) NOT NULL,
                        metric_value DECIMAL(15,4) NOT NULL,
                        metric_unit VARCHAR(20) DEFAULT '',
                        tags JSON,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_metric_time (metric_name, recorded_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 缓存元数据表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cache_metadata (
                        cache_key VARCHAR(255) PRIMARY KEY,
                        cache_level TINYINT NOT NULL COMMENT '1=L1, 2=L2, 3=L3',
                        data_size BIGINT DEFAULT 0,
                        hit_count BIGINT DEFAULT 0,
                        miss_count BIGINT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        INDEX idx_level_expires (cache_level, expires_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
    
    @asynccontextmanager
    async def get_connection(self):
        """获取MySQL连接"""
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        conn = None
        try:
            conn = await self.pool.acquire()
            yield conn
        except Exception as e:
            logger.error(f"MySQL连接错误: {e}")
            raise
        finally:
            if conn:
                await self.pool.release(conn)
    
    async def record_process_history(self, distro_name: str, processes: List[Dict[str, Any]]):
        """记录进程历史到MySQL"""
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    # 批量插入进程历史
                    values = []
                    for process in processes:
                        values.append((
                            distro_name,
                            process.get('pid', 0),
                            process.get('name', ''),
                            process.get('user', ''),
                            process.get('cpu_percent', 0),
                            process.get('rss', 0),
                            process.get('vsz', 0),
                            process.get('command', ''),
                            process.get('stat', ''),
                            datetime.now()
                        ))
                    
                    if values:
                        await cursor.executemany("""
                            INSERT INTO process_history 
                            (distro_name, pid, name, user_name, cpu_percent, memory_rss, 
                             memory_vsz, command, status, recorded_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, values)
                        
                        logger.debug(f"记录了 {len(values)} 个进程历史到MySQL")
                        
        except Exception as e:
            logger.error(f"记录进程历史失败: {e}")
    
    async def record_performance_metric(self, metric_name: str, metric_value: float, 
                                      metric_unit: str = "", tags: Dict[str, Any] = None):
        """记录性能指标到MySQL"""
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute("""
                        INSERT INTO performance_metrics 
                        (metric_name, metric_value, metric_unit, tags, recorded_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        metric_name,
                        metric_value,
                        metric_unit,
                        json.dumps(tags or {}),
                        datetime.now()
                    ))
                    
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
    
    async def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """多级缓存获取数据"""
        
        # L1缓存（内存）
        if cache_key in self.cache_l1 and self._is_cache_valid(cache_key):
            await self._update_cache_stats(cache_key, 1, hit=True)
            logger.debug(f"L1缓存命中: {cache_key}")
            return self.cache_l1[cache_key]
        
        # L2缓存（磁盘）
        l2_data = await self._get_l2_cache(cache_key)
        if l2_data is not None:
            # 回填到L1缓存
            self.cache_l1[cache_key] = l2_data
            self.cache_timestamps[cache_key] = datetime.now()
            await self._update_cache_stats(cache_key, 2, hit=True)
            logger.debug(f"L2缓存命中: {cache_key}")
            return l2_data
        
        # L3缓存（Redis模拟）
        if cache_key in self.cache_l3_redis:
            data = self.cache_l3_redis[cache_key]
            # 回填到L1和L2缓存
            self.cache_l1[cache_key] = data
            self.cache_timestamps[cache_key] = datetime.now()
            await self._set_l2_cache(cache_key, data)
            await self._update_cache_stats(cache_key, 3, hit=True)
            logger.debug(f"L3缓存命中: {cache_key}")
            return data
        
        # 所有缓存都未命中
        await self._update_cache_stats(cache_key, 1, hit=False)
        return None
    
    async def set_cached_data(self, cache_key: str, data: Any):
        """多级缓存设置数据"""
        
        # 设置到所有缓存级别
        self.cache_l1[cache_key] = data
        self.cache_timestamps[cache_key] = datetime.now()
        
        # 异步设置L2缓存
        await self._set_l2_cache(cache_key, data)
        
        # 设置L3缓存
        self.cache_l3_redis[cache_key] = data
        
        # 记录缓存元数据
        await self._record_cache_metadata(cache_key, data)
        
        # 清理过期缓存
        await self._cleanup_expired_cache()
    
    async def _get_l2_cache(self, cache_key: str) -> Optional[Any]:
        """获取L2磁盘缓存"""
        try:
            cache_file = os.path.join(self.cache_l2_dir, f"{cache_key}.pkl")
            if os.path.exists(cache_file):
                # 检查文件修改时间
                file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
                if datetime.now() - file_time < self.cache_ttl:
                    async with aiofiles.open(cache_file, 'rb') as f:
                        content = await f.read()
                        return pickle.loads(content)
            return None
        except Exception as e:
            logger.error(f"L2缓存读取失败: {e}")
            return None
    
    async def _set_l2_cache(self, cache_key: str, data: Any):
        """设置L2磁盘缓存"""
        try:
            cache_file = os.path.join(self.cache_l2_dir, f"{cache_key}.pkl")
            async with aiofiles.open(cache_file, 'wb') as f:
                content = pickle.dumps(data)
                await f.write(content)
        except Exception as e:
            logger.error(f"L2缓存写入失败: {e}")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache_timestamps:
            return False
        
        return datetime.now() - self.cache_timestamps[cache_key] < self.cache_ttl
    
    async def _update_cache_stats(self, cache_key: str, cache_level: int, hit: bool):
        """更新缓存统计"""
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    if hit:
                        await cursor.execute("""
                            INSERT INTO cache_metadata (cache_key, cache_level, hit_count)
                            VALUES (%s, %s, 1)
                            ON DUPLICATE KEY UPDATE 
                            hit_count = hit_count + 1,
                            updated_at = CURRENT_TIMESTAMP
                        """, (cache_key, cache_level))
                    else:
                        await cursor.execute("""
                            INSERT INTO cache_metadata (cache_key, cache_level, miss_count)
                            VALUES (%s, %s, 1)
                            ON DUPLICATE KEY UPDATE 
                            miss_count = miss_count + 1,
                            updated_at = CURRENT_TIMESTAMP
                        """, (cache_key, cache_level))
                        
        except Exception as e:
            logger.error(f"更新缓存统计失败: {e}")
    
    async def _record_cache_metadata(self, cache_key: str, data: Any):
        """记录缓存元数据"""
        try:
            data_size = len(pickle.dumps(data))
            expires_at = datetime.now() + self.cache_ttl
            
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute("""
                        INSERT INTO cache_metadata 
                        (cache_key, cache_level, data_size, expires_at)
                        VALUES (%s, 1, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                        data_size = %s,
                        expires_at = %s,
                        updated_at = CURRENT_TIMESTAMP
                    """, (cache_key, data_size, expires_at, data_size, expires_at))
                    
        except Exception as e:
            logger.error(f"记录缓存元数据失败: {e}")
    
    async def _cleanup_expired_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        
        # 清理L1缓存
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if now - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            self.cache_l1.pop(key, None)
            self.cache_timestamps.pop(key, None)
        
        # 清理L2缓存文件
        try:
            for filename in os.listdir(self.cache_l2_dir):
                if filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_l2_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if now - file_time > self.cache_ttl:
                        os.remove(file_path)
        except Exception as e:
            logger.error(f"清理L2缓存失败: {e}")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute("""
                        SELECT 
                            cache_level,
                            COUNT(*) as cache_count,
                            SUM(hit_count) as total_hits,
                            SUM(miss_count) as total_misses,
                            SUM(data_size) as total_size
                        FROM cache_metadata 
                        GROUP BY cache_level
                    """)
                    
                    results = await cursor.fetchall()
                    
                    stats = {
                        "cache_levels": {},
                        "total_l1_keys": len(self.cache_l1),
                        "total_l3_keys": len(self.cache_l3_redis)
                    }
                    
                    for row in results:
                        level = f"L{row[0]}"
                        stats["cache_levels"][level] = {
                            "cache_count": row[1],
                            "total_hits": row[2],
                            "total_misses": row[3],
                            "total_size_bytes": row[4],
                            "hit_rate": row[2] / (row[2] + row[3]) if (row[2] + row[3]) > 0 else 0
                        }
                    
                    return stats
                    
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    async def cleanup(self):
        """清理资源"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("MySQL连接池已关闭")

# 全局MySQL数据库实例
mysql_db_manager = None

async def get_mysql_database() -> MySQLDatabaseManager:
    """依赖注入：获取MySQL数据库管理器"""
    global mysql_db_manager
    if mysql_db_manager is None:
        mysql_db_manager = MySQLDatabaseManager()
        await mysql_db_manager.initialize()
    return mysql_db_manager
