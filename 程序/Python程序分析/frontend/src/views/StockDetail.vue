<template>
  <div>
    <a-page-header
      :title="stockName ? `${stockCode} ${stockName}` : `${stockCode} 行情数据`"
      @back="() => $router.push('/stocks')"
    />

    <!-- 统计卡片 -->
    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="4">
        <a-statistic title="数据总量" :value="stats.total_records" />
      </a-col>
      <a-col :span="5">
        <a-statistic title="日期范围" :value="`${stats.earliest_date} ~ ${stats.latest_date}`" />
      </a-col>
      <a-col :span="3">
        <a-statistic title="最新收盘价" :value="stats.latest_close" :precision="2" />
      </a-col>
      <a-col :span="3">
        <a-statistic title="最高收盘价" :value="stats.max_close" :precision="2" />
      </a-col>
      <a-col :span="3">
        <a-statistic title="最低收盘价" :value="stats.min_close" :precision="2" />
      </a-col>
    </a-row>

    <!-- 工具栏 -->
    <a-space style="margin-bottom: 16px">
      <span>复权类型：</span>
      <a-radio-group v-model:value="adjustType" @change="fetchQuotes">
        <a-radio-button value="none">不复权</a-radio-button>
        <a-radio-button value="forward">前复权</a-radio-button>
        <a-radio-button value="backward">后复权</a-radio-button>
      </a-radio-group>
      <a-range-picker
        v-model:value="dateRange"
        :placeholder="['起始日期', '结束日期']"
        @change="fetchQuotes"
      />
    </a-space>

    <!-- K线图 -->
    <a-card title="K线图" style="margin-bottom: 24px">
      <KLineChart :data="chartData" style="height: 450px" />
    </a-card>

    <!-- 数据表格 -->
    <a-card title="日K线数据">
      <a-table
        :columns="quoteColumns"
        :data-source="quotes"
        :loading="loading"
        :pagination="pagination"
        row-key="trade_date"
        size="small"
        @change="onTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'change'">
            <span :style="{ color: record._change >= 0 ? '#cf1322' : '#3f8600' }">
              {{ record._change >= 0 ? '+' : '' }}{{ record._change }}%
            </span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
import { getStockQuotes, getStockStats } from '../api'
import KLineChart from '../components/KLineChart.vue'

const route = useRoute()
const stockCode = computed(() => route.params.code)

const loading = ref(false)
const quotes = ref([])
const stats = ref({})
const stockName = ref('')
const adjustType = ref('none')
const dateRange = ref(null)

const pagination = ref({
  current: 1,
  pageSize: 100,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['50', '100', '200', '500'],
})

const quoteColumns = [
  { title: '日期', dataIndex: 'trade_date', key: 'trade_date', width: 110 },
  { title: '开盘价', dataIndex: 'open_price', key: 'open_price', align: 'right' },
  { title: '最高价', dataIndex: 'high_price', key: 'high_price', align: 'right' },
  { title: '最低价', dataIndex: 'low_price', key: 'low_price', align: 'right' },
  { title: '收盘价', dataIndex: 'close_price', key: 'close_price', align: 'right' },
  { title: '涨跌幅', key: 'change', align: 'right', width: 100 },
  { title: '成交量', dataIndex: 'volume', key: 'volume', align: 'right' },
  { title: '成交额', dataIndex: 'amount', key: 'amount', align: 'right' },
]

const chartData = computed(() => {
  // K线图需要时间升序
  return [...quotes.value].reverse().map((q) => ({
    ...q,
    _change: q._change,
  }))
})

function calcChange(data) {
  return data.map((item, i) => {
    const prev = data[i + 1]
    const chg = prev && prev.close_price ? ((item.close_price - prev.close_price) / prev.close_price * 100).toFixed(2) : '0.00'
    return { ...item, _change: parseFloat(chg) }
  })
}

async function fetchQuotes() {
  loading.value = true
  try {
    const params = {
      adjust_type: adjustType.value,
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].format('YYYY-MM-DD')
      params.end_date = dateRange.value[1].format('YYYY-MM-DD')
    }
    const { data } = await getStockQuotes(stockCode.value, params)
    quotes.value = calcChange(data.data)
    pagination.value.total = data.total
  } finally {
    loading.value = false
  }
}

function onTableChange(pag) {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  fetchQuotes()
}

onMounted(async () => {
  try {
    const { data } = await getStockStats(stockCode.value)
    stats.value = data
    if (data.stock_name) {
      stockName.value = data.stock_name
    }
  } catch { /* ignore */ }
  fetchQuotes()
})
</script>
