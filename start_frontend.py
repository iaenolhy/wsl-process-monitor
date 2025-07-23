#!/usr/bin/env python3
"""
前端启动脚本
"""

import sys
import subprocess
import os
from pathlib import Path

def check_node():
    """检查Node.js环境"""
    print("检查Node.js环境...")

    try:
        # 检查Node.js
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js版本: {result.stdout.strip()}")
        else:
            print("❌ Node.js未安装或无法访问")
            print_node_install_guide()
            return False

        # 检查npm
        npm_cmd = ["npm", "--version"]
        if os.name == 'nt':  # Windows
            npm_cmd = ["cmd", "/c", "npm", "--version"]

        result = subprocess.run(npm_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm版本: {result.stdout.strip()}")
        else:
            print("❌ npm未安装或无法访问")
            print_node_install_guide()
            return False

        return True

    except FileNotFoundError:
        print("❌ Node.js未安装或不在PATH中")
        print_node_install_guide()
        return False
    except Exception as e:
        print(f"❌ 检查Node.js时出错: {e}")
        print_node_install_guide()
        return False

def print_node_install_guide():
    """打印Node.js安装指南"""
    print("\n" + "=" * 50)
    print("Node.js安装指南")
    print("=" * 50)
    print("1. 访问 https://nodejs.org/en/download/")
    print("2. 下载适合您系统的LTS版本")
    print("3. 安装Node.js (会自动安装npm)")
    print("4. 重启命令行窗口")
    print("5. 验证安装: node --version")
    print("\n如果已安装但命令无法识别:")
    print("- 确保Node.js安装目录已添加到PATH环境变量")
    print("- Windows: 检查 %AppData%\\npm 是否在PATH中")
    print("- 重启命令行或计算机")
    print("=" * 50)

def install_deps():
    """安装前端依赖"""
    print("检查前端依赖...")
    
    current_dir = Path(__file__).parent
    frontend_dir = current_dir / "frontend"
    node_modules = frontend_dir / "node_modules"
    
    if not node_modules.exists():
        print("安装前端依赖...")
        try:
            npm_install_cmd = ["npm", "install"]
            if os.name == 'nt':  # Windows
                npm_install_cmd = ["cmd", "/c", "npm", "install"]

            subprocess.run(npm_install_cmd, cwd=frontend_dir, check=True)
            print("✅ 前端依赖安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 前端依赖安装失败: {e}")
            return False
    else:
        print("✅ 前端依赖已安装")
        return True

def start_frontend():
    """启动前端开发服务器"""
    print("启动前端开发服务器...")
    
    current_dir = Path(__file__).parent
    frontend_dir = current_dir / "frontend"
    
    try:
        print("执行命令: npm run dev")
        print(f"工作目录: {frontend_dir}")
        print("前端服务器启动中...")
        print("服务器地址: http://localhost:5173")
        print("按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        # 启动前端服务器
        npm_dev_cmd = ["npm", "run", "dev"]
        if os.name == 'nt':  # Windows
            npm_dev_cmd = ["cmd", "/c", "npm", "run", "dev"]

        subprocess.run(npm_dev_cmd, cwd=frontend_dir)
        
        return True
        
    except KeyboardInterrupt:
        print("\n前端服务器已停止")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动前端服务器失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 启动异常: {e}")
        return False

def main():
    """主函数"""
    print("WSL进程监控工具 - 前端启动器")
    print("=" * 40)
    
    # 检查Node.js环境
    if not check_node():
        return False
    
    # 安装依赖
    if not install_deps():
        return False
    
    # 启动前端
    return start_frontend()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)
