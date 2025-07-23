"""
API路由模块
定义所有的REST API端点
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..services.wsl_service import WSLService
from ..services.process_service import ProcessService

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

def get_wsl_service() -> WSLService:
    """获取WSL服务实例"""
    return WSLService()

def get_process_service() -> ProcessService:
    """获取进程服务实例"""
    wsl_svc = WSLService()
    return ProcessService(wsl_svc)

@router.get("/distros")
async def get_distros():
    """获取WSL发行版列表"""
    try:
        import subprocess
        import asyncio

        logger.info("直接检查WSL可用性...")

        # 直接在路由中检查WSL，避免依赖注入问题
        def check_wsl_direct():
            try:
                result = subprocess.run(
                    ["wsl", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            except:
                return False

        def get_distros_direct():
            try:
                result = subprocess.run(
                    ["wsl", "-l", "-v"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # 处理Windows的编码问题
                    try:
                        # 尝试UTF-8解码
                        output = result.stdout.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            # 尝试GBK解码（中文Windows）
                            output = result.stdout.decode('gbk')
                        except UnicodeDecodeError:
                            # 最后尝试忽略错误
                            output = result.stdout.decode('utf-8', errors='ignore')

                    return output
                return ""
            except:
                return ""

        # 在线程池中执行
        loop = asyncio.get_event_loop()
        is_available = await loop.run_in_executor(None, check_wsl_direct)

        logger.info(f"WSL可用性检查结果: {is_available}")

        if not is_available:
            logger.warning("WSL不可用，返回503错误")
            raise HTTPException(
                status_code=503,
                detail="WSL不可用，请确保WSL已正确安装并启动"
            )

        # 获取发行版列表
        distro_output = await loop.run_in_executor(None, get_distros_direct)

        # 解析发行版列表
        distros = []
        if distro_output:
            logger.info(f"原始发行版输出: {repr(distro_output[:200])}")

            lines = distro_output.strip().split('\n')
            logger.info(f"分割后的行数: {len(lines)}")

            # 跳过标题行，处理每一行
            for i, line in enumerate(lines[1:], 1):
                logger.info(f"处理第{i}行: {repr(line)}")

                if line.strip():
                    # 清理行内容，移除特殊字符
                    clean_line = line.replace('\x00', '').strip()
                    parts = clean_line.split()

                    logger.info(f"分割后的部分: {parts}")

                    if len(parts) >= 2:
                        name = parts[0].replace('*', '').strip()
                        state = parts[1] if len(parts) > 1 else "Unknown"
                        version = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 2
                        is_default = '*' in line

                        if name:  # 确保名称不为空
                            distros.append({
                                "name": name,
                                "state": state,
                                "version": version,
                                "is_default": is_default
                            })
                            logger.info(f"添加发行版: {name} ({state})")

        logger.info(f"获取到 {len(distros)} 个发行版")

        return {
            "success": True,
            "data": distros,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取发行版列表失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processes/{distro_name}")
async def get_processes(
    distro_name: str,
    refresh: bool = False,
    process_svc: ProcessService = Depends(get_process_service)
):
    """获取指定发行版的进程列表"""
    try:
        processes = await process_svc.get_processes(distro_name, use_cache=not refresh)
        
        # 获取统计信息
        stats = process_svc.get_process_statistics(distro_name)
        
        return {
            "success": True,
            "data": {
                "processes": processes,
                "statistics": stats,
                "distro": distro_name,
                "count": len(processes)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取进程列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/{distro_name}/kill")
async def kill_process(
    distro_name: str,
    request_data: Dict[str, Any],
    process_svc: ProcessService = Depends(get_process_service)
):
    """终止进程"""
    try:
        pids = request_data.get("pids", [])
        signal = request_data.get("signal", "SIGTERM")
        
        if not pids:
            raise HTTPException(status_code=400, detail="未指定要终止的进程ID")
        
        if signal not in ["SIGTERM", "SIGKILL"]:
            raise HTTPException(status_code=400, detail="不支持的信号类型")
        
        # 单个进程
        if len(pids) == 1:
            result = await process_svc.kill_process(distro_name, pids[0], signal)
        else:
            # 批量进程
            result = await process_svc.kill_multiple_processes(distro_name, pids, signal)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"终止进程失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processes/{distro_name}/statistics")
async def get_process_statistics(
    distro_name: str,
    process_svc: ProcessService = Depends(get_process_service)
):
    """获取进程统计信息"""
    try:
        stats = process_svc.get_process_statistics(distro_name)
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/status")
async def get_system_status(wsl_svc: WSLService = Depends(get_wsl_service)):
    """获取系统状态"""
    try:
        wsl_available = await wsl_svc.is_wsl_available()
        distros = await wsl_svc.get_distros() if wsl_available else []
        
        running_distros = [d for d in distros if d.get("state") == "Running"]
        
        return {
            "success": True,
            "data": {
                "wsl_available": wsl_available,
                "total_distros": len(distros),
                "running_distros": len(running_distros),
                "distros": distros,
                "system_time": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/system/distro/{distro_name}/set-current")
async def set_current_distro(
    distro_name: str,
    wsl_svc: WSLService = Depends(get_wsl_service)
):
    """设置当前使用的发行版"""
    try:
        success = wsl_svc.set_current_distro(distro_name)
        
        if success:
            return {
                "success": True,
                "message": f"已设置当前发行版为: {distro_name}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="设置发行版失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置当前发行版失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 健康检查端点
@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "WSL Process Monitor API",
            "version": "1.0.0"
        },
        "timestamp": datetime.now().isoformat()
    }
