"""
进程服务模块
负责进程监控、管理和数据处理
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from .wsl_service import WSLService

logger = logging.getLogger(__name__)

class ProcessService:
    """进程服务类"""
    
    def __init__(self, wsl_service: WSLService):
        self.wsl_service = wsl_service
        self._process_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_timeout = 2  # 缓存2秒
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._process_history: Dict[str, List[Dict[str, Any]]] = {}
        
    async def get_processes(self, distro_name: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """获取进程列表"""
        try:
            # 检查缓存
            if use_cache and self._is_cache_valid(distro_name):
                return self._process_cache.get(distro_name, [])
            
            # 从WSL获取进程
            processes = await self.wsl_service.get_processes(distro_name)
            
            # 增强进程信息
            enhanced_processes = []
            for process in processes:
                enhanced_process = await self._enhance_process_info(process, distro_name)
                enhanced_processes.append(enhanced_process)
            
            # 更新缓存
            self._process_cache[distro_name] = enhanced_processes
            self._cache_timestamps[distro_name] = datetime.now()
            
            # 更新历史记录
            self._update_process_history(distro_name, enhanced_processes)
            
            return enhanced_processes
            
        except Exception as e:
            logger.error(f"获取进程列表失败: {e}")
            return []
    
    def _is_cache_valid(self, distro_name: str) -> bool:
        """检查缓存是否有效"""
        if distro_name not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[distro_name]
        return datetime.now() - cache_time < timedelta(seconds=self._cache_timeout)
    
    async def _enhance_process_info(self, process: Dict[str, Any], distro_name: str) -> Dict[str, Any]:
        """增强进程信息"""
        try:
            # 获取父进程ID
            if process.get("ppid", 0) == 0:
                ppid = await self._get_parent_pid(process["pid"], distro_name)
                process["ppid"] = ppid
            
            # 格式化时间戳
            process["start_time"] = self._format_start_time(process.get("start_time", ""))
            
            # 添加安全标记
            process["is_protected"] = self._is_protected_process(process)
            
            # 添加进程类型
            process["process_type"] = self._classify_process(process)
            
            return process
            
        except Exception as e:
            logger.warning(f"增强进程信息失败: {e}")
            return process
    
    async def _get_parent_pid(self, pid: int, distro_name: str) -> int:
        """获取父进程ID"""
        try:
            command = f"ps -o ppid= -p {pid}"
            success, stdout, stderr = await self.wsl_service.execute_command(command, distro_name)
            
            if success and stdout.strip():
                return int(stdout.strip())
            
        except (ValueError, Exception) as e:
            logger.debug(f"获取父进程ID失败: {e}")
        
        return 0
    
    def _format_start_time(self, start_time: str) -> str:
        """格式化启动时间为ISO格式"""
        try:
            if not start_time:
                return datetime.now().isoformat()
            
            # 这里可以根据实际的start_time格式进行解析
            # 目前返回当前时间的ISO格式
            return datetime.now().isoformat()
            
        except Exception:
            return datetime.now().isoformat()
    
    def _is_protected_process(self, process: Dict[str, Any]) -> bool:
        """判断是否为受保护进程"""
        pid = process.get("pid", 0)
        user = process.get("user", "").lower()
        name = process.get("name", "").lower()
        
        # 系统进程（PID < 100）
        if pid < 100:
            return True
        
        # 系统用户进程
        system_users = {"root", "daemon", "bin", "sys", "sync", "games", "man", "lp", "mail", "news", "uucp", "proxy", "www-data", "backup", "list", "irc", "gnats", "nobody", "systemd+"}
        if user in system_users:
            return True
        
        # 关键系统进程
        critical_processes = {"systemd", "kthreadd", "ksoftirqd", "migration", "rcu_", "watchdog", "init", "kernel"}
        if any(critical in name for critical in critical_processes):
            return True
        
        return False
    
    def _classify_process(self, process: Dict[str, Any]) -> str:
        """分类进程类型"""
        name = process.get("name", "").lower()
        command = process.get("command", "").lower()
        
        if any(sys_proc in name for sys_proc in ["systemd", "kernel", "kthread", "init"]):
            return "system"
        elif any(daemon in name for daemon in ["daemon", "service", "sshd", "cron"]):
            return "daemon"
        elif any(shell in name for shell in ["bash", "sh", "zsh", "fish"]):
            return "shell"
        elif "python" in name or "node" in name or "java" in name:
            return "application"
        else:
            return "user"
    
    def _update_process_history(self, distro_name: str, processes: List[Dict[str, Any]]):
        """更新进程历史记录"""
        try:
            if distro_name not in self._process_history:
                self._process_history[distro_name] = []
            
            # 保留最近10次的进程快照
            history = self._process_history[distro_name]
            history.append({
                "timestamp": datetime.now().isoformat(),
                "process_count": len(processes),
                "processes": [p["pid"] for p in processes]
            })
            
            # 只保留最近10次记录
            if len(history) > 10:
                history.pop(0)
                
        except Exception as e:
            logger.warning(f"更新进程历史失败: {e}")
    
    async def kill_process(self, distro_name: str, pid: int, signal: str = "SIGTERM") -> Dict[str, Any]:
        """终止进程"""
        try:
            # 获取进程信息
            processes = await self.get_processes(distro_name, use_cache=True)
            target_process = next((p for p in processes if p["pid"] == pid), None)
            
            if not target_process:
                return {
                    "success": False,
                    "message": f"进程 {pid} 不存在",
                    "affected_pids": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            # 检查是否为受保护进程
            if target_process.get("is_protected", False) and signal == "SIGKILL":
                return {
                    "success": False,
                    "message": f"进程 {pid} 是受保护的系统进程，不能强制终止",
                    "affected_pids": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            # 执行终止操作
            success, message = await self.wsl_service.kill_process(pid, signal, distro_name)
            
            # 记录操作日志
            await self._log_operation(distro_name, "kill", pid, signal, success, message)
            
            return {
                "success": success,
                "message": message,
                "affected_pids": [pid] if success else [],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"终止进程失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "affected_pids": [],
                "timestamp": datetime.now().isoformat()
            }
    
    async def kill_multiple_processes(self, distro_name: str, pids: List[int], signal: str = "SIGTERM") -> Dict[str, Any]:
        """批量终止进程"""
        try:
            results = []
            affected_pids = []
            
            for pid in pids:
                result = await self.kill_process(distro_name, pid, signal)
                results.append(result)
                if result["success"]:
                    affected_pids.extend(result["affected_pids"])
            
            success_count = sum(1 for r in results if r["success"])
            
            return {
                "success": success_count > 0,
                "message": f"成功终止 {success_count}/{len(pids)} 个进程",
                "affected_pids": affected_pids,
                "timestamp": datetime.now().isoformat(),
                "details": results
            }
            
        except Exception as e:
            logger.error(f"批量终止进程失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "affected_pids": [],
                "timestamp": datetime.now().isoformat()
            }
    
    async def _log_operation(self, distro_name: str, action: str, pid: int, signal: str, success: bool, message: str):
        """记录操作日志"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "distro": distro_name,
                "action": action,
                "pid": pid,
                "signal": signal,
                "success": success,
                "message": message
            }
            
            # 这里可以写入文件或数据库
            logger.info(f"操作日志: {log_entry}")
            
        except Exception as e:
            logger.warning(f"记录操作日志失败: {e}")
    
    def get_process_statistics(self, distro_name: str) -> Dict[str, Any]:
        """获取进程统计信息"""
        try:
            processes = self._process_cache.get(distro_name, [])
            
            if not processes:
                return {
                    "total": 0,
                    "running": 0,
                    "sleeping": 0,
                    "stopped": 0,
                    "zombie": 0,
                    "total_cpu": 0.0,
                    "total_memory": 0
                }
            
            stats = {
                "total": len(processes),
                "running": 0,
                "sleeping": 0,
                "stopped": 0,
                "zombie": 0,
                "total_cpu": 0.0,
                "total_memory": 0
            }
            
            for process in processes:
                status = process.get("status", "S")
                if status == "R":
                    stats["running"] += 1
                elif status == "S":
                    stats["sleeping"] += 1
                elif status == "T":
                    stats["stopped"] += 1
                elif status == "Z":
                    stats["zombie"] += 1
                
                stats["total_cpu"] += process.get("cpu_percent", 0.0)
                stats["total_memory"] += process.get("memory_rss", 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
