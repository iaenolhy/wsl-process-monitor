# WSL Process Monitor - 统一优化版本

一个高性能的WSL（Windows Subsystem for Linux）进程监控和管理工具，支持多级缓存、数据库持久化和实时监控。

## 🌟 功能特性

### 核心功能
- 🔄 **实时进程监控** - WebSocket实时数据推送
- 📊 **进程详细信息** - CPU、内存、状态等完整信息
- ⚡ **进程管理** - 安全的进程终止功能
- 🎨 **现代化界面** - Vue 3 + Element Plus响应式设计
- 📈 **数据可视化** - 动画图表和统计信息

### 性能优化
- 🚀 **多级缓存** - L1内存缓存 + L2磁盘缓存
- 💾 **数据持久化** - SQLite数据库存储历史数据
- ⚡ **高并发处理** - 线程池优化CPU密集型任务
- 📊 **性能监控** - 实时性能指标收集
- 🔧 **智能优化** - 批量并行处理大量进程数据

## 🛠 技术栈

### 后端 (Python)
- **FastAPI** - 高性能异步Web框架
- **SQLite + aiosqlite** - 异步数据库操作
- **WebSocket** - 实时数据推送
- **多线程处理** - CPU密集型任务优化
- **结构化日志** - 完整的错误追踪

### 前端 (Vue 3)
- **Vue 3 + TypeScript** - 现代化前端框架
- **Element Plus** - 企业级UI组件库
- **Vite** - 快速构建工具
- **响应式设计** - 完美适配桌面和移动端
- **动画效果** - 流畅的数据更新动画

## 🚀 快速开始

### 环境要求

- **Python 3.8+**
- **Node.js 16+**
- **WSL 2**
- **Windows 10/11**

### 一键启动

1. **克隆仓库**
```bash
git clone https://github.com/iaenolhy/wsl-process-monitor.git
cd wsl-process-monitor
```

2. **安装依赖**
```bash
# 后端依赖
cd backend
pip install -r requirements.txt
pip install aiosqlite

# 前端依赖
cd ../frontend
npm install
```

3. **启动服务**
```bash
# 启动后端 (在backend目录)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 启动前端 (在frontend目录)
npm run dev
```

4. **访问应用**
- 🌐 **前端界面**: http://localhost:5173
- 📚 **API文档**: http://127.0.0.1:8000/docs
- 🔍 **健康检查**: http://127.0.0.1:8000/health

## 📡 API文档

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 系统信息和功能特性 |
| `/health` | GET | 健康检查和系统状态 |
| `/api/distros` | GET | WSL发行版列表 |
| `/api/processes/{distro_name}` | GET | 进程列表（支持缓存） |
| `/api/processes/{distro_name}/kill` | POST | 安全进程终止 |
| `/api/system/status` | GET | 系统状态和统计 |
| `/api/performance` | GET | 性能指标摘要 |

### WebSocket实时推送

```javascript
// 连接WebSocket
const ws = new WebSocket('ws://127.0.0.1:8000/ws/processes/Ubuntu-22.04');

// 接收实时进程数据
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'processes') {
        console.log('进程数据:', data.data.processes);
        console.log('统计信息:', data.data.statistics);
    }
};
```

## 🎯 系统架构

### 数据库设计
- **process_history** - 进程历史记录
- **system_stats** - 系统统计数据
- **operation_logs** - 操作日志记录
- **performance_metrics** - 性能指标数据

### 缓存策略
- **L1缓存** - 内存中的快速访问
- **L2缓存** - 磁盘持久化缓存
- **TTL管理** - 自动过期清理
- **缓存预热** - 智能数据预加载

## 🔧 开发指南

### 项目结构
```
wsl-process-monitor/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── main.py         # 主应用入口
│   │   ├── database.py     # 数据库管理
│   │   ├── services/       # 业务服务
│   │   └── api/           # API路由
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # Vue组件
│   │   └── assets/        # 静态资源
│   └── package.json       # Node.js依赖
└── docs/                  # 文档
```

### 开发命令
```bash
# 开发模式启动后端
cd backend && python -m uvicorn app.main:app --reload

# 开发模式启动前端
cd frontend && npm run dev

# 构建前端
cd frontend && npm run build

# 运行测试
python -m pytest tests/
```

## 📊 性能特性

- ⚡ **响应时间**: API响应 < 500ms
- 🔄 **实时更新**: WebSocket 2秒刷新
- 💾 **缓存命中率**: > 80%
- 📈 **并发处理**: 支持多用户同时访问
- 🛡️ **错误恢复**: 自动重试和故障转移

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Element Plus](https://element-plus.org/) - Vue 3组件库
