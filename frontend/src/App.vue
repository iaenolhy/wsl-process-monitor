<template>
  <div id="app">
    <el-container class="app-container">
      <el-header class="app-header">
        <h1>WSL Process Monitor</h1>
        <div class="header-actions">
          <el-button type="primary" @click="checkConnection">
            <el-icon><Connection /></el-icon>
            检查连接
          </el-button>
        </div>
      </el-header>
      
      <el-main class="app-main">
        <router-view />
      </el-main>
      
      <el-footer class="app-footer">
        <div class="status-bar">
          <span>状态: {{ connectionStatus }}</span>
          <span>版本: v1.0.0</span>
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection } from '@element-plus/icons-vue'

const connectionStatus = ref('未连接')

const checkConnection = async () => {
  try {
    const response = await fetch('/api/status')
    const data = await response.json()
    
    if (data.success) {
      connectionStatus.value = '已连接'
      ElMessage.success('连接成功')
    } else {
      connectionStatus.value = '连接失败'
      ElMessage.error('连接失败: ' + data.error)
    }
  } catch (error) {
    connectionStatus.value = '连接失败'
    ElMessage.error('无法连接到后端服务')
  }
}

onMounted(() => {
  checkConnection()
})
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #409eff;
  color: white;
  padding: 0 20px;
}

.app-header h1 {
  margin: 0;
  font-size: 24px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.app-main {
  padding: 20px;
  background-color: #f5f5f5;
}

.app-footer {
  background-color: #f0f0f0;
  border-top: 1px solid #ddd;
  padding: 10px 20px;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #666;
}
</style>
