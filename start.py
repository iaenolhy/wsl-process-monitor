#!/usr/bin/env python3
"""
WSL进程监控器 - 主启动脚本
统一的启动入口，支持后端和前端的启动
"""

import sys
import os
import subprocess
import time
import requests
from pathlib import Path

def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print("🚀 WSL进程监控器 v2.0.0 - 统一启动器")
    print("=" * 60)
    print("这个脚本将启动后端服务并可选择启动前端")
    print()

def check_dependencies():
    """检查依赖"""
    print("🔍 检查依赖...")
    
    # 检查Python依赖
    required_packages = ['fastapi', 'uvicorn', 'websockets']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: 已安装")
        except ImportError:
            print(f"❌ {package}: 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ 缺少依赖: {', '.join(missing_packages)}")
        print("请运行: pip install fastapi uvicorn websockets")
        return False
    
    return True

def start_backend():
    """启动后端服务"""
    print("\n📡 启动后端服务...")
    
    current_dir = Path(__file__).parent
    server_file = current_dir / "UNIFIED_SERVER.py"
    
    if not server_file.exists():
        print("❌ 找不到UNIFIED_SERVER.py文件")
        return None
    
    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    
    # 启动命令
    cmd = [sys.executable, str(server_file)]
    
    print(f"执行命令: {' '.join(cmd)}")
    print(f"工作目录: {current_dir}")
    print()
    
    try:
        # 启动后台进程
        process = subprocess.Popen(
            cmd,
            cwd=current_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("✅ 后端进程已启动")
        print("⏳ 等待服务器启动...")
        
        return process
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return None

def wait_for_server(max_wait=30):
    """等待服务器启动"""
    print("🔍 检查服务器状态...")
    
    for i in range(max_wait):
        try:
            response = requests.get("http://127.0.0.1:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ 服务器启动成功！")
                return True
        except:
            pass
        
        print(f"⏳ 等待中... ({i+1}/{max_wait})")
        time.sleep(1)
    
    print("❌ 服务器启动超时")
    return False

def test_server_endpoints():
    """测试服务器端点"""
    print("\n🧪 测试服务器端点...")
    
    endpoints = [
        ("根路径", "http://127.0.0.1:8000/"),
        ("健康检查", "http://127.0.0.1:8000/health"),
        ("API文档", "http://127.0.0.1:8000/docs"),
        ("WSL发行版", "http://127.0.0.1:8000/api/distros"),
        ("系统状态", "http://127.0.0.1:8000/api/system/status")
    ]
    
    success_count = 0
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            status = "✅" if response.status_code == 200 else "⚠️"
            print(f"{status} {name}: {response.status_code}")
            if response.status_code == 200:
                success_count += 1
        except Exception as e:
            print(f"❌ {name}: 连接失败 - {e}")
    
    print(f"\n测试结果: {success_count}/{len(endpoints)} 个端点成功")
    return success_count == len(endpoints)

def show_access_info():
    """显示访问信息"""
    print("\n" + "=" * 60)
    print("🎉 WSL进程监控器启动成功！")
    print("=" * 60)
    print("📍 访问地址:")
    print("   • 主页: http://127.0.0.1:8000")
    print("   • API文档: http://127.0.0.1:8000/docs")
    print("   • 健康检查: http://127.0.0.1:8000/health")
    print("   • WSL发行版: http://127.0.0.1:8000/api/distros")
    print("   • 系统状态: http://127.0.0.1:8000/api/system/status")
    print("   • WebSocket: ws://127.0.0.1:8000/ws/processes/{distro_name}")
    print()
    print("🌐 前端界面:")
    print("   • 地址: http://localhost:5173")
    print("   • 启动: python start_frontend.py")
    print()
    print("⚠️ 停止服务器:")
    print("   • 按 Ctrl+C 或关闭此窗口")
    print("=" * 60)

def start_frontend_option():
    """询问是否启动前端"""
    print("\n❓ 是否同时启动前端服务？")
    print("1. 是，启动前端")
    print("2. 否，只运行后端")
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        print("\n🎨 启动前端服务...")
        try:
            current_dir = Path(__file__).parent
            frontend_script = current_dir / "start_frontend.py"
            
            if frontend_script.exists():
                subprocess.Popen([sys.executable, str(frontend_script)])
                print("✅ 前端服务启动中...")
                print("📍 前端地址: http://localhost:5173")
            else:
                print("❌ 找不到start_frontend.py文件")
                print("请手动运行: cd frontend && npm run dev")
            
        except Exception as e:
            print(f"❌ 前端启动失败: {e}")
            print("请手动运行: cd frontend && npm run dev")

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，无法继续")
        return False
    
    # 启动后端
    process = start_backend()
    if not process:
        print("❌ 无法启动后端服务")
        return False
    
    # 等待服务器启动
    if not wait_for_server():
        print("❌ 服务器启动失败")
        process.terminate()
        return False
    
    # 测试端点
    if not test_server_endpoints():
        print("⚠️ 部分端点测试失败，但服务器已启动")
    
    # 显示访问信息
    show_access_info()
    
    # 询问是否启动前端
    start_frontend_option()
    
    # 等待用户中断
    try:
        print("\n⌨️ 按 Ctrl+C 停止服务器...")
        while True:
            time.sleep(1)
            # 检查进程是否还在运行
            if process.poll() is not None:
                print("⚠️ 后端进程意外退出")
                break
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务器...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("✅ 服务器已停止")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("\n按Enter键退出...")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 启动器异常: {e}")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...")
        sys.exit(1)
