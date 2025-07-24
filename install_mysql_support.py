#!/usr/bin/env python3
"""
MySQL支持安装脚本
安装MySQL相关依赖并配置数据库
"""

import subprocess
import sys
import os
import json
from pathlib import Path

def run_command(command, description=""):
    """运行命令并显示结果"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description}成功")
            if result.stdout.strip():
                print(f"   输出: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description}失败")
            if result.stderr.strip():
                print(f"   错误: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description}异常: {e}")
        return False

def install_mysql_dependencies():
    """安装MySQL依赖"""
    print("📦 安装MySQL依赖包")
    print("=" * 40)
    
    dependencies = [
        ("aiomysql", "MySQL异步驱动"),
        ("aiofiles", "异步文件操作"),
        ("pymysql", "MySQL同步驱动（备用）")
    ]
    
    success_count = 0
    
    for package, description in dependencies:
        if run_command(f"pip install {package}", f"安装{description}"):
            success_count += 1
    
    print(f"\n📊 依赖安装结果: {success_count}/{len(dependencies)} 成功")
    return success_count == len(dependencies)

def create_mysql_config():
    """创建MySQL配置文件"""
    print("\n⚙️ 创建MySQL配置文件")
    print("=" * 40)
    
    config_data = {
        "database": {
            "type": "mysql",
            "sqlite_path": "wsl_monitor.db",
            "mysql_host": "localhost",
            "mysql_port": 3306,
            "mysql_user": "root",
            "mysql_password": "",
            "mysql_database": "wsl_monitor",
            "cache_ttl_seconds": 30
        },
        "server": {
            "host": "127.0.0.1",
            "port": 8000,
            "log_level": "info"
        },
        "wsl": {
            "default_distro": "",
            "command_timeout": 30,
            "process_refresh_interval": 2
        },
        "cache": {
            "enable_multilevel": True,
            "l1_max_size": 1000,
            "l2_max_size_mb": 100,
            "l3_max_size": 5000
        }
    }
    
    try:
        config_file = "backend/app/config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ MySQL配置文件已创建: {config_file}")
        print("📝 请根据实际情况修改MySQL连接参数")
        return True
        
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False

def create_mysql_database():
    """创建MySQL数据库"""
    print("\n🗄️ 创建MySQL数据库")
    print("=" * 40)
    
    print("📝 请确保MySQL服务器已启动")
    
    # 提示用户手动创建数据库
    print("""
请在MySQL中执行以下命令创建数据库:

1. 连接到MySQL:
   mysql -u root -p

2. 创建数据库:
   CREATE DATABASE wsl_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

3. 创建用户（可选）:
   CREATE USER 'wsl_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON wsl_monitor.* TO 'wsl_user'@'localhost';
   FLUSH PRIVILEGES;

4. 退出MySQL:
   EXIT;
""")
    
    response = input("是否已完成数据库创建? (y/n): ").lower().strip()
    return response == 'y'

def test_mysql_connection():
    """测试MySQL连接"""
    print("\n🔍 测试MySQL连接")
    print("=" * 40)
    
    try:
        # 尝试导入并测试连接
        import aiomysql
        import asyncio
        
        async def test_connection():
            try:
                # 读取配置
                config_file = "backend/app/config.json"
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    db_config = config["database"]
                    
                    # 测试连接
                    conn = await aiomysql.connect(
                        host=db_config["mysql_host"],
                        port=db_config["mysql_port"],
                        user=db_config["mysql_user"],
                        password=db_config["mysql_password"],
                        db=db_config["mysql_database"],
                        charset='utf8mb4'
                    )
                    
                    # 测试查询
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                        result = await cursor.fetchone()
                    
                    conn.close()
                    
                    if result and result[0] == 1:
                        print("✅ MySQL连接测试成功")
                        return True
                    else:
                        print("❌ MySQL连接测试失败")
                        return False
                        
                else:
                    print("❌ 配置文件不存在")
                    return False
                    
            except Exception as e:
                print(f"❌ MySQL连接测试失败: {e}")
                return False
        
        return asyncio.run(test_connection())
        
    except ImportError:
        print("❌ aiomysql未安装，无法测试连接")
        return False

def create_startup_scripts():
    """创建启动脚本"""
    print("\n📜 创建启动脚本")
    print("=" * 40)
    
    # Windows批处理脚本
    bat_script = """@echo off
