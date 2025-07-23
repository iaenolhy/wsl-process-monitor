#!/usr/bin/env python3
"""
启动开发服务器脚本
"""

import sys
import os
import subprocess
from pathlib import Path

# 添加必要的路径到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
backend_dir = current_dir

# 确保所有必要的路径都在sys.path中
paths_to_add = [str(project_root), str(backend_dir), str(current_dir)]
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import pydantic
        print("✅ 依赖检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def start_server():
    """启动服务器"""
    if not check_dependencies():
        return False
    
    print("启动WSL Process Monitor后端服务器...")
    print("服务器地址: http://127.0.0.1:8000")
    print("API文档: http://127.0.0.1:8000/docs")
    print("按 Ctrl+C 停止服务器")
    print("-" * 50)
    
    try:
        # 使用uvicorn启动服务器
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动服务器失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    start_server()
