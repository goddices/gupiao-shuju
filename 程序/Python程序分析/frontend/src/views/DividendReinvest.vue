<template>
  <div class="dividend-reinvest">
    <!-- 参数工具栏 -->
    <a-card style="margin-bottom: 16px">
      <a-row :gutter="16" align="middle">
        <a-col :span="5">
          <a-select
            v-model:value="selectedStock"
            show-search
            placeholder="搜索并选择股票"
            :filter-option="false"
            :options="stockOptions"
            @search="onSearchStock"
            @change="onStockChange"
            style="width: 100%"
          />
        </a-col>
        <a-col :span="5">
          <a-range-picker
            v-model:value="rangeDates"
            value-format="YYYY-MM-DD"
            placeholder="['起始日期', '结束日期']"
            style="width: 100%"
          />
        </a-col>
        <a-col :span="3">
          <a-input-number v-model:value="initialCash" :min="1000" :step="10000" style="width: 100%">
            <template #addonBefore>本金</template>
          </a-input-number>
        </a-col>
        <a-col :span="3">
          <a-input-number v-model:value="taxRate" :min="0" :max="1" :step="0.05" style="width: 100%">
            <template #addonBefore>税率</template>
          </a-input-number>
        </a-col>
        <a-col :span="3">
          <span style="margin-right: 6px">红利再投</span>
          <a-switch v-model:checked="reinvestSwitch" />
        </a-col>
        <a-col :span="5">
          <a-space>
            <a-button type="primary" @click="handleSimulate" :loading="simulating">开始模拟</a-button>
            <a-button @click="handleSync" :loading="syncing" :disabled="!selectedStock">同步分红数据</a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 空状态 -->
    <a-card v-if="!result && !simulating">
      <a-empty description="选择股票后点击「开始模拟」，计算长期持股 + 分红无脑再投的收益" />
    </a-card>

    <a-spin :spinning="simulating || syncing" tip="计算中...">
      <template v-if="result">
        <!-- 模拟区间信息 -->
        <a-card size="small" style="margin-bottom: 16px">
          <a-space wrap>
            <a-tag color="blue">{{ result.stock_name }}({{ result.stock_code }})</a-tag>
            <a-tag>模拟区间: {{ result.summary.start_date }} ~ {{ result.summary.end_date }}</a-tag>
            <a-tag>共 {{ result.summary.trading_days }} 个交易日</a-tag>
            <a-tag color="purple">分红 {{ result.summary.dividend_count }} 次</a-tag>
            <a-tag>股价区间涨跌: {{ fmtPct(result.summary.period_return_pct / 100) }}</a-tag>
          </a-space>
          <a-alert
            v-for="(w, i) in result.warnings"
            :key="i"
            :message="w"
            type="warning"
            show-icon
            style="margin-top: 8px"
          />
        </a-card>

        <!-- 三策略对比卡片 -->
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8" v-for="line in strategyCards" :key="line.key">
            <a-card :class="['strategy-card', line.key]" size="small">
              <template #title>
                <span class="strategy-title">{{ line.title }}</span>
              </template>
              <a-statistic title="期末总资产（元）" :value="line.data.final_asset" :precision="2" />
              <a-row :gutter="8" style="margin-top: 8px">
                <a-col :span="12">
                  <div class="mini-item">
                    <span class="mini-label">总收益率</span>
                    <span :class="['mini-value', line.data.total_return_pct >= 0 ? 'up' : 'down']">
                      {{ line.data.total_return_pct.toFixed(2) }}%
                    </span>
                  </div>
                </a-col>
                <a-col :span="12">
                  <div class="mini-item">
                    <span class="mini-label">年化收益</span>
                    <span :class="['mini-value', (line.data.annual_return_pct ?? 0) >= 0 ? 'up' : 'down']">
                      {{ line.data.annual_return_pct != null ? (line.data.annual_return_pct * 100).toFixed(2) + '%' : 'N/A' }}
                    </span>
                  </div>
                </a-col>
                <a-col :span="12">
                  <div class="mini-item">
                    <span class="mini-label">最大回撤</span>
                    <span class="mini-value down">{{ line.data.max_drawdown_pct.toFixed(2) }}%</span>
                  </div>
                </a-col>
                <a-col :span="12">
                  <div class="mini-item">
                    <span class="mini-label">期末持股</span>
                    <span class="mini-value">{{ line.data.final_shares.toLocaleString() }} 股</span>
                  </div>
                </a-col>
                <a-col :span="12">
                  <div class="mini-item">
                    <span class="mini-label">期末现金</span>
                    <span class="mini-value">{{ fmtMoney(line.data.final_cash) }}</span>
                  </div>
                </a-col>
                <a-col :span="12">
                  <div class="mini-item">
                    <span class="mini-label">累计分红</span>
                    <span class="mini-value up">{{ fmtMoney(line.data.total_dividends) }}</span>
                  </div>
                </a-col>
                <a-col :span="24" v-if="line.key === 'reinvest'">
                  <div class="mini-item">
                    <span class="mini-label">累计再投金额（{{ line.data.reinvest_count }} 次）</span>
                    <span class="mini-value up">{{ fmtMoney(line.data.total_reinvested) }}</span>
                  </div>
                </a-col>
                <a-col :span="24" v-if="line.data.forward_cost != null">
                  <div class="mini-item">
                    <span class="mini-label">前复权口径收益率（成本价前复权）</span>
                    <span :class="['mini-value', line.data.forward_return_pct >= 0 ? 'up' : 'down']">
                      {{ line.data.forward_return_pct.toFixed(2) }}%
                    </span>
                  </div>
                </a-col>
                <a-col :span="24" v-if="line.data.forward_cost != null">
                  <div class="mini-item">
                    <span class="mini-label">前复权成本 / 成本均价</span>
                    <span class="mini-value">{{ fmtMoney(line.data.forward_cost) }} 元 / {{ line.data.forward_cost_avg.toFixed(4) }} 元/股</span>
                  </div>
                </a-col>
              </a-row>
            </a-card>
          </a-col>
        </a-row>

        <!-- 核心结论 -->
        <a-card size="small" style="margin-bottom: 16px" v-if="result">
          <a-result
            :status="conclusion.isWin ? 'success' : 'info'"
            :title="conclusion.title"
            :sub-title="conclusion.subTitle"
          >
          </a-result>
        </a-card>

        <!-- 权益曲线图 -->
        <a-card title="📈 权益曲线对比（不复权价格）" size="small" style="margin-bottom: 16px">
          <div ref="chartRef" class="chart-container"></div>
        </a-card>

        <!-- 每笔交易明细（前复权成本口径） -->
        <a-card
          title="📒 每笔交易明细（红利再投线：日期/价格/数量 + 当日前复权价）"
          size="small"
          style="margin-bottom: 16px"
          v-if="tradeList.length"
        >
          <a-table
            :columns="tradeColumns"
            :data-source="tradeList"
            :pagination="{ pageSize: 10, showTotal: t => `共 ${t} 笔` }"
            size="small"
            row-key="index"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'price'">{{ record.price.toFixed(4) }}</template>
              <template v-if="column.key === 'shares'">{{ record.shares.toLocaleString() }}</template>
              <template v-if="column.key === 'amount'">{{ fmtMoney(record.amount) }}</template>
              <template v-if="column.key === 'fwd_price'">
                {{ record.fwd_price != null ? record.fwd_price.toFixed(4) : '—' }}
              </template>
            </template>
          </a-table>
        </a-card>

        <!-- 分红事件明细 -->
        <a-card title="📋 分红事件明细（仅实施分配）" size="small">
          <a-table
            :columns="eventColumns"
            :data-source="result.dividend_events"
            :pagination="{ pageSize: 10, showTotal: t => `共 ${t} 笔` }"
            size="small"
            row-key="ex_dividend_date"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'cash_per_10'">
                {{ record.cash_per_10.toFixed(4) }}
              </template>
              <template v-if="column.key === 'bonus_total'">
                {{ ((record.bonus_per_10 || 0) + (record.conversion_per_10 || 0)).toFixed(1) }}
              </template>
              <template v-if="column.key === 'cash_received'">
                <span class="up">{{ fmtMoney(record.cash_received) }}</span>
              </template>
              <template v-if="column.key === 'reinvest_amount'">
                <span :class="record.reinvest_amount > 0 ? 'up' : ''">{{ fmtMoney(record.reinvest_amount) }}</span>
              </template>
              <template v-if="column.key === 'close_price'">
                {{ record.close_price.toFixed(2) }}
              </template>
            </template>
          </a-table>
        </a-card>
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import { searchStockInfo, syncDividendReinvest, simulateDividendReinvest } from '../api'