echo 🚀 启动WSL Process Monitor - MySQL版本
echo =====================================

echo 检查MySQL依赖...
python -c "import aiomysql; print('✅ MySQL依赖正常')" 2>nul
if errorlevel 1 (
    echo ❌ MySQL依赖缺失，请运行 install_mysql_support.py
    pause
    exit /b 1
)

echo 启动MySQL版本服务器...
python mysql_unified_server.py

pause
"""
    
    # Shell脚本
    sh_script = """#!/bin/bash
echo "🚀 启动WSL Process Monitor - MySQL版本"
echo "====================================="

echo "检查MySQL依赖..."
python3 -c "import aiomysql; print('✅ MySQL依赖正常')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ MySQL依赖缺失，请运行 python3 install_mysql_support.py"
    exit 1
fi

echo "启动MySQL版本服务器..."
python3 mysql_unified_server.py
"""
    
    try:
        # 创建Windows脚本
        with open("start_mysql_server.bat", 'w', encoding='utf-8') as f:
            f.write(bat_script)
        print("✅ Windows启动脚本: start_mysql_server.bat")
        
        # 创建Shell脚本
        with open("start_mysql_server.sh", 'w', encoding='utf-8') as f:
            f.write(sh_script)
        
        # 设置执行权限
        try:
            os.chmod("start_mysql_server.sh", 0o755)
        except:
            pass
        
        print("✅ Linux/Mac启动脚本: start_mysql_server.sh")
        return True
        
    except Exception as e:
        print(f"❌ 创建启动脚本失败: {e}")
        return False

def main():
    """主函数"""
    print("🎯 WSL Process Monitor - MySQL支持安装")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 安装步骤
    steps = [
        ("安装MySQL依赖", install_mysql_dependencies),
        ("创建MySQL配置", create_mysql_config),
        ("创建启动脚本", create_startup_scripts)
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        print(f"\n📋 步骤: {step_name}")
        if step_func():
            success_count += 1
        else:
            print(f"⚠️ {step_name}失败，但可以继续")
    
    # 数据库创建（手动步骤）
    print(f"\n📋 步骤: 创建MySQL数据库")
    if create_mysql_database():
        success_count += 1
        
        # 测试连接
        print(f"\n📋 步骤: 测试MySQL连接")
        if test_mysql_connection():
            success_count += 1
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 安装总结")
    print("=" * 50)
    
    total_steps = len(steps) + 2  # 包括数据库创建和连接测试
    
    if success_count >= total_steps - 1:  # 允许一个步骤失败
        print("🎉 MySQL支持安装成功!")
        print("\n🚀 启动方式:")
        print("1. Windows: 双击 start_mysql_server.bat")
        print("2. Linux/Mac: ./start_mysql_server.sh")
        print("3. 手动: python mysql_unified_server.py")
        
        print("\n📝 配置文件:")
        print("- 配置文件: backend/app/config.json")
        print("- 请根据实际情况修改MySQL连接参数")
        
        print("\n🌐 访问地址:")
        print("- 前端界面: http://localhost:5173")
        print("- 后端API: http://127.0.0.1:8000")
        print("- API文档: http://127.0.0.1:8000/docs")
        print("- 缓存统计: http://127.0.0.1:8000/api/cache/stats")
        
    else:
        print("⚠️ 安装过程中遇到问题")
        print("请检查错误信息并手动解决")
        print("\n🔧 常见问题:")
        print("1. MySQL服务器未启动")
        print("2. MySQL连接参数错误")
        print("3. 权限不足")
        print("4. 网络连接问题")
    
    return success_count >= total_steps - 1

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 安装异常: {e}")
        sys.exit(1)
