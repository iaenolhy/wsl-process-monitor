#!/usr/bin/env python3
"""
WSL Process Monitor 项目设置脚本
自动化项目初始化和依赖安装
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, cwd=None, shell=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=shell,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def check_requirements():
    """检查系统要求"""
    print("检查系统要求...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 9):
        print(f"❌ Python版本过低: {python_version.major}.{python_version.minor}")
        print("需要Python 3.9或更高版本")
        return False
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查Node.js
    success, output = run_command("node --version")
    if not success:
        print("❌ Node.js未安装")
        return False
    print(f"✅ Node.js版本: {output.strip()}")
    
    # 检查npm
    success, output = run_command("npm --version")
    if not success:
        print("❌ npm未安装")
        return False
    print(f"✅ npm版本: {output.strip()}")
    
    # 检查WSL (仅Windows)
    if platform.system() == "Windows":
        success, output = run_command("wsl --version")
        if success:
            print("✅ WSL已安装")
        else:
            print("⚠️  WSL未安装或不可用")
    
    return True


def setup_backend():
    """设置后端环境"""
    print("\n设置后端环境...")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    
    # 创建虚拟环境
    print("创建Python虚拟环境...")
    success, output = run_command(
        f"{sys.executable} -m venv venv",
        cwd=backend_dir
    )
    if not success:
        print(f"❌ 创建虚拟环境失败: {output}")
        return False
    print("✅ 虚拟环境创建成功")
    
    # 激活虚拟环境并安装依赖
    if platform.system() == "Windows":
        pip_path = backend_dir / "venv" / "Scripts" / "pip"
    else:
        pip_path = backend_dir / "venv" / "bin" / "pip"
    
    print("安装Python依赖...")
    success, output = run_command(
        f"{pip_path} install -r requirements.txt",
        cwd=backend_dir
    )
    if not success:
        print(f"❌ 安装依赖失败: {output}")
        return False
    print("✅ Python依赖安装成功")
    
    return True


def setup_frontend():
    """设置前端环境"""
    print("\n设置前端环境...")
    
    frontend_dir = Path(__file__).parent.parent / "frontend"
    
    # 安装npm依赖
    print("安装npm依赖...")
    success, output = run_command("npm install", cwd=frontend_dir)
    if not success:
        print(f"❌ 安装依赖失败: {output}")
        return False
    print("✅ npm依赖安装成功")
    
    return True


def main():
    """主函数"""
    print("WSL Process Monitor 项目设置")
    print("=" * 40)
    
    # 检查系统要求
    if not check_requirements():
        print("\n❌ 系统要求检查失败")
        sys.exit(1)
    
    # 设置后端
    if not setup_backend():
        print("\n❌ 后端设置失败")
        sys.exit(1)
    
    # 设置前端
    if not setup_frontend():
        print("\n❌ 前端设置失败")
        sys.exit(1)
    
    print("\n🎉 项目设置完成!")
    print("\n启动说明:")
    print("后端: cd backend && uvicorn app.main:app --reload")
    print("前端: cd frontend && npm run dev")


if __name__ == "__main__":
    main()
