/**
 * WSL进程监控工具的共享类型定义
 * 这些类型在前端和后端之间保持一致
 */

export interface WSLProcess {
  pid: number;
  ppid: number;
  user: string;
  command: string;
  name: string;
  cpuPercent: number;
  memoryRSS: number;        // KB
  memoryVSZ: number;        // KB
  startTime: string;        // ISO格式
  runningTime: string;      // 人类可读格式，如"2h 30m"
  status: 'R' | 'S' | 'D' | 'Z' | 'T' | 'I';
}

export interface WSLDistro {
  name: string;
  version: 1 | 2;
  state: 'Running' | 'Stopped';
  isDefault: boolean;
}

export interface ProcessOperation {
  action: 'kill' | 'terminate';
  pids: number[];
  signal: 'SIGTERM' | 'SIGKILL';
  timestamp: string;
}

export interface ProcessFilter {
  user?: string;
  name?: string;
  command?: string;
  minCpu?: number;
  maxCpu?: number;
  minMemory?: number;
  maxMemory?: number;
  status?: WSLProcess['status'][];
}

export interface WebSocketMessage {
  type: 'processes' | 'error' | 'connection' | 'operation_result';
  data: any;
  timestamp: string;
}

export interface AppSettings {
  refreshInterval: number;    // 1-10秒
  theme: 'light' | 'dark';
  visibleColumns: string[];
  autoReconnect: boolean;
  maxReconnectAttempts: number;
}

export interface OperationResult {
  success: boolean;
  message: string;
  affectedPids: number[];
  timestamp: string;
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

// 进程统计信息
export interface ProcessStats {
  total: number;
  running: number;
  sleeping: number;
  stopped: number;
  zombie: number;
  totalCpu: number;
  totalMemory: number;
}
