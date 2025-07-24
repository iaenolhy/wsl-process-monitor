#!/usr/bin/env python3
"""
配置管理 - 支持MySQL和SQLite数据库切换
"""

import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"  # sqlite 或 mysql
    
    # SQLite配置
    sqlite_path: str = "wsl_monitor.db"
    
    # MySQL配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "wsl_monitor"
    
    # 缓存配置
    cache_ttl_seconds: int = 30
    cache_dir: str = "cache"
    enable_l1_cache: bool = True  # 内存缓存
    enable_l2_cache: bool = True  # 磁盘缓存
    enable_l3_cache: bool = True  # Redis缓存（模拟）

@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    log_level: str = "info"
    
    # CORS配置
    cors_origins: list = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173"
            ]

@dataclass
class WSLConfig:
    """WSL配置"""
    default_distro: str = ""
    command_timeout: int = 30
    process_refresh_interval: int = 2

@dataclass
class CacheConfig:
    """缓存配置"""
    enable_multilevel: bool = True
    l1_max_size: int = 1000  # L1缓存最大条目数
    l2_max_size_mb: int = 100  # L2缓存最大大小（MB）
    l3_max_size: int = 5000  # L3缓存最大条目数

class Config:
    """主配置类"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.server = ServerConfig()
        self.wsl = WSLConfig()
        self.cache = CacheConfig()
        
        # 从环境变量加载配置
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        
        # 数据库配置
        self.database.type = os.getenv("DB_TYPE", self.database.type)
        self.database.sqlite_path = os.getenv("SQLITE_PATH", self.database.sqlite_path)
        
        self.database.mysql_host = os.getenv("MYSQL_HOST", self.database.mysql_host)
        self.database.mysql_port = int(os.getenv("MYSQL_PORT", self.database.mysql_port))
        self.database.mysql_user = os.getenv("MYSQL_USER", self.database.mysql_user)
        self.database.mysql_password = os.getenv("MYSQL_PASSWORD", self.database.mysql_password)
        self.database.mysql_database = os.getenv("MYSQL_DATABASE", self.database.mysql_database)
        
        # 服务器配置
        self.server.host = os.getenv("SERVER_HOST", self.server.host)
        self.server.port = int(os.getenv("SERVER_PORT", self.server.port))
        self.server.log_level = os.getenv("LOG_LEVEL", self.server.log_level)
        
        # WSL配置
        self.wsl.default_distro = os.getenv("WSL_DEFAULT_DISTRO", self.wsl.default_distro)
        self.wsl.command_timeout = int(os.getenv("WSL_TIMEOUT", self.wsl.command_timeout))
        
        # 缓存配置
        self.cache.enable_multilevel = os.getenv("ENABLE_MULTILEVEL_CACHE", "true").lower() == "true"
        self.cache.l1_max_size = int(os.getenv("L1_CACHE_SIZE", self.cache.l1_max_size))
        self.cache.l2_max_size_mb = int(os.getenv("L2_CACHE_SIZE_MB", self.cache.l2_max_size_mb))
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        if self.database.type == "mysql":
            return f"mysql://{self.database.mysql_user}:{self.database.mysql_password}@{self.database.mysql_host}:{self.database.mysql_port}/{self.database.mysql_database}"
        else:
            return f"sqlite:///{self.database.sqlite_path}"
    
    def is_mysql_enabled(self) -> bool:
        """检查是否启用MySQL"""
        return self.database.type.lower() == "mysql"
    
    def is_sqlite_enabled(self) -> bool:
        """检查是否启用SQLite"""
        return self.database.type.lower() == "sqlite"
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return {
            "enable_multilevel": self.cache.enable_multilevel,
            "l1_max_size": self.cache.l1_max_size,
            "l2_max_size_mb": self.cache.l2_max_size_mb,
            "l3_max_size": self.cache.l3_max_size,
            "ttl_seconds": self.database.cache_ttl_seconds,
            "cache_dir": self.database.cache_dir
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "database": {
                "type": self.database.type,
                "sqlite_path": self.database.sqlite_path if self.is_sqlite_enabled() else None,
                "mysql_host": self.database.mysql_host if self.is_mysql_enabled() else None,
                "mysql_port": self.database.mysql_port if self.is_mysql_enabled() else None,
                "mysql_database": self.database.mysql_database if self.is_mysql_enabled() else None,
                "cache_ttl_seconds": self.database.cache_ttl_seconds
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "log_level": self.server.log_level
            },
            "wsl": {
                "default_distro": self.wsl.default_distro,
                "command_timeout": self.wsl.command_timeout,
                "process_refresh_interval": self.wsl.process_refresh_interval
            },
            "cache": {
                "enable_multilevel": self.cache.enable_multilevel,
                "l1_max_size": self.cache.l1_max_size,
                "l2_max_size_mb": self.cache.l2_max_size_mb,
                "l3_max_size": self.cache.l3_max_size
            }
        }

# 全局配置实例
config = Config()

def get_config() -> Config:
    """获取配置实例"""
    return config

def load_config_from_file(config_file: str = "config.json"):
    """从文件加载配置"""
    import json
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 更新配置
            if "database" in config_data:
                db_config = config_data["database"]
                config.database.type = db_config.get("type", config.database.type)
                config.database.sqlite_path = db_config.get("sqlite_path", config.database.sqlite_path)
                config.database.mysql_host = db_config.get("mysql_host", config.database.mysql_host)
                config.database.mysql_port = db_config.get("mysql_port", config.database.mysql_port)
                config.database.mysql_user = db_config.get("mysql_user", config.database.mysql_user)
                config.database.mysql_password = db_config.get("mysql_password", config.database.mysql_password)
                config.database.mysql_database = db_config.get("mysql_database", config.database.mysql_database)
            
            if "server" in config_data:
                server_config = config_data["server"]
                config.server.host = server_config.get("host", config.server.host)
                config.server.port = server_config.get("port", config.server.port)
                config.server.log_level = server_config.get("log_level", config.server.log_level)
            
            if "cache" in config_data:
                cache_config = config_data["cache"]
                config.cache.enable_multilevel = cache_config.get("enable_multilevel", config.cache.enable_multilevel)
                config.cache.l1_max_size = cache_config.get("l1_max_size", config.cache.l1_max_size)
                config.cache.l2_max_size_mb = cache_config.get("l2_max_size_mb", config.cache.l2_max_size_mb)
            
            print(f"✅ 配置已从 {config_file} 加载")
            
        except Exception as e:
            print(f"⚠️ 加载配置文件失败: {e}")
    else:
        print(f"⚠️ 配置文件 {config_file} 不存在，使用默认配置")

def save_config_to_file(config_file: str = "config.json"):
    """保存配置到文件"""
    import json
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"✅ 配置已保存到 {config_file}")
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")

# 示例配置文件内容
EXAMPLE_CONFIG = {
    "database": {
        "type": "mysql",  # 或 "sqlite"
        "sqlite_path": "wsl_monitor.db",
        "mysql_host": "localhost",
        "mysql_port": 3306,
        "mysql_user": "root",
        "mysql_password": "your_password",
        "mysql_database": "wsl_monitor",
        "cache_ttl_seconds": 30
    },
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
        "log_level": "info"
    },
    "wsl": {
        "default_distro": "Ubuntu-22.04",
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

def create_example_config():
    """创建示例配置文件"""
    import json
    
    config_file = "config.example.json"
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(EXAMPLE_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"✅ 示例配置文件已创建: {config_file}")
        print("📝 请复制为 config.json 并修改相应配置")
    except Exception as e:
        print(f"❌ 创建示例配置文件失败: {e}")

if __name__ == "__main__":
    # 创建示例配置文件
    create_example_config()
    
    # 显示当前配置
    print("\n📋 当前配置:")
    import json
    print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))
