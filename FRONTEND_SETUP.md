# 前端环境设置指南

## 概述

WSL进程监控工具的前端使用Vue3 + Element Plus构建，需要Node.js环境支持。

## 环境要求

- **Node.js**: 16.0.0 或更高版本
- **npm**: 8.0.0 或更高版本
- **操作系统**: Windows 10/11, macOS, Linux

## 安装步骤

### 1. 安装Node.js

#### Windows用户
1. 访问 [Node.js官网](https://nodejs.org/en/download/)
2. 下载Windows Installer (.msi)
3. 运行安装程序，选择"Add to PATH"选项
4. 重启命令行窗口

#### 验证安装
```bash
node --version
npm --version
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 启动前端开发服务器

#### 方法一：使用启动脚本
```bash
python start_frontend.py
```

#### 方法二：手动启动
```bash
cd frontend
npm run dev
```

## 常见问题

### Q: 提示"node不是内部或外部命令"
**A**: Node.js未正确安装或未添加到PATH
- 重新安装Node.js，确保选择"Add to PATH"
- 重启命令行窗口
- 检查环境变量PATH中是否包含Node.js路径

### Q: npm install失败
**A**: 网络或权限问题
```bash
# 清理npm缓存
npm cache clean --force

# 使用淘宝镜像
npm config set registry https://registry.npmmirror.com

# 重新安装
npm install
```

### Q: 端口5173被占用
**A**: 修改端口或关闭占用进程
```bash
# 查看端口占用
netstat -ano | findstr :5173

# 或者修改vite.config.ts中的端口配置
```

### Q: 前端启动后无法访问后端API
**A**: 检查后端服务状态
- 确保后端服务在http://127.0.0.1:8000运行
- 检查CORS配置
- 查看浏览器控制台错误信息

## 开发模式

### 热重载
前端开发服务器支持热重载，修改代码后会自动刷新页面。

### 代理配置
前端已配置代理，API请求会自动转发到后端：
- `/api/*` → `http://127.0.0.1:8000/api/*`
- `/ws/*` → `ws://127.0.0.1:8000/ws/*`

### 构建生产版本
```bash
cd frontend
npm run build
```

## 项目结构

```
frontend/
├── src/
│   ├── main.ts              # 应用入口
│   ├── App.vue              # 根组件
│   ├── components/          # 组件目录
│   │   └── ProcessMonitor.vue
│   ├── views/               # 页面目录
│   │   └── Home.vue
│   └── router/              # 路由配置
│       └── index.ts
├── public/                  # 静态资源
├── package.json             # 项目配置
├── vite.config.ts           # Vite配置
└── tsconfig.json            # TypeScript配置
```

## 技术栈说明

- **Vue 3**: 渐进式JavaScript框架
- **TypeScript**: 类型安全的JavaScript超集
- **Element Plus**: Vue 3的UI组件库
- **Vite**: 快速的前端构建工具
- **Vue Router**: Vue.js官方路由管理器
- **Pinia**: Vue的状态管理库

## 开发建议

1. **使用TypeScript**: 项目已配置TypeScript，建议充分利用类型检查
2. **组件化开发**: 将功能拆分为可复用的组件
3. **状态管理**: 复杂状态使用Pinia管理
4. **代码规范**: 遵循Vue 3 Composition API最佳实践

## 故障排除

如果遇到问题，请按以下顺序检查：

1. **检查Node.js版本**: `node --version`
2. **清理依赖**: `rm -rf node_modules && npm install`
3. **检查端口**: 确保5173端口未被占用
4. **查看错误日志**: 检查控制台输出
5. **重启服务**: 停止并重新启动开发服务器

## 获取帮助

- 查看控制台错误信息
- 检查网络连接
- 确认后端服务正常运行
- 参考Vue 3和Element Plus官方文档