// ---- 参数 ----
const selectedStock = ref(null)
const stockOptions = ref([])
const rangeDates = ref([])
const initialCash = ref(100000)
const taxRate = ref(0)
const reinvestSwitch = ref(true)

// ---- 状态 ----
const syncing = ref(false)
const simulating = ref(false)
const result = ref(null)
const chartRef = ref(null)
let chart = null

// ---- 工具 ----
function fmtMoney(v) {
  return Number(v ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtPct(fraction) {
  return (Number(fraction ?? 0) * 100).toFixed(2) + '%'
}

// ---- 股票搜索（防抖） ----
let searchTimer = null
function onSearchStock(val) {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    if (!val) { stockOptions.value = []; return }
    try {
      const { data } = await searchStockInfo(val)
      stockOptions.value = (data || []).map(s => ({
        value: s.stock_code,
        label: `${s.stock_code} ${s.stock_name}`,
      }))
    } catch (e) {
      console.error(e)
    }
  }, 300)
}

function onStockChange() {
  result.value = null
  if (chart) chart.clear()
}

// ---- 三策略卡片数据 ----
const strategyCards = computed(() => {
  if (!result.value) return []
  const s = result.value.summary
  return [
    { key: 'reinvest', title: '🔴 红利再投（分红无脑买入）', data: s.reinvest },
    { key: 'no_reinvest', title: '🔵 分红不投（现金留存）', data: s.no_reinvest },
    { key: 'price_only', title: '⚪ 纯股价（忽略分红）', data: s.price_only },
  ]
})

