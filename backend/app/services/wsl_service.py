"""
WSL服务模块
负责与WSL系统交互，获取发行版信息和执行命令
"""

import subprocess
import re
import asyncio
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import logging

# 设置日志
logger = logging.getLogger(__name__)

class WSLService:
    """WSL服务类"""
    
    def __init__(self):
        self.current_distro: Optional[str] = None
        self._distro_cache: Dict[str, Any] = {}
        self._cache_timeout = 30  # 缓存30秒
        
    async def is_wsl_available(self) -> bool:
        """检查WSL是否可用"""
        try:
            # 使用run_in_executor来避免uvicorn异步上下文问题
            import subprocess
            import asyncio

            def check_wsl():
                try:
                    result = subprocess.run(
                        ["wsl", "--version"],
                        capture_output=True,
                        timeout=10
                    )
                    logger.info(f"WSL版本检查返回码: {result.returncode}")

                    # 处理输出编码
                    if result.stdout:
                        try:
                            stdout_str = result.stdout.decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                stdout_str = result.stdout.decode('utf-16le')
                            except UnicodeDecodeError:
                                stdout_str = result.stdout.decode('utf-8', errors='ignore')

                        # 清理输出
                        stdout_str = stdout_str.replace('\x00', '').strip()
                        logger.info(f"WSL版本输出: {stdout_str[:100]}")

                    if result.stderr:
                        try:
                            stderr_str = result.stderr.decode('utf-8')
                        except UnicodeDecodeError:
                            stderr_str = result.stderr.decode('utf-8', errors='ignore')
                        logger.info(f"WSL版本错误: {stderr_str[:100]}")

                    return result.returncode == 0
                except FileNotFoundError:
                    logger.error("WSL命令未找到")
                    return False
                except subprocess.TimeoutExpired:
                    logger.error("WSL命令超时")
                    return False
                except Exception as e:
                    logger.error(f"WSL命令异常: {e}")
                    return False

            # 在线程池中执行
            loop = asyncio.get_event_loop()
            is_available = await loop.run_in_executor(None, check_wsl)

            logger.info(f"WSL可用性检查结果: {is_available}")
            return is_available

        except Exception as e:
            logger.error(f"检查WSL可用性失败: {e}")
            return False
    
    async def get_distros(self) -> List[Dict[str, Any]]:
        """获取WSL发行版列表"""
        try:
            # 使用run_in_executor来避免uvicorn异步上下文问题
            import subprocess
            import asyncio

            def get_distro_list():
                try:
                    result = subprocess.run(
                        ["wsl", "-l", "-v"],
                        capture_output=True,
                        timeout=10
                    )
                    logger.info(f"WSL列表检查返回码: {result.returncode}")

                    if result.returncode == 0:
                        # 处理Windows下WSL的编码问题
                        output = ""
                        try:
                            # 首先尝试UTF-8
                            output = result.stdout.decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                # 尝试UTF-16 (Windows WSL常见)
                                output = result.stdout.decode('utf-16le')
                            except UnicodeDecodeError:
                                try:
                                    # 尝试GBK (中文Windows)
                                    output = result.stdout.decode('gbk')
                                except UnicodeDecodeError:
                                    # 最后忽略错误
                                    output = result.stdout.decode('utf-8', errors='ignore')

                        # 清理输出中的空字节和特殊字符
                        output = output.replace('\x00', '').replace('\r\n', '\n')

                        logger.info(f"WSL列表清理后输出: {repr(output[:200])}")
                        return output
                    else:
                        if result.stderr:
                            try:
                                stderr = result.stderr.decode('utf-8', errors='ignore')
                            except:
                                stderr = str(result.stderr)
                            logger.error(f"获取发行版列表失败: {stderr}")
                        return ""
                except Exception as e:
                    logger.error(f"获取发行版列表异常: {e}")
                    return ""

            # 在线程池中执行
            loop = asyncio.get_event_loop()
            stdout_str = await loop.run_in_executor(None, get_distro_list)

            if not stdout_str:
                return []

            logger.info(f"WSL发行版列表原始输出: {stdout_str[:200]}")
            return self._parse_distro_list(stdout_str)

        except Exception as e:
            logger.error(f"获取发行版列表异常: {e}")
            return []
    
    def _parse_distro_list(self, output: str) -> List[Dict[str, Any]]:
        """解析发行版列表输出"""
        distros = []
        lines = output.strip().split('\n')

        logger.info(f"解析发行版列表，总行数: {len(lines)}")

        # 跳过标题行
        for i, line in enumerate(lines[1:], 1):
            if not line.strip():
                continue

            logger.info(f"处理第{i}行: {repr(line)}")

            # 清理行内容，保留重要字符
            clean_line = line.strip()
            # 移除多余的空格，但保留基本结构
            clean_line = re.sub(r'\s+', ' ', clean_line)

            # 检查是否为默认发行版（以*开头）
            is_default = clean_line.startswith('*')
            if is_default:
                clean_line = clean_line[1:].strip()

            parts = clean_line.split()
            logger.info(f"分割后的部分: {parts}")

            if len(parts) >= 2:
                name = parts[0]
                state = parts[1] if len(parts) > 1 else "Unknown"
                version = 2  # 默认WSL2

                # 解析版本
                if len(parts) > 2:
                    try:
                        version = int(parts[2])
                    except ValueError:
                        version = 2

                if name:  # 确保名称不为空
                    distro = {
                        "name": name,
                        "state": state,
                        "version": version,
                        "is_default": is_default
                    }
                    distros.append(distro)
                    logger.info(f"添加发行版: {distro}")

        logger.info(f"总共解析出 {len(distros)} 个发行版")
        return distros
    
    async def execute_command(self, command: str, distro: Optional[str] = None) -> Tuple[bool, str, str]:
        """在WSL中执行命令"""
        try:
            target_distro = distro or self.current_distro
            if not target_distro:
                raise ValueError("未指定WSL发行版")
            
            cmd = ["wsl", "-d", target_distro, "--", "bash", "-c", command]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            success = result.returncode == 0
            stdout_str = stdout.decode('utf-8', errors='ignore')
            stderr_str = stderr.decode('utf-8', errors='ignore')
            
            return success, stdout_str, stderr_str
            
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            return False, "", str(e)
    
    async def get_processes(self, distro: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取WSL进程列表"""
        try:
            # 使用ps命令获取详细进程信息
            command = "ps aux --no-headers"
            success, stdout, stderr = await self.execute_command(command, distro)
            
            if not success:
                logger.error(f"获取进程列表失败: {stderr}")
                return []
            
            return self._parse_process_list(stdout)
            
        except Exception as e:
            logger.error(f"获取进程列表异常: {e}")
            return []
    
    def _parse_process_list(self, output: str) -> List[Dict[str, Any]]:
        """解析进程列表输出"""
        processes = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                # ps aux输出格式: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                parts = line.split(None, 10)  # 最多分割10次，保留命令行完整
                
                if len(parts) >= 11:
                    user = parts[0]
                    pid = int(parts[1])
                    cpu_percent = float(parts[2])
                    memory_percent = float(parts[3])
                    vsz = int(parts[4])  # 虚拟内存大小(KB)
                    rss = int(parts[5])  # 物理内存大小(KB)
                    tty = parts[6]
                    status = parts[7]
                    start_time = parts[8]
                    time = parts[9]
                    command = parts[10] if len(parts) > 10 else ""
                    
                    # 提取进程名（命令的第一部分）
                    name = command.split()[0] if command else f"pid-{pid}"
                    if '/' in name:
                        name = name.split('/')[-1]  # 只保留文件名部分
                    
                    # 计算运行时间（简化版本）
                    running_time = self._format_running_time(time)
                    
                    processes.append({
                        "pid": pid,
                        "ppid": 0,  # ps aux不直接提供ppid，需要额外查询
                        "user": user,
                        "command": command,
                        "name": name,
                        "cpu_percent": cpu_percent,
                        "memory_rss": rss,
                        "memory_vsz": vsz,
                        "memory_percent": memory_percent,
                        "start_time": start_time,
                        "running_time": running_time,
                        "status": self._normalize_status(status),
                        "tty": tty
                    })
                    
            except (ValueError, IndexError) as e:
                logger.warning(f"解析进程行失败: {line[:50]}... 错误: {e}")
                continue
        
        return processes
    
    def _normalize_status(self, status: str) -> str:
        """标准化进程状态"""
        if not status:
            return 'S'
        
        # 取状态字符串的第一个字符
        first_char = status[0].upper()
        
        # 映射到标准状态
        status_map = {
            'R': 'R',  # Running
            'S': 'S',  # Sleeping
            'D': 'D',  # Disk sleep
            'Z': 'Z',  # Zombie
            'T': 'T',  # Stopped
            'I': 'I',  # Idle
        }
        
        return status_map.get(first_char, 'S')
    
    def _format_running_time(self, time_str: str) -> str:
        """格式化运行时间"""
        try:
            # time_str格式可能是 "HH:MM" 或 "MM:SS" 或 "days"
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    hours_or_minutes = int(parts[0])
                    minutes_or_seconds = int(parts[1])
                    
                    # 如果第一个数字很大，可能是分钟:秒
                    if hours_or_minutes > 24:
                        return f"{hours_or_minutes}m {minutes_or_seconds}s"
                    else:
                        return f"{hours_or_minutes}h {minutes_or_seconds}m"
            else:
                # 可能是天数或其他格式
                return time_str
                
        except (ValueError, IndexError):
            return time_str
        
        return time_str
    
    async def kill_process(self, pid: int, signal: str = "SIGTERM", distro: Optional[str] = None) -> Tuple[bool, str]:
        """终止进程"""
        try:
            # 验证信号类型
            if signal not in ["SIGTERM", "SIGKILL"]:
                return False, f"不支持的信号类型: {signal}"
            
            # 构造kill命令
            signal_num = "15" if signal == "SIGTERM" else "9"
            command = f"kill -{signal_num} {pid}"
            
            success, stdout, stderr = await self.execute_command(command, distro)
            
            if success:
                return True, f"进程 {pid} 已使用 {signal} 信号终止"
            else:
                return False, f"终止进程失败: {stderr}"
                
        except Exception as e:
            logger.error(f"终止进程异常: {e}")
            return False, str(e)
    
    def set_current_distro(self, distro_name: str) -> bool:
        """设置当前使用的发行版"""
        try:
            self.current_distro = distro_name
            logger.info(f"设置当前发行版: {distro_name}")
            return True
        except Exception as e:
            logger.error(f"设置发行版失败: {e}")
            return False

    async def verify_process_exists(self, distro_name: str, pid: int) -> bool:
        """验证进程是否存在"""
        try:
            command = f"ps -p {pid}"
            success, stdout, stderr = await self.execute_command(command, distro_name)

            return success and str(pid) in stdout

        except Exception as e:
            logger.warning(f"验证进程存在性失败: {e}")
            return False

    async def kill_process(self, distro_name: str, pid: int, signal: str = "SIGTERM") -> Dict[str, Any]:
        """终止WSL进程"""
        try:
            # 验证信号类型
            if signal not in ["SIGTERM", "SIGKILL"]:
                return {
                    "success": False,
                    "message": f"不支持的信号类型: {signal}",
                    "affected_pids": []
                }

            # 首先验证进程是否存在
            if not await self.verify_process_exists(distro_name, pid):
                return {
                    "success": False,
                    "message": f"进程 {pid} 不存在或已经结束",
                    "affected_pids": []
                }

            logger.info(f"尝试终止进程: PID={pid}, 信号={signal}")

            # 构造kill命令
            signal_num = "15" if signal == "SIGTERM" else "9"
            command = f"kill -{signal_num} {pid}"

            success, stdout, stderr = await self.execute_command(command, distro_name)

            if success:
                # 验证进程是否真的被终止
                await asyncio.sleep(0.5)  # 等待一下让进程有时间结束

                if not await self.verify_process_exists(distro_name, pid):
                    logger.info(f"进程 {pid} 已成功终止")
                    return {
                        "success": True,
                        "message": f"进程 {pid} 已使用 {signal} 信号终止",
                        "affected_pids": [pid]
                    }
                else:
                    logger.warning(f"进程 {pid} 终止命令执行成功但进程仍然存在")
                    return {
                        "success": False,
                        "message": f"进程 {pid} 终止命令执行成功但进程仍然存在，可能需要使用SIGKILL",
                        "affected_pids": []
                    }
            else:
                error_msg = stderr.strip() if stderr else "未知错误"

                # 特殊处理常见错误
                if "No such process" in error_msg:
                    return {
                        "success": False,
                        "message": f"进程 {pid} 在终止过程中已经结束",
                        "affected_pids": []
                    }
                elif "Operation not permitted" in error_msg:
                    return {
                        "success": False,
                        "message": f"没有权限终止进程 {pid}，可能是系统进程或属于其他用户",
                        "affected_pids": []
                    }
                else:
                    return {
                        "success": False,
                        "message": f"终止进程失败: {error_msg}",
                        "affected_pids": []
                    }

        except Exception as e:
            logger.error(f"终止进程异常: {e}")
            return {
                "success": False,
                "message": str(e),
                "affected_pids": []
            }
