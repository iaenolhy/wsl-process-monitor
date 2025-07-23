"""
WebSocket处理模块
提供实时进程数据推送功能
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from ..services.wsl_service import WSLService
from ..services.process_service import ProcessService

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接: {distro_name: {websocket_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 监控任务: {distro_name: task}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        # 服务实例
        self.wsl_service = WSLService()
        self.process_service = ProcessService(self.wsl_service)
        # 连接计数器
        self._connection_counter = 0
    
    def _get_connection_id(self) -> str:
        """生成连接ID"""
        self._connection_counter += 1
        return f"conn_{self._connection_counter}_{datetime.now().timestamp()}"
    
    async def connect(self, websocket: WebSocket, distro_name: str) -> str:
        """建立WebSocket连接"""
        await websocket.accept()
        
        connection_id = self._get_connection_id()
        
        # 初始化发行版连接字典
        if distro_name not in self.active_connections:
            self.active_connections[distro_name] = {}
        
        # 添加连接
        self.active_connections[distro_name][connection_id] = websocket
        
        # 启动监控任务（如果还没有）
        if distro_name not in self.monitoring_tasks:
            task = asyncio.create_task(self._monitor_processes(distro_name))
            self.monitoring_tasks[distro_name] = task
        
        logger.info(f"WebSocket连接建立: {connection_id} -> {distro_name}")
        
        # 发送连接成功消息
        await self._send_to_connection(websocket, {
            "type": "connection",
            "data": {
                "status": "connected",
                "connection_id": connection_id,
                "distro": distro_name
            },
            "timestamp": datetime.now().isoformat()
        })
        
        return connection_id
    
    def disconnect(self, connection_id: str, distro_name: str):
        """断开WebSocket连接"""
        try:
            if distro_name in self.active_connections:
                if connection_id in self.active_connections[distro_name]:
                    del self.active_connections[distro_name][connection_id]
                    logger.info(f"WebSocket连接断开: {connection_id}")
                
                # 如果该发行版没有活跃连接了，停止监控任务
                if not self.active_connections[distro_name]:
                    del self.active_connections[distro_name]
                    
                    if distro_name in self.monitoring_tasks:
                        task = self.monitoring_tasks[distro_name]
                        task.cancel()
                        del self.monitoring_tasks[distro_name]
                        logger.info(f"停止监控任务: {distro_name}")
        
        except Exception as e:
            logger.error(f"断开连接时出错: {e}")
    
    async def _send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """向单个连接发送消息"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"发送消息失败: {e}")
    
    async def broadcast_to_distro(self, distro_name: str, message: Dict[str, Any]):
        """向指定发行版的所有连接广播消息"""
        if distro_name not in self.active_connections:
            return
        
        connections = list(self.active_connections[distro_name].values())
        if not connections:
            return
        
        # 并发发送消息
        tasks = []
        for websocket in connections:
            task = asyncio.create_task(self._send_to_connection(websocket, message))
            tasks.append(task)
        
        # 等待所有发送完成，忽略失败的连接
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _monitor_processes(self, distro_name: str):
        """监控进程变化并推送更新"""
        logger.info(f"开始监控进程: {distro_name}")
        
        previous_processes = {}
        refresh_interval = 2  # 默认2秒刷新间隔
        
        try:
            while distro_name in self.active_connections:
                try:
                    # 获取当前进程列表
                    processes = await self.process_service.get_processes(distro_name, use_cache=False)
                    
                    # 构建进程字典用于比较
                    current_processes = {p["pid"]: p for p in processes}
                    
                    # 检测变化
                    changes = self._detect_process_changes(previous_processes, current_processes)
                    
                    # 获取统计信息
                    stats = self.process_service.get_process_statistics(distro_name)
                    
                    # 构建消息
                    message = {
                        "type": "processes",
                        "data": {
                            "processes": processes,
                            "statistics": stats,
                            "changes": changes,
                            "distro": distro_name,
                            "count": len(processes)
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # 广播消息
                    await self.broadcast_to_distro(distro_name, message)
                    
                    # 更新上一次的进程列表
                    previous_processes = current_processes
                    
                except Exception as e:
                    logger.error(f"监控进程时出错: {e}")
                    
                    # 发送错误消息
                    error_message = {
                        "type": "error",
                        "data": {
                            "error": str(e),
                            "distro": distro_name
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.broadcast_to_distro(distro_name, error_message)
                
                # 等待下次刷新
                await asyncio.sleep(refresh_interval)
                
        except asyncio.CancelledError:
            logger.info(f"监控任务被取消: {distro_name}")
        except Exception as e:
            logger.error(f"监控任务异常: {e}")
    
    def _detect_process_changes(self, previous: Dict[int, Dict], current: Dict[int, Dict]) -> Dict[str, Any]:
        """检测进程变化"""
        changes = {
            "new_processes": [],
            "terminated_processes": [],
            "updated_processes": []
        }
        
        try:
            # 检测新进程
            for pid, process in current.items():
                if pid not in previous:
                    changes["new_processes"].append(process)
            
            # 检测终止的进程
            for pid, process in previous.items():
                if pid not in current:
                    changes["terminated_processes"].append(process)
            
            # 检测更新的进程（CPU或内存使用率变化显著）
            for pid, process in current.items():
                if pid in previous:
                    prev_process = previous[pid]
                    
                    # 检查CPU使用率变化
                    cpu_change = abs(process.get("cpu_percent", 0) - prev_process.get("cpu_percent", 0))
                    memory_change = abs(process.get("memory_rss", 0) - prev_process.get("memory_rss", 0))
                    
                    # 如果变化超过阈值，标记为更新
                    if cpu_change > 5.0 or memory_change > 1024:  # CPU变化>5% 或 内存变化>1MB
                        changes["updated_processes"].append(process)
        
        except Exception as e:
            logger.warning(f"检测进程变化时出错: {e}")
        
        return changes

# 全局连接管理器实例
manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, distro_name: str):
    """WebSocket端点处理函数"""
    connection_id = None
    
    try:
        # 建立连接
        connection_id = await manager.connect(websocket, distro_name)
        
        # 保持连接并处理消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理客户端消息
                await handle_client_message(websocket, message, distro_name)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager._send_to_connection(websocket, {
                    "type": "error",
                    "data": {"error": "Invalid JSON format"},
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"处理WebSocket消息时出错: {e}")
                await manager._send_to_connection(websocket, {
                    "type": "error",
                    "data": {"error": str(e)},
                    "timestamp": datetime.now().isoformat()
                })
    
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
    
    finally:
        # 清理连接
        if connection_id:
            manager.disconnect(connection_id, distro_name)

async def handle_client_message(websocket: WebSocket, message: Dict[str, Any], distro_name: str):
    """处理客户端消息"""
    try:
        message_type = message.get("type")
        
        if message_type == "ping":
            # 心跳检测
            await manager._send_to_connection(websocket, {
                "type": "pong",
                "data": {"timestamp": datetime.now().isoformat()},
                "timestamp": datetime.now().isoformat()
            })
        
        elif message_type == "refresh":
            # 强制刷新
            processes = await manager.process_service.get_processes(distro_name, use_cache=False)
            stats = manager.process_service.get_process_statistics(distro_name)
            
            await manager._send_to_connection(websocket, {
                "type": "processes",
                "data": {
                    "processes": processes,
                    "statistics": stats,
                    "distro": distro_name,
                    "count": len(processes)
                },
                "timestamp": datetime.now().isoformat()
            })
        
        else:
            logger.warning(f"未知的消息类型: {message_type}")
    
    except Exception as e:
        logger.error(f"处理客户端消息失败: {e}")
        await manager._send_to_connection(websocket, {
            "type": "error",
            "data": {"error": str(e)},
            "timestamp": datetime.now().isoformat()
        })
