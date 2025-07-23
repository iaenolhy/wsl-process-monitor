<template>
  <div class="home">
    <el-card class="welcome-card">
      <template #header>
        <div class="card-header">
          <span>欢迎使用 WSL Process Monitor</span>
        </div>
      </template>
      
      <div class="welcome-content">
        <p>这是一个用于监控WSL进程的工具，具有以下功能：</p>
        <ul>
          <li>实时监控WSL发行版中的进程</li>
          <li>支持进程搜索和筛选</li>
          <li>可以终止或强制终止进程</li>
          <li>提供详细的进程信息</li>
        </ul>
        
        <div class="status-info">
          <el-alert
            :title="statusMessage"
            :type="statusType"
            :closable="false"
            show-icon
          />
        </div>
        
        <div class="actions">
          <el-button type="primary" size="large" @click="showProcessMonitor">
            进入监控界面
          </el-button>
          <el-button size="large" @click="checkStatus">
            检查状态
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 进程监控组件 -->
    <div v-if="showMonitor">
      <ProcessMonitor />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import ProcessMonitor from '../components/ProcessMonitor.vue'

const statusMessage = ref('正在检查系统状态...')
const statusType = ref<'info' | 'success' | 'warning' | 'error'>('info')
const showMonitor = ref(false)

const checkStatus = async () => {
  try {
    const response = await fetch('/api/system/status')
    const data = await response.json()

    if (data.success) {
      const { wsl_available, total_distros, running_distros } = data.data
      if (wsl_available) {
        statusMessage.value = `WSL环境可用，发现 ${total_distros} 个发行版，${running_distros} 个正在运行`
        statusType.value = 'success'
      } else {
        statusMessage.value = 'WSL环境不可用，请检查WSL安装'
        statusType.value = 'warning'
      }
    } else {
      statusMessage.value = '无法连接到后端服务'
      statusType.value = 'error'
    }
  } catch (error) {
    statusMessage.value = '连接后端服务失败'
    statusType.value = 'error'
  }
}

const showProcessMonitor = () => {
  showMonitor.value = true
}

onMounted(() => {
  checkStatus()
})
</script>

<style scoped>
.home {
  max-width: 800px;
  margin: 0 auto;
}

.welcome-card {
  margin-bottom: 20px;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.welcome-content {
  line-height: 1.6;
}

.welcome-content ul {
  margin: 20px 0;
  padding-left: 20px;
}

.welcome-content li {
  margin: 8px 0;
}

.status-info {
  margin: 20px 0;
}

.actions {
  margin-top: 30px;
  text-align: center;
}

.actions .el-button {
  margin: 0 10px;
}
</style>