// ---- 每笔交易明细（前复权成本口径） ----
const tradeList = computed(() => {
  const trades = result.value?.summary?.reinvest?.trades
  if (!trades?.length) return []
  return trades.map((t, i) => ({ ...t, index: i }))
})

const tradeColumns = [
  { title: '交易日期', dataIndex: 'trade_date', key: 'trade_date', width: 110 },
  { title: '类型', dataIndex: 'kind', key: 'kind', width: 100 },
  { title: '成交价(不复权)', dataIndex: 'price', key: 'price', width: 110 },
  { title: '数量', dataIndex: 'shares', key: 'shares', width: 100 },
  { title: '金额', dataIndex: 'amount', key: 'amount', width: 130 },
  { title: '当日前复权价', dataIndex: 'fwd_price', key: 'fwd_price', width: 110 },
]

const conclusion = computed(() => {
  if (!result.value) return { isWin: false, title: '', subTitle: '' }
  const s = result.value.summary
  const ri = s.reinvest
  const nr = s.no_reinvest
  const diff = ri.final_asset - nr.final_asset
  const vsPrice = ri.final_asset - s.price_only.final_asset
  const isWin = diff > 0
  return {
    isWin,
    title: `红利再投比「分红不投」${isWin ? '多赚' : '少赚'} ${Math.abs(diff).toLocaleString('zh-CN', { maximumFractionDigits: 0 })} 元`,
    subTitle: `累计分红到账 ${fmtMoney(ri.total_dividends)} 元，其中再投 ${fmtMoney(ri.total_reinvested)} 元（${ri.reinvest_count} 次）` +
      `；比「分红不投」${diff >= 0 ? '+' : ''}${(diff / nr.final_asset * 100).toFixed(2)}%，` +
      `比「纯股价」${vsPrice >= 0 ? '+' : ''}${(vsPrice / s.price_only.final_asset * 100).toFixed(2)}%`,
  }
})

