<template>
  <div>
    <h2 style="margin-bottom: 16px">📤 数据导出</h2>

    <a-card title="数据库 SQL 导出" style="margin-bottom: 16px">
      <p style="color: #888; margin-bottom: 16px">
        将当前数据库的全部 {{ tableCount }} 张表导出为 SQL 文件（含建表语句和 INSERT 数据），可用于备份或迁移。
      </p>

      <a-space size="large" align="center" style="margin-bottom: 16px">
        <a-button
          type="primary"
          size="large"
          :loading="exporting"
          :disabled="exporting"
          @click="handleStart"
        >
          {{ exporting ? '导出中...' : '开始导出' }}
        </a-button>
        <a-button
          v-if="done"
          type="primary"
          size="large"
          @click="handleDownload"
        >
          ⬇ 下载 SQL 文件
        </a-button>
      </a-space>

      <!-- 进度条 -->
      <div v-if="exporting || done" style="margin: 16px 0">
        <a-progress
          :percent="Math.round(progress.percent || 0)"
          :status="progressStatus"
          style="max-width: 600px"
        />
        <p style="color: #888">
          {{ progressMessage }}
        </p>
      </div>
    </a-card>

    <!-- 表进度列表 -->
    <a-card title="各表导出进度" v-if="hasTables">
      <a-table
        :columns="columns"
        :data-source="tableList"
        :pagination="false"
        size="small"
        row-key="name"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag v-if="record.status === 'done'" color="green">完成</a-tag>
            <a-tag v-else-if="record.status === 'running'" color="processing">导出中</a-tag>
            <a-tag v-else color="default">等待</a-tag>
          </template>
          <template v-else-if="column.key === 'rows'">
            {{ record.rows.toLocaleString() }} 行
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { startExport, getExportProgress, downloadExport } from '../api'

const TABLE_NAMES_CN = {
  stock_daily_quote: '日K线行情',
  stock_info: '股票基本信息',
  stock_dividend_events: '分红事件',
  stock_core_data: '个股核心数据',
  stock_cookies: 'Cookie 池',
  simulation_account: '模拟账户',
  simulation_position: '模拟持仓',
  simulation_trade: '模拟交易记录',
  stock_weekday_stats: '星期涨跌统计',
}

const columns = [
  { title: '表名', dataIndex: 'name', key: 'name', width: 220 },
  { title: '说明', dataIndex: 'label', key: 'label' },
  { title: '行数', dataIndex: 'rows', key: 'rows', width: 120 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
]

const exporting = ref(false)
const done = ref(false)
const taskId = ref('')
const progress = ref({ percent: 0, current_table: '', done_rows: 0, total_rows: 0, message: '' })
const tables = ref({})
let pollTimer = null

const tableCount = computed(() => Object.keys(tables.value).length || 9)
const hasTables = computed(() => Object.keys(tables.value).length > 0)
const tableList = computed(() =>
  Object.entries(tables.value).map(([name, t]) => ({
    name,
    label: TABLE_NAMES_CN[name] || name,
    rows: t.rows || 0,
    status: t.status || 'pending',
  })),
)

const progressStatus = computed(() => {
  if (progress.value.status === 'error') return 'exception'
  if (done.value) return 'success'
  return 'active'
})

const progressMessage = computed(() => {
  if (progress.value.status === 'error') return progress.value.message || '导出失败'
  if (done.value) return progress.value.message || '导出完成'
  if (progress.value.current_table) {
    const label = TABLE_NAMES_CN[progress.value.current_table] || progress.value.current_table
    return `正在导出 ${label}（${progress.value.done_rows.toLocaleString()} / ${progress.value.total_rows.toLocaleString()} 行）...`
  }
  return '准备中...'
})

async function handleStart() {
  exporting.value = true
  done.value = false
  progress.value = { percent: 0, current_table: '', done_rows: 0, total_rows: 0, status: 'running', message: '' }
  tables.value = {}
  try {
    const { data } = await startExport()
    taskId.value = data.task_id
    message.success(`导出任务已启动: ${data.task_id}`)
    pollTimer = setInterval(pollProgress, 1000)
  } catch (e) {
    exporting.value = false
    message.error(e.response?.data?.detail || e.message)
  }
}

async function pollProgress() {
  try {
    const { data } = await getExportProgress(taskId.value)
    progress.value = data
    tables.value = data.tables || {}
    if (data.status === 'done') {
      stopPoll()
      exporting.value = false
      done.value = true
      message.success('导出完成')
    } else if (data.status === 'error') {
      stopPoll()
      exporting.value = false
      message.error(data.message || '导出失败')
    }
  } catch (e) {
    // 网络抖动则忽略,继续轮询
  }
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleDownload() {
  try {
    const resp = await downloadExport(taskId.value)
    const blob = new Blob([resp.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `deepstock_export_${Date.now()}.sql`
    a.click()
    URL.revokeObjectURL(url)
    message.success('下载已开始')
  } catch (e) {
    message.error(e.response?.data?.detail || e.message)
  }
}

onUnmounted(stopPoll)
</script>
