#!/usr/bin/env python3
"""
WSL Process Monitor - 服务器启动脚本
解决导入问题的统一启动入口
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent
backend_path = project_root / "backend"
app_path = backend_path / "app"

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(app_path))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wsl_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    try:
        logger.info("🚀 启动WSL Process Monitor服务器...")
        
        # 检查依赖
        try:
            import fastapi
            import uvicorn
            import aiosqlite
            logger.info("✅ 依赖检查通过")
        except ImportError as e:
            logger.error(f"❌ 缺少依赖: {e}")
            logger.info("请运行: pip install fastapi uvicorn aiosqlite")
            return False
        
        # 切换到app目录
        os.chdir(app_path)
        
        # 启动服务器
        import uvicorn
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 异常: {e}")
        sys.exit(1)
