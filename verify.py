#!/usr/bin/env python3
"""
WSL进程监控器 - 验证脚本
验证所有功能是否正常工作
"""

import asyncio
import requests
import websockets
import json
import time

async def verify_system():
    """验证整个系统"""
    print("🔍 WSL进程监控器系统验证")
    print("=" * 50)
    
    # 1. 验证API端点
    print("1. 验证API端点...")
    api_success = verify_api_endpoints()
    
    if not api_success:
        print("❌ API验证失败")
        return False
    
    # 2. 验证WebSocket
    print("\n2. 验证WebSocket连接...")
    ws_success = await verify_websocket()
    
    if not ws_success:
        print("❌ WebSocket验证失败")
        return False
    
    print("\n" + "=" * 50)
    print("✅ 系统验证成功！所有功能正常工作")
    print("📍 访问地址:")
    print("   • API文档: http://127.0.0.1:8000/docs")
    print("   • 前端界面: http://localhost:5173")
    print("=" * 50)
    
    return True

def verify_api_endpoints():
    """验证API端点"""
    endpoints = [
        ("健康检查", "http://127.0.0.1:8000/health"),
        ("API状态", "http://127.0.0.1:8000/api/status"),  # 新增的端点
        ("WSL发行版", "http://127.0.0.1:8000/api/distros"),
        ("系统状态", "http://127.0.0.1:8000/api/system/status")
    ]
    
    success_count = 0
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {name}: 正常")
                success_count += 1
            else:
                print(f"   ❌ {name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ {name}: 连接失败")
    
    return success_count == len(endpoints)

async def verify_websocket():
    """验证WebSocket连接"""
    try:
        # 获取发行版
        response = requests.get("http://127.0.0.1:8000/api/distros", timeout=5)
        if response.status_code != 200:
            print("   ❌ 无法获取发行版列表")
            return False
        
        data = response.json()
        distros = data.get("data", [])
        
        if not distros:
            print("   ❌ 没有找到WSL发行版")
            return False
        
        # 使用第一个发行版测试
        test_distro = distros[0]['name']
        ws_url = f"ws://127.0.0.1:8000/ws/processes/{test_distro}"
        
        async with websockets.connect(ws_url) as websocket:
            print(f"   ✅ WebSocket连接成功: {test_distro}")
            
            # 等待连接消息
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            if data.get('type') == 'connection':
                print("   ✅ 连接消息接收成功")
            
            # 发送ping
            await websocket.send(json.dumps({"type": "ping"}))
            
            # 等待pong
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get('type') == 'pong':
                print("   ✅ ping/pong测试成功")
            
            # 等待进程数据
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(message)
            
            if data.get('type') == 'processes':
                processes = data.get('data', {}).get('processes', [])
                print(f"   ✅ 进程数据接收成功: {len(processes)} 个进程")
                return True
            
        return False
        
    except Exception as e:
        print(f"   ❌ WebSocket测试失败: {e}")
        return False

def main():
    """主函数"""
    print("等待服务器启动...")
    time.sleep(3)
    
    try:
        success = asyncio.run(verify_system())
        return success
    except Exception as e:
        print(f"❌ 验证异常: {e}")
        return False

if __name__ == "__main__":
    main()
