<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h2 style="margin: 0">股票列表</h2>
      <a-space>
        <a-button type="primary" @click="syncStocks" :loading="syncing">
          同步股票列表
        </a-button>
      </a-space>
    </div>

    <a-alert
      v-if="syncMsg"
      :message="syncMsg"
      :type="syncMsgType"
      closable
      style="margin-bottom: 12px"
      @close="syncMsg = ''"
    />

    <a-table
      :columns="columns"
      :data-source="stocks"
      :loading="loading"
      row-key="stock_code"
      @row-click="onRowClick"
      :custom-row="customRow"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <a-button type="primary" size="small" @click.stop="goDetail(record.stock_code)">
            查看详情
          </a-button>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStockList, syncStockList } from '../api'

const router = useRouter()
const loading = ref(false)
const syncing = ref(false)
const syncMsg = ref('')
const syncMsgType = ref('success')
const stocks = ref([])

const columns = [
  { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code', width: 120 },
  { title: '股票名称', dataIndex: 'stock_name', key: 'stock_name', width: 140 },
  { title: '数据条数', dataIndex: 'total_records', key: 'total_records' },
  { title: '最早日期', dataIndex: 'earliest_date', key: 'earliest_date' },
  { title: '最新日期', dataIndex: 'latest_date', key: 'latest_date' },
  { title: '操作', key: 'action', width: 120 },
]

const customRow = () => ({
  style: { cursor: 'pointer' },
})

function onRowClick(record) {
  goDetail(record.stock_code)
}

function goDetail(code) {
  router.push(`/stocks/${code}`)
}

async function syncStocks() {
  syncing.value = true
  syncMsg.value = ''
  try {
    const { data } = await syncStockList()
    syncMsg.value = data.message || '同步完成'
    syncMsgType.value = data.status === 'ok' ? 'success' : 'warning'
    // 同步完成后刷新列表
    await fetchList()
  } catch (e) {
    syncMsg.value = '同步失败: ' + (e.response?.data?.detail || e.message)
    syncMsgType.value = 'error'
  } finally {
    syncing.value = false
  }
}

async function fetchList() {
  loading.value = true
  try {
    const { data } = await getStockList()
    stocks.value = data
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchList()
})
</script>
