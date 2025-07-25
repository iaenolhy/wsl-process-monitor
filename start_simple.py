#!/usr/bin/env python3
"""
WSL进程监控器 - 简化启动脚本
直接启动UNIFIED_SERVER，避免复杂的进程管理
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def main():
    """主函数"""
    print("🚀 WSL进程监控器 - 简化启动")
    print("=" * 40)
    
    # 检查UNIFIED_SERVER.py是否存在
    current_dir = Path(__file__).parent
    server_file = current_dir / "UNIFIED_SERVER.py"
    
    if not server_file.exists():
        print("❌ 找不到UNIFIED_SERVER.py文件")
        return False
    
    print(f"📁 工作目录: {current_dir}")
    print(f"📄 服务器文件: {server_file}")
    
    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    
    # 启动命令
    cmd = [sys.executable, str(server_file)]
    
    print(f"🔧 执行命令: {' '.join(cmd)}")
    print("=" * 40)
    print("🔄 启动服务器...")
    print("📝 服务器日志:")
    print("-" * 40)
    
    try:
        # 直接运行，不捕获输出
        result = subprocess.run(
            cmd,
            cwd=current_dir,
            env=env
        )
        
        print("-" * 40)
        print(f"🏁 服务器退出，返回码: {result.returncode}")
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断服务器")
        return True
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n❌ 启动失败")
            input("按Enter键退出...")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 异常: {e}")
        input("按Enter键退出...")
        sys.exit(1)
