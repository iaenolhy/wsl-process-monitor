<template>
  <div class="process-monitor">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="selectedDistro"
          placeholder="选择WSL发行版"
          @change="onDistroChange"
          style="width: 200px"
          :loading="isLoadingDistros"
          clearable
        >
          <el-option
            v-for="distro in distros"
            :key="`distro-${distro.name}`"
            :label="`${distro.name} (${distro.state})`"
            :value="distro.name"
            :disabled="distro.state !== 'Running'"
          />
        </el-select>
        
        <el-button
          :type="isMonitoring ? 'danger' : 'primary'"
          @click="toggleMonitoring"
          :disabled="!selectedDistro"
        >
          <el-icon><VideoPlay v-if="!isMonitoring" /><VideoPause v-else /></el-icon>
          {{ isMonitoring ? '停止监控' : '开始监控' }}
        </el-button>
        
        <el-button @click="refreshProcesses" :disabled="!selectedDistro">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      
      <div class="toolbar-right">
        <el-input
          v-model="searchText"
          placeholder="搜索进程..."
          style="width: 200px"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>
    
    <!-- 统计信息 -->
    <div class="statistics" v-if="statistics">
      <!-- 总进程数卡片 -->
      <el-card class="stat-card processes-card" shadow="hover">
        <div class="stat-item">
          <div class="stat-icon">
            <el-icon size="24"><Monitor /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-label">总进程数</span>
            <div class="stat-value-container">
              <span class="stat-value" :class="{ 'animate-number': isMonitoring }">
                {{ animatedTotalProcesses }}
              </span>
              <span class="stat-trend" v-if="processTrend !== 0">
                <el-icon :class="processTrend > 0 ? 'trend-up' : 'trend-down'">
                  <ArrowUp v-if="processTrend > 0" />
                  <ArrowDown v-else />
                </el-icon>
                {{ Math.abs(processTrend) }}
              </span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 运行中进程卡片 -->
      <el-card class="stat-card running-card" shadow="hover">
        <div class="stat-item">
          <div class="stat-icon">
            <el-icon size="24"><VideoPlay /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-label">运行中</span>
            <div class="stat-value-container">
              <span class="stat-value running" :class="{ 'animate-number': isMonitoring }">
                {{ animatedRunningProcesses }}
              </span>
              <el-progress
                :percentage="runningPercentage"
                :show-text="false"
                :stroke-width="4"
                color="#67c23a"
                class="mini-progress"
              />
            </div>
          </div>
        </div>
      </el-card>

      <!-- CPU使用率卡片 -->
      <el-card class="stat-card cpu-card" shadow="hover">
        <div class="stat-item">
          <div class="stat-icon">
            <el-icon size="24"><Cpu /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-label">CPU使用率</span>
            <div class="stat-value-container">
              <span class="stat-value" :class="{ 'animate-number': isMonitoring, 'high-usage': cpuUsage > 80 }">
                {{ animatedCpuUsage.toFixed(1) }}%
              </span>
              <el-progress
                type="circle"
                :percentage="Math.min(cpuUsage, 100)"
                :width="40"
                :stroke-width="4"
                :color="getCpuProgressColor(cpuUsage)"
                class="cpu-circle"
              />
            </div>
          </div>
        </div>
      </el-card>

      <!-- 内存使用卡片 -->
      <el-card class="stat-card memory-card" shadow="hover">
        <div class="stat-item">
          <div class="stat-icon">
            <el-icon size="24"><MemoryCard /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-label">总内存</span>
            <div class="stat-value-container">
              <span class="stat-value memory" :class="{ 'animate-number': isMonitoring }">
                {{ formatMemoryValue(animatedMemoryUsage) }}
              </span>
              <div class="memory-bar">
                <div class="memory-segments">
                  <div
                    v-for="i in 10"
                    :key="i"
                    class="memory-segment"
                    :class="{ 'active': i <= Math.ceil(memoryPercentage / 10) }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 进程表格 -->
    <div class="process-table">
      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-header">
            <h3>进程列表</h3>
            <div class="table-actions">
              <span class="process-count">共 {{ filteredProcesses.length }} 个进程</span>
              <el-button size="small" @click="refreshProcesses(true)">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          :data="filteredProcesses"
          style="width: 100%"
          height="500"
          @selection-change="onSelectionChange"
          stripe
          :header-cell-style="{ background: '#f8f9fa', color: '#495057' }"
          :row-class-name="getRowClassName"
        >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="pid" label="PID" width="80" sortable />
        
        <el-table-column prop="name" label="进程名" width="150" sortable>
          <template #default="{ row }">
            <span :class="{ 'protected-process': row.is_protected }">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="user" label="用户" width="100" sortable />
        
        <el-table-column prop="cpu_percent" label="CPU%" width="80" sortable>
          <template #default="{ row }">
            <el-progress
              :percentage="Math.min(row.cpu_percent || 0, 100)"
              :color="getCpuColor(row.cpu_percent || 0)"
              :show-text="false"
              style="width: 50px"
            />
            <span style="margin-left: 8px">{{ (row.cpu_percent || 0).toFixed(1) }}%</span>
          </template>
        </el-table-column>

        <el-table-column prop="rss" label="内存" width="100" sortable>
          <template #default="{ row }">
            {{ formatMemory(row.rss || 0) }}
          </template>
        </el-table-column>

        <el-table-column prop="stat" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.stat)">
              {{ getStatusText(row.stat) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="time" label="运行时间" width="100" />
        
        <el-table-column prop="command" label="命令" min-width="200" show-overflow-tooltip />
        
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="warning"
              @click="killProcess(row.pid, 'SIGTERM')"
              :disabled="row.is_protected"
            >
              终止
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="killProcess(row.pid, 'SIGKILL')"
              :disabled="row.is_protected"
            >
              强杀
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      </el-card>
    </div>
    
    <!-- 状态栏 -->
    <div class="status-bar">
      <span>总进程数: {{ processes.length }}</span>
      <span>筛选后: {{ filteredProcesses.length }}</span>
      <span>选中: {{ selectedProcesses.length }}</span>
      <span>连接状态: 
        <el-tag :type="connectionStatus === 'connected' ? 'success' : 'danger'">
          {{ connectionStatus === 'connected' ? '已连接' : '未连接' }}
        </el-tag>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, onErrorCaptured, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, VideoPause, Refresh, Search, Monitor, Cpu, MemoryCard, ArrowUp, ArrowDown } from '@element-plus/icons-vue'

// 响应式数据
const distros = ref<any[]>([])
const selectedDistro = ref<string>('')
const processes = ref<any[]>([])
const statistics = ref<any>(null)
const searchText = ref<string>('')
const selectedProcesses = ref<any[]>([])
const isMonitoring = ref<boolean>(false)
const connectionStatus = ref<string>('disconnected')
const websocket = ref<WebSocket | null>(null)
const isLoadingDistros = ref<boolean>(false)

// 动画相关数据
const animatedTotalProcesses = ref<number>(0)
const animatedRunningProcesses = ref<number>(0)
const animatedCpuUsage = ref<number>(0)
const animatedMemoryUsage = ref<number>(0)
const processTrend = ref<number>(0)
const previousStats = ref<any>(null)

// 计算属性
const filteredProcesses = computed(() => {
  if (!searchText.value) return processes.value

  const search = searchText.value.toLowerCase()
  return processes.value.filter(process =>
    process.name.toLowerCase().includes(search) ||
    process.user.toLowerCase().includes(search) ||
    process.command.toLowerCase().includes(search) ||
    process.pid.toString().includes(search)
  )
})

// 统计数据计算属性
const cpuUsage = computed(() => statistics.value?.total_cpu_percent || 0)
const memoryUsage = computed(() => statistics.value?.total_memory_mb || 0)
const totalProcesses = computed(() => statistics.value?.total_processes || 0)
const runningProcesses = computed(() => statistics.value?.running_processes || 0)

const runningPercentage = computed(() => {
  if (totalProcesses.value === 0) return 0
  return Math.round((runningProcesses.value / totalProcesses.value) * 100)
})

const memoryPercentage = computed(() => {
  // 假设系统总内存为8GB，可以根据实际情况调整
  const totalMemoryMB = 8 * 1024
  return Math.min((memoryUsage.value / totalMemoryMB) * 100, 100)
})

// 方法
const loadDistros = async () => {
  try {
    isLoadingDistros.value = true

    const response = await fetch('/api/distros')
    const data = await response.json()

    if (data.success && Array.isArray(data.data)) {
      // 使用nextTick确保DOM更新完成
      await nextTick()

      // 安全地更新distros数组，避免Vue响应式系统错误
      distros.value = [...data.data]

      // 等待Vue响应式系统更新完成
      await nextTick()

      // 自动选择第一个运行中的发行版
      const runningDistro = data.data.find((d: any) => d.state === 'Running')
      if (runningDistro && !selectedDistro.value) {
        selectedDistro.value = runningDistro.name

        // 等待选择器更新完成
        await nextTick()
      }
    } else {
      ElMessage.error('获取发行版列表失败: ' + (data.error || '数据格式错误'))
    }
  } catch (error) {
    console.error('加载发行版失败:', error)
    ElMessage.error('连接服务器失败: 网络错误')
  } finally {
    isLoadingDistros.value = false
  }
}

const onDistroChange = async (newDistro?: string) => {
  try {
    // 如果正在监控，先停止
    if (isMonitoring.value) {
      stopMonitoring()
    }

    // 等待停止完成
    await nextTick()

    // 清理当前数据
    processes.value = []
    statistics.value = null

    // 如果有新的发行版选择，可以在这里添加额外的处理
    if (newDistro) {
      console.log('切换到发行版:', newDistro)
    }
  } catch (error) {
    console.error('切换发行版时出错:', error)
  }
}

const toggleMonitoring = () => {
  if (isMonitoring.value) {
    stopMonitoring()
  } else {
    startMonitoring()
  }
}

const startMonitoring = () => {
  if (!selectedDistro.value) return
  
  const wsUrl = `ws://127.0.0.1:8000/ws/processes/${selectedDistro.value}`
  websocket.value = new WebSocket(wsUrl)
  
  websocket.value.onopen = () => {
    connectionStatus.value = 'connected'
    isMonitoring.value = true
    ElMessage.success('开始监控进程')
  }
  
  websocket.value.onmessage = async (event) => {
    try {
      const message = JSON.parse(event.data)

      if (message.type === 'processes') {
        // 使用nextTick确保Vue响应式系统稳定
        await nextTick()

        // 安全地更新进程数据，避免null引用错误
        if (message.data && Array.isArray(message.data.processes)) {
          // 创建新数组避免引用问题
          processes.value = [...message.data.processes]
        }
        if (message.data && message.data.statistics && typeof message.data.statistics === 'object') {
          // 创建新对象避免引用问题
          statistics.value = { ...message.data.statistics }
        }

        // 等待DOM更新完成
        await nextTick()

      } else if (message.type === 'error') {
        ElMessage.error(`监控错误: ${message.data?.error || '未知错误'}`)
      } else if (message.type === 'connection') {
        console.log('WebSocket连接建立:', message.data)
        connectionStatus.value = 'connected'
      }
    } catch (error) {
      console.error('处理WebSocket消息失败:', error)
      ElMessage.error('处理服务器消息失败')
    }
  }
  
  websocket.value.onclose = () => {
    connectionStatus.value = 'disconnected'
    isMonitoring.value = false
  }
  
  websocket.value.onerror = () => {
    ElMessage.error('WebSocket连接错误')
    connectionStatus.value = 'disconnected'
    isMonitoring.value = false
  }
}

const stopMonitoring = () => {
  if (websocket.value) {
    websocket.value.close()
    websocket.value = null
  }
  isMonitoring.value = false
  connectionStatus.value = 'disconnected'
  ElMessage.info('停止监控进程')
}

const refreshProcesses = async (showMessage: boolean = false) => {
  if (!selectedDistro.value) return

  try {
    const response = await fetch(`/api/processes/${selectedDistro.value}?refresh=true`)

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()

    if (data.success && data.data) {
      // 安全地更新进程数据
      if (Array.isArray(data.data.processes)) {
        processes.value = [...data.data.processes]  // 创建新数组
      }
      if (data.data.statistics) {
        statistics.value = { ...data.data.statistics }  // 创建新对象
      }

      if (showMessage) {
        ElMessage.success(`刷新成功，获取到 ${data.data.processes?.length || 0} 个进程`)
      }
    } else {
      const errorMsg = data.error || data.message || '未知错误'
      console.error('刷新进程失败:', errorMsg)
      if (showMessage) {
        ElMessage.error('刷新失败: ' + errorMsg)
      }
    }
  } catch (error) {
    console.error('刷新进程网络错误:', error)
    if (showMessage) {
      ElMessage.error('刷新失败: 网络错误')
    }
  }
}

const killProcess = async (pid: number, signal: string) => {
  try {
    // 首先检查进程是否仍然存在（通过刷新进程列表）
    await refreshProcesses()

    // 检查进程是否还在列表中
    const currentProcess = processes.value.find(p => p.pid === pid)
    if (!currentProcess) {
      ElMessage.warning(`进程 ${pid} 已经结束，无需终止`)
      return
    }

    await ElMessageBox.confirm(
      `确定要${signal === 'SIGKILL' ? '强制终止' : '终止'}进程 ${pid} (${currentProcess.name}) 吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false
      }
    )

    // 显示加载状态
    const loadingMessage = ElMessage({
      message: `正在${signal === 'SIGKILL' ? '强制终止' : '终止'}进程 ${pid}...`,
      type: 'info',
      duration: 0
    })

    try {
      const response = await fetch(`/api/processes/${selectedDistro.value}/kill`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pids: [pid],
          signal: signal
        })
      })

      loadingMessage.close()

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()

      if (data.success) {
        ElMessage.success(data.message)

        // 立即从本地列表中移除进程，提供更好的用户体验
        processes.value = processes.value.filter(p => p.pid !== pid)

        // 然后刷新完整列表
        setTimeout(() => {
          refreshProcesses()
        }, 1000)
      } else {
        // 显示详细的错误信息
        let errorMessage = data.message

        if (data.details && data.details.length > 0) {
          const failedDetail = data.details.find(d => !d.success)
          if (failedDetail) {
            errorMessage = failedDetail.message
          }
        }

        ElMessage.error(errorMessage)

        // 如果是进程不存在的错误，刷新进程列表
        if (errorMessage.includes('不存在') || errorMessage.includes('已经结束')) {
          refreshProcesses()
        }
      }
    } catch (fetchError) {
      loadingMessage.close()
      console.error('终止进程请求失败:', fetchError)
      ElMessage.error(`终止进程失败: ${fetchError.message}`)
    }

  } catch (error) {
    // 用户取消操作或其他错误
    if (error !== 'cancel') {
      console.error('终止进程操作失败:', error)
      ElMessage.error('操作失败，请重试')
    }
  }
}

const onSelectionChange = (selection: any[]) => {
  selectedProcesses.value = selection
}

const getCpuColor = (cpu: number) => {
  if (cpu > 80) return '#f56c6c'
  if (cpu > 50) return '#e6a23c'
  return '#67c23a'
}

const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    'R': 'success',
    'S': 'info',
    'D': 'warning',
    'Z': 'danger',
    'T': 'warning',
    'I': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'R': '运行',
    'S': '休眠',
    'D': '等待',
    'Z': '僵尸',
    'T': '停止',
    'I': '空闲'
  }
  return statusMap[status] || status
}

const formatMemory = (kb: number) => {
  if (kb < 1024) return `${kb} KB`
  if (kb < 1024 * 1024) return `${(kb / 1024).toFixed(1)} MB`
  return `${(kb / 1024 / 1024).toFixed(1)} GB`
}

const formatMemoryValue = (mb: number) => {
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(1)} GB`
}

const getCpuProgressColor = (percentage: number) => {
  if (percentage > 80) return '#f56c6c'
  if (percentage > 60) return '#e6a23c'
  if (percentage > 40) return '#409eff'
  return '#67c23a'
}

// 数值动画函数
const animateNumber = (from: number, to: number, target: any, duration: number = 1000) => {
  const startTime = Date.now()
  const difference = to - from

  const animate = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)

    // 使用缓动函数
    const easeOutQuart = 1 - Math.pow(1 - progress, 4)
    target.value = from + (difference * easeOutQuart)

    if (progress < 1) {
      requestAnimationFrame(animate)
    } else {
      target.value = to
    }
  }

  requestAnimationFrame(animate)
}

// 更新动画数据
const updateAnimatedStats = () => {
  if (!statistics.value) return

  const newStats = statistics.value

  // 计算趋势
  if (previousStats.value) {
    processTrend.value = newStats.total_processes - previousStats.value.total_processes
  }

  // 动画更新数值
  animateNumber(animatedTotalProcesses.value, newStats.total_processes || 0, animatedTotalProcesses)
  animateNumber(animatedRunningProcesses.value, newStats.running_processes || 0, animatedRunningProcesses)
  animateNumber(animatedCpuUsage.value, newStats.total_cpu_percent || 0, animatedCpuUsage)
  animateNumber(animatedMemoryUsage.value, newStats.total_memory_mb || 0, animatedMemoryUsage)

  // 保存当前统计数据
  previousStats.value = { ...newStats }
}

// 表格行样式
const getRowClassName = ({ row, rowIndex }: { row: any, rowIndex: number }) => {
  let className = ''

  if (row.is_protected) {
    className += 'protected-row '
  }

  if (row.cpu_percent > 80) {
    className += 'high-cpu-row '
  }

  if (row.stat === 'R') {
    className += 'running-row '
  }

  return className.trim()
}

// 监听统计数据变化
watch(statistics, (newStats) => {
  if (newStats) {
    updateAnimatedStats()
  }
}, { deep: true })

// 生命周期
onMounted(async () => {
  try {
    await loadDistros()
  } catch (error) {
    console.error('组件挂载时加载发行版失败:', error)
    ElMessage.error('初始化失败，请刷新页面重试')
  }
})

onUnmounted(() => {
  try {
    stopMonitoring()
  } catch (error) {
    console.error('组件卸载时清理资源失败:', error)
  }
})

// 错误捕获
onErrorCaptured((error, instance, info) => {
  console.error('Vue组件错误:', error)
  console.error('错误信息:', info)
  console.error('组件实例:', instance)

  // 如果是select组件相关的错误，尝试重置状态
  if (error.message && error.message.includes('emitsOptions')) {
    console.warn('检测到select组件错误，尝试重置状态')

    // 重置相关状态
    nextTick(() => {
      try {
        // 如果distros为空或有问题，重新加载
        if (!Array.isArray(distros.value) || distros.value.length === 0) {
          loadDistros()
        }
      } catch (resetError) {
        console.error('重置状态失败:', resetError)
      }
    })
  }

  // 返回false阻止错误继续传播
  return false
})
</script>

<style scoped>
.process-monitor {
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 20px 25px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
}

.toolbar-left {
  display: flex;
  gap: 15px;
  align-items: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .process-monitor {
    padding: 15px;
  }

  .toolbar {
    flex-direction: column;
    gap: 15px;
    padding: 15px;
  }

  .toolbar-left {
    width: 100%;
    justify-content: center;
  }

  .statistics {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 15px;
  }

  .stat-item {
    padding: 15px;
  }

  .stat-value {
    font-size: 24px;
  }
}

@media (max-width: 480px) {
  .statistics {
    grid-template-columns: 1fr;
  }

  .stat-item {
    flex-direction: column;
    text-align: center;
    gap: 10px;
  }

  .stat-value-container {
    justify-content: center;
  }
}

.statistics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.processes-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.running-card {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.cpu-card {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.memory-card {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  color: white;
}

.stat-item {
  display: flex;
  align-items: center;
  padding: 20px;
  gap: 15px;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.stat-content {
  flex: 1;
}

.stat-label {
  display: block;
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
  font-weight: 500;
}

.stat-value-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  line-height: 1;
  transition: all 0.3s ease;
}

.stat-value.animate-number {
  animation: pulse 2s infinite;
}

.stat-value.high-usage {
  animation: warning-pulse 1s infinite;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.2);
}

.trend-up {
  color: #67c23a;
}

.trend-down {
  color: #f56c6c;
}

.mini-progress {
  width: 60px;
}

.cpu-circle {
  margin-left: auto;
}

.memory-bar {
  width: 80px;
}

.memory-segments {
  display: flex;
  gap: 2px;
  height: 6px;
}

.memory-segment {
  flex: 1;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 1px;
  transition: all 0.3s ease;
}

.memory-segment.active {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 4px rgba(255, 255, 255, 0.5);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes warning-pulse {
  0%, 100% { color: inherit; }
  50% { color: #f56c6c; text-shadow: 0 0 10px rgba(245, 108, 108, 0.5); }
}

.process-table {
  margin-bottom: 20px;
}

.table-card {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 18px;
  font-weight: 600;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.process-count {
  font-size: 14px;
  color: #6c757d;
  background: #f8f9fa;
  padding: 4px 8px;
  border-radius: 6px;
}

.protected-process {
  color: #e6a23c;
  font-weight: bold;
}

/* 表格行样式 */
:deep(.el-table .protected-row) {
  background-color: #fdf6ec !important;
}

:deep(.el-table .high-cpu-row) {
  background-color: #fef0f0 !important;
}

:deep(.el-table .running-row) {
  background-color: #f0f9ff !important;
}

:deep(.el-table .protected-row:hover) {
  background-color: #faecd8 !important;
}

:deep(.el-table .high-cpu-row:hover) {
  background-color: #fde2e2 !important;
}

:deep(.el-table .running-row:hover) {
  background-color: #e0f2fe !important;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px;
  font-size: 14px;
  margin-top: 20px;
}
</style>