// ---- 图表 ----
function renderChart() {
  const curve = result.value?.equity_curve || []
  if (!curve.length || !chartRef.value) return
  if (chart) { chart.dispose(); chart = null }
  chart = echarts.init(chartRef.value)

  const dates = curve.map(e => e.trade_date)
  // 除息日标记（红利再投曲线上的点）
  const exMarks = (result.value?.dividend_events || [])
    .filter(e => curve.some(c => c.trade_date === e.ex_dividend_date))
    .map(e => {
      const point = curve.find(c => c.trade_date === e.ex_dividend_date)
      return { coord: [e.ex_dividend_date, point.reinvest_asset], value: `除息 ${e.cash_per_10.toFixed(2)}` }
    })

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      valueFormatter: v => Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 }),
    },
    legend: { data: ['红利再投', '分红不投', '纯股价'] },
    grid: { left: 80, right: 40, top: 40, bottom: 80 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: '总资产（元）',
      axisLabel: { formatter: v => v.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 },
    ],
    series: [
      {
        name: '红利再投',
        type: 'line',
        data: curve.map(e => e.reinvest_asset),
        lineStyle: { width: 2, color: '#cf1322' },
        itemStyle: { color: '#cf1322' },
        symbol: 'none',
        markPoint: exMarks.length ? {
          data: exMarks,
          symbol: 'triangle',
          symbolSize: 8,
          symbolRotate: 180,
          itemStyle: { color: '#d4b106' },
          label: { show: false },
        } : undefined,
      },
      {
        name: '分红不投',
        type: 'line',
        data: curve.map(e => e.no_reinvest_asset),
        lineStyle: { width: 1.5, color: '#1890ff' },
        itemStyle: { color: '#1890ff' },
        symbol: 'none',
      },
      {
        name: '纯股价',
        type: 'line',
        data: curve.map(e => e.price_only_asset),
        lineStyle: { width: 1, color: '#8c8c8c', type: 'dashed' },
        itemStyle: { color: '#8c8c8c' },
        symbol: 'none',
      },
    ],
  })

  const onResize = () => chart && chart.resize()
  window.addEventListener('resize', onResize)
  chart._onResize = onResize
}

// ---- 操作 ----
async function handleSimulate() {
  if (!selectedStock.value) {
    message.warning('请先选择股票')
    return
  }
  simulating.value = true
  try {
    const payload = {
      initial_cash: initialCash.value,
      tax_rate: taxRate.value,
      reinvest: reinvestSwitch.value,
    }
    if (rangeDates.value && rangeDates.value.length === 2) {
      payload.start_date = rangeDates.value[0]
      payload.end_date = rangeDates.value[1]
    }
    const { data } = await simulateDividendReinvest(selectedStock.value, payload)
    result.value = data
    await nextTick()
    renderChart()
    message.success('模拟完成')
  } catch (e) {
    message.error(e.response?.data?.detail || e.message || '模拟失败')
  } finally {
    simulating.value = false
  }
}

async function handleSync() {
  syncing.value = true
  try {
    const { data } = await syncDividendReinvest(selectedStock.value)
    message.success(data.message || '同步完成')
  } catch (e) {
    message.error(e.response?.data?.detail || e.message || '同步失败')
  } finally {
    syncing.value = false
  }
}

onMounted(() => {
  // 默认选中中国石油，方便演示
  selectedStock.value = '601857'
  handleSimulate()
})

onBeforeUnmount(() => {
  if (chart) {
    window.removeEventListener('resize', chart._onResize)
    chart.dispose()
    chart = null
  }
})

// ---- 表格列 ----
const eventColumns = [
  { title: '除息日', dataIndex: 'ex_dividend_date', key: 'ex_dividend_date', width: 100 },
  { title: '报告期', dataIndex: 'report_date', key: 'report_date', width: 100 },
  { title: '每10股派息', dataIndex: 'cash_per_10', key: 'cash_per_10', width: 100 },
  { title: '送转(股/10)', key: 'bonus_total', width: 100 },
  { title: '到账金额', dataIndex: 'cash_received', key: 'cash_received', width: 110 },
  { title: '送转股数', dataIndex: 'bonus_shares', key: 'bonus_shares', width: 90 },
  { title: '当日收盘', dataIndex: 'close_price', key: 'close_price', width: 90 },
  { title: '再投股数', dataIndex: 'reinvest_shares', key: 'reinvest_shares', width: 90 },
  { title: '再投金额', dataIndex: 'reinvest_amount', key: 'reinvest_amount', width: 110 },
]
</script>

<style scoped>
.dividend-reinvest {
  max-width: 1400px;
  margin: 0 auto;
}
.strategy-card.reinvest {
  border: 2px solid #ffa39e;
}
.strategy-card.no_reinvest {
  border: 2px solid #91caff;
}
.strategy-title {
  font-weight: bold;
}
.mini-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 2px 0;
}
.mini-label {
  color: #888;
}
.mini-value {
  font-weight: bold;
}
.mini-value.up { color: #cf1322; }
.mini-value.down { color: #3f8600; }
.chart-container {
  width: 100%;
  height: 460px;
}
</style>
