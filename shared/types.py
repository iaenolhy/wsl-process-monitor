"""
WSL进程监控工具的共享类型定义
这些类型在前端和后端之间保持一致
"""

from typing import List, Optional, Literal, Union
from pydantic import BaseModel
from datetime import datetime


class WSLProcess(BaseModel):
    pid: int
    ppid: int
    user: str
    command: str
    name: str
    cpu_percent: float
    memory_rss: int  # KB
    memory_vsz: int  # KB
    start_time: str  # ISO格式
    running_time: str  # 人类可读格式，如"2h 30m"
    status: Literal['R', 'S', 'D', 'Z', 'T', 'I']


class WSLDistro(BaseModel):
    name: str
    version: Literal[1, 2]
    state: Literal['Running', 'Stopped']
    is_default: bool


class ProcessOperation(BaseModel):
    action: Literal['kill', 'terminate']
    pids: List[int]
    signal: Literal['SIGTERM', 'SIGKILL']
    timestamp: str


class ProcessFilter(BaseModel):
    user: Optional[str] = None
    name: Optional[str] = None
    command: Optional[str] = None
    min_cpu: Optional[float] = None
    max_cpu: Optional[float] = None
    min_memory: Optional[int] = None
    max_memory: Optional[int] = None
    status: Optional[List[Literal['R', 'S', 'D', 'Z', 'T', 'I']]] = None


class WebSocketMessage(BaseModel):
    type: Literal['processes', 'error', 'connection', 'operation_result']
    data: Union[dict, list, str]
    timestamp: str


class AppSettings(BaseModel):
    refresh_interval: int = 2  # 1-10秒
    theme: Literal['light', 'dark'] = 'light'
    visible_columns: List[str] = [
        'pid', 'user', 'name', 'cpu_percent', 'memory_rss', 'status'
    ]
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 3


class OperationResult(BaseModel):
    success: bool
    message: str
    affected_pids: List[int]
    timestamp: str


class ApiResponse(BaseModel):
    success: bool
    data: Optional[Union[dict, list]] = None
    error: Optional[str] = None
    timestamp: str


class ProcessStats(BaseModel):
    total: int
    running: int
    sleeping: int
    stopped: int
    zombie: int
    total_cpu: float
    total_memory: int


# 常量定义
class ProcessStatus:
    RUNNING = 'R'
    SLEEPING = 'S'
    DISK_SLEEP = 'D'
    ZOMBIE = 'Z'
    STOPPED = 'T'
    IDLE = 'I'


class Signals:
    SIGTERM = 'SIGTERM'
    SIGKILL = 'SIGKILL'


# 配置常量
class Config:
    DEFAULT_REFRESH_INTERVAL = 2
    MIN_REFRESH_INTERVAL = 1
    MAX_REFRESH_INTERVAL = 10
    MAX_RECONNECT_ATTEMPTS = 3
    SYSTEM_PROCESS_PID_THRESHOLD = 100
    MAX_PROCESSES_PER_PAGE = 1000
