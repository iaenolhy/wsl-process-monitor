# 开发文档

## 项目概述

WSL Process Monitor 是一个用于监控Windows Subsystem for Linux (WSL)进程的工具，采用前后端分离架构。

## 技术栈

### 后端
- **Python 3.9+**: 主要编程语言
- **FastAPI**: Web框架，提供RESTful API和WebSocket支持
- **Pydantic**: 数据验证和序列化
- **uvicorn**: ASGI服务器
- **asyncio**: 异步编程支持

### 前端
- **Vue 3**: 前端框架
- **TypeScript**: 类型安全的JavaScript
- **Element Plus**: UI组件库
- **Vite**: 构建工具
- **Pinia**: 状态管理

## 开发环境设置

### 后端设置

1. 创建Python虚拟环境：
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 启动开发服务器：
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 前端设置

1. 安装Node.js依赖：
```bash
cd frontend
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

## API文档

启动后端服务后，可以访问以下地址查看API文档：
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## 项目结构说明

```
wsl-process-monitor/
├── backend/                  # Python后端
│   ├── app/
│   │   ├── main.py          # FastAPI应用入口
│   │   ├── models/          # 数据模型
│   │   ├── services/        # 业务逻辑服务
│   │   └── api/             # API路由
│   ├── requirements.txt     # Python依赖
│   └── pyproject.toml       # 项目配置
├── frontend/                # Vue3前端
│   ├── src/
│   │   ├── components/      # Vue组件
│   │   ├── views/           # 页面视图
│   │   ├── router/          # 路由配置
│   │   └── stores/          # Pinia状态管理
│   ├── package.json         # Node.js依赖
│   └── vite.config.ts       # Vite配置
├── shared/                  # 共享类型定义
│   ├── types.ts             # TypeScript类型
│   └── types.py             # Python类型
├── docs/                    # 项目文档
├── tests/                   # 测试文件
└── scripts/                 # 构建脚本
```

## 开发规范

### 代码风格
- Python: 使用Black格式化，遵循PEP 8
- TypeScript: 使用ESLint和Prettier
- 提交信息: 使用约定式提交格式

### 类型安全
- 前后端共享类型定义在`shared/`目录中
- 确保TypeScript和Python类型定义保持同步

### 错误处理
- 所有API调用都应该有适当的错误处理
- 用户友好的错误消息
- 详细的日志记录

## 测试

### 后端测试
```bash
cd backend
pytest
```

### 前端测试
```bash
cd frontend
npm run test
```

## 构建和部署

### 后端构建
```bash
cd backend
pip install build
python -m build
```

### 前端构建
```bash
cd frontend
npm run build
```

## 常见问题

### WSL相关问题
1. 确保WSL已正确安装
2. 检查WSL版本兼容性
3. 验证WSL发行版状态

### 开发环境问题
1. 确保Python版本 >= 3.9
2. 确保Node.js版本 >= 16
3. 检查端口占用情况
