"""
优化的进程服务模块
高性能进程监控、管理和数据处理
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .wsl_service import WSLService
from ..database import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class ProcessMetrics:
    """进程性能指标"""
    total_processes: int
    running_processes: int
    total_cpu_percent: float
    total_memory_mb: float
    high_cpu_processes: int
    high_memory_processes: int

class OptimizedProcessService:
    """高性能进程服务类"""
    
    def __init__(self, wsl_service: WSLService, db_manager: Optional[DatabaseManager] = None):
        self.wsl_service = wsl_service
        self.db_manager = db_manager
        
        # 多级缓存
        self._l1_cache: Dict[str, List[Dict[str, Any]]] = {}  # 内存缓存
        self._l2_cache: Dict[str, List[Dict[str, Any]]] = {}  # 磁盘缓存
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(seconds=5)
        
        # 性能优化
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ProcessService")
        self._process_history: Dict[str, List[Dict[str, Any]]] = {}
        self._performance_metrics: Dict[str, List[float]] = {}
        
        # 监控任务管理
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._active_connections: Set[str] = set()
        
    async def get_processes_optimized(self, distro_name: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """获取进程列表（优化版本）"""
        start_time = time.time()
        
        try:
            # 检查多级缓存
            if use_cache:
                cached_data = await self._get_from_cache(distro_name)
                if cached_data:
                    await self._record_performance_metric("cache_hit_time", time.time() - start_time)
                    return cached_data
            
            # 从WSL获取进程（在线程池中执行）
            loop = asyncio.get_event_loop()
            processes = await loop.run_in_executor(
                self._thread_pool, 
                self._get_processes_sync, 
                distro_name
            )
            
            # 并行增强进程信息
            enhanced_processes = await self._enhance_processes_parallel(processes, distro_name)
            
            # 更新缓存
            await self._update_cache(distro_name, enhanced_processes)
            
            # 异步保存到数据库
            if self.db_manager:
                asyncio.create_task(self._save_to_database(distro_name, enhanced_processes))
            
            # 记录性能指标
            processing_time = time.time() - start_time
            await self._record_performance_metric("process_fetch_time", processing_time)
            await self._record_performance_metric("process_count", len(enhanced_processes))
            
            return enhanced_processes
            
        except Exception as e:
            logger.error(f"获取进程列表失败: {e}")
            await self._record_performance_metric("error_count", 1)
            return []
    
    def _get_processes_sync(self, distro_name: str) -> List[Dict[str, Any]]:
        """同步获取进程（在线程池中执行）"""
        import subprocess
        
        try:
            # 使用ps命令获取进程信息
            cmd = ["wsl", "-d", distro_name, "ps", "aux", "--no-headers"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                logger.error(f"获取进程列表失败: {result.stderr}")
                return []
            
            return self._parse_process_output(result.stdout)
            
        except Exception as e:
            logger.error(f"同步获取进程失败: {e}")
            return []
    
    def _parse_process_output(self, output: str) -> List[Dict[str, Any]]:
        """解析进程输出（优化版本）"""
        processes = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                # ps aux输出格式: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
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
                    
            except (ValueError, IndexError) as e:
                logger.debug(f"解析进程行失败: {line}, 错误: {e}")
                continue
        
        return processes
    
    async def _enhance_processes_parallel(self, processes: List[Dict[str, Any]], distro_name: str) -> List[Dict[str, Any]]:
        """并行增强进程信息"""
        if not processes:
            return []
        
        # 分批处理，避免过多并发
        batch_size = 20
        enhanced_processes = []
        
        for i in range(0, len(processes), batch_size):
            batch = processes[i:i + batch_size]
            
            # 并行处理当前批次
            tasks = [
                self._enhance_single_process(process, distro_name)
                for process in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤异常结果
            for result in batch_results:
                if isinstance(result, dict):
                    enhanced_processes.append(result)
        
        return enhanced_processes
    
    async def _enhance_single_process(self, process: Dict[str, Any], distro_name: str) -> Dict[str, Any]:
        """增强单个进程信息"""
        try:
            # 添加安全标记
            process['is_protected'] = self._is_protected_process(process)
            
            # 添加进程类型
            process['process_type'] = self._classify_process(process)
            
            # 格式化时间戳
            process['start_time'] = self._format_start_time(process.get('start', ''))
            
            # 添加内存使用量（MB）
            process['memory_mb'] = round(process.get('rss', 0) / 1024, 2)
            
            return process
            
        except Exception as e:
            logger.warning(f"增强进程信息失败: {e}")
            return process
    
    def _is_protected_process(self, process: Dict[str, Any]) -> bool:
        """判断是否为受保护进程（优化版本）"""
        pid = process.get('pid', 0)
        user = process.get('user', '').lower()
        name = process.get('name', '').lower()
        
        # 系统进程（PID < 100）
        if pid < 100:
            return True
        
        # 系统用户进程
        system_users = {
            'root', 'daemon', 'bin', 'sys', 'sync', 'games', 'man', 'lp', 
            'mail', 'news', 'uucp', 'proxy', 'www-data', 'backup', 'list', 
            'irc', 'gnats', 'nobody', 'systemd+'
        }
        if user in system_users:
            return True
        
        # 关键系统进程
        critical_processes = {
            'systemd', 'kthreadd', 'ksoftirqd', 'migration', 'rcu_', 
            'watchdog', 'init', 'kernel'
        }
        if any(critical in name for critical in critical_processes):
            return True
        
        return False
    
    def _classify_process(self, process: Dict[str, Any]) -> str:
        """分类进程类型"""
        name = process.get('name', '').lower()
        command = process.get('command', '').lower()
        
        if any(term in name or term in command for term in ['python', 'node', 'java', 'go']):
            return 'application'
        elif any(term in name for term in ['systemd', 'kernel', 'kthread']):
            return 'system'
        elif any(term in name for term in ['bash', 'sh', 'zsh', 'fish']):
            return 'shell'
        elif any(term in name for term in ['nginx', 'apache', 'mysql', 'postgres']):
            return 'service'
        else:
            return 'other'
    
    def _format_start_time(self, start_time: str) -> str:
        """格式化启动时间"""
        try:
            if not start_time:
                return datetime.now().isoformat()
            
            # 简单处理，实际可以根据需要解析具体格式
            return datetime.now().isoformat()
            
        except Exception:
            return datetime.now().isoformat()
    
    async def _get_from_cache(self, distro_name: str) -> Optional[List[Dict[str, Any]]]:
        """从多级缓存获取数据"""
        # L1缓存（内存）
        if distro_name in self._l1_cache and self._is_cache_valid(distro_name):
            return self._l1_cache[distro_name]
        
        # L2缓存（磁盘）
        if distro_name in self._l2_cache and self._is_cache_valid(distro_name):
            # 提升到L1缓存
            self._l1_cache[distro_name] = self._l2_cache[distro_name]
            return self._l2_cache[distro_name]
        
        return None
    
    async def _update_cache(self, distro_name: str, data: List[Dict[str, Any]]):
        """更新多级缓存"""
        self._l1_cache[distro_name] = data
        self._l2_cache[distro_name] = data
        self._cache_timestamps[distro_name] = datetime.now()
        
        # 清理过期缓存
        await self._cleanup_expired_cache()
    
    def _is_cache_valid(self, distro_name: str) -> bool:
        """检查缓存是否有效"""
        if distro_name not in self._cache_timestamps:
            return False
        
        return datetime.now() - self._cache_timestamps[distro_name] < self._cache_ttl
    
    async def _cleanup_expired_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if now - timestamp > self._cache_ttl
        ]
        
        for key in expired_keys:
            self._l1_cache.pop(key, None)
            self._l2_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
    
    async def _save_to_database(self, distro_name: str, processes: List[Dict[str, Any]]):
        """异步保存到数据库"""
        if not self.db_manager:
            return
        
        try:
            # 保存进程历史
            await self.db_manager.save_process_history(distro_name, processes)
            
            # 计算并保存统计信息
            stats = self.calculate_statistics(processes)
            await self.db_manager.save_system_stats(distro_name, stats.__dict__)
            
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")
    
    def calculate_statistics(self, processes: List[Dict[str, Any]]) -> ProcessMetrics:
        """计算进程统计信息（优化版本）"""
        if not processes:
            return ProcessMetrics(0, 0, 0.0, 0.0, 0, 0)
        
        total_processes = len(processes)
        running_processes = sum(1 for p in processes if p.get('stat', '').startswith('R'))
        total_cpu = sum(p.get('cpu_percent', 0) for p in processes)
        total_memory = sum(p.get('rss', 0) for p in processes) / 1024  # MB
        
        high_cpu_processes = sum(1 for p in processes if p.get('cpu_percent', 0) > 80)
        high_memory_processes = sum(1 for p in processes if p.get('rss', 0) > 1024 * 1024)  # > 1GB
        
        return ProcessMetrics(
            total_processes=total_processes,
            running_processes=running_processes,
            total_cpu_percent=round(total_cpu, 2),
            total_memory_mb=round(total_memory, 2),
            high_cpu_processes=high_cpu_processes,
            high_memory_processes=high_memory_processes
        )
    
    async def _record_performance_metric(self, metric_name: str, value: float):
        """记录性能指标"""
        if metric_name not in self._performance_metrics:
            self._performance_metrics[metric_name] = []
        
        self._performance_metrics[metric_name].append(value)
        
        # 保持最近100个指标
        if len(self._performance_metrics[metric_name]) > 100:
            self._performance_metrics[metric_name] = self._performance_metrics[metric_name][-100:]
        
        # 异步保存到数据库
        if self.db_manager:
            asyncio.create_task(
                self.db_manager.record_performance_metric(metric_name, value)
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        summary = {}
        
        for metric_name, values in self._performance_metrics.items():
            if values:
                summary[metric_name] = {
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
        
        return summary
    
    async def cleanup(self):
        """清理资源"""
        # 关闭线程池
        self._thread_pool.shutdown(wait=True)
        
        # 取消监控任务
        for task in self._monitoring_tasks.values():
            if not task.done():
                task.cancel()
        
        # 清理缓存
        self._l1_cache.clear()
        self._l2_cache.clear()
        self._cache_timestamps.clear()
