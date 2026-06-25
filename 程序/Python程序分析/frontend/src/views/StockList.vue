<template>
  <div>
    <h2 style="margin-bottom: 16px">股票列表</h2>
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
import { getStockList } from '../api'

const router = useRouter()
const loading = ref(false)
const stocks = ref([])

const columns = [
  { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code' },
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

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await getStockList()
    stocks.value = data
  } finally {
    loading.value = false
  }
})
</script>
