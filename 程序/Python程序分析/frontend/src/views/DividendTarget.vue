<template>
  <div class="dividend-target">
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
        <a-col :span="4">
          <a-date-picker
            v-model:value="buyDate"
            value-format="YYYY-MM-DD"
            placeholder="买入日期"
            style="width: 100%"
          />
        </a-col>
        <a-col :span="4">
          <a-input-number v-model:value="targetAnnual" :min="1000" :step="50000" style="width: 100%">
            <template #addonBefore>年分红</template>
          </a-input-number>
        </a-col>
        <a-col :span="3">
          <a-select v-model:value="reference" style="width: 100%">
            <a-select-option value="last_year">基准: 去年全年</a-select-option>
            <a-select-option value="trailing">基准: 最近12个月</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="2">
          <a-input-number v-model:value="taxRate" :min="0" :max="1" :step="0.05" style="width: 100%">
            <template #addonBefore>税</template>
          </a-input-number>
        </a-col>
        <a-col :span="2">
          <span style="margin-right: 6px">再投</span>
          <a-switch v-model:checked="reinvestSwitch" />
        </a-col>
        <a-col :span="4">
          <a-button type="primary" @click="handlePlan" :loading="planning">开始测算</a-button>
        </a-col>
      </a-row>
    </a-card>

    <!-- 空状态 -->
    <a-card v-if="!result && !planning">
      <a-empty description="选择股票、输入买入日期和目标年分红金额，点击「开始测算」" />
    </a-card>

    <a-spin :spinning="planning" tip="测算中...">
      <template v-if="result">
        <!-- 基准信息 -->
        <a-card size="small" style="margin-bottom: 16px">
          <a-space wrap>
            <a-tag color="blue">{{ result.stock_name }}({{ result.stock_code }})</a-tag>
            <a-tag>指定买入日: {{ s.buy_date }}</a-tag>
            <a-tag>实际买入日: {{ s.actual_buy_date }} @ {{ s.buy_price.toFixed(2) }} 元</a-tag>
            <a-tag color="purple">分红基准: {{ s.reference.label }}（{{ s.reference.dividend_count }} 笔，
              {{ (s.reference.d_per_share * 10).toFixed(2) }} 元/10股 = {{ s.reference.d_per_share.toFixed(4) }} 元/股）</a-tag>
            <a-tag>目标: 每年到账 {{ fmtMoney(s.target_annual_dividend) }} 元 → {{ s.target_shares.toLocaleString() }} 股</a-tag>
          </a-space>
        </a-card>

        <!-- 两策略对比卡片 -->
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8">
            <a-card class="strategy-card reinvest" size="small" title="🔴 红利再投（期初少买）">
              <template v-if="s.reinvest">
                <a-statistic title="期初买入资金（元）" :value="s.reinvest.required_amount" :precision="0" />
                <div class="big-wan">{{ wan(s.reinvest.required_amount) }}</div>
                <div class="mini-item"><span class="mini-label">期初买入股数</span>
                  <span class="mini-value">{{ s.reinvest.required_shares.toLocaleString() }} 股</span></div>
                <div class="mini-item"><span class="mini-label">期间再投</span>
                  <span class="mini-value up">{{ s.reinvest.reinvest_count }} 次 / {{ wan(s.reinvest.total_reinvested) }}</span></div>
                <div class="mini-item"><span class="mini-label">现在持股</span>
                  <span class="mini-value">{{ s.reinvest.final_shares.toLocaleString() }} 股</span></div>
                <div class="mini-item"><span class="mini-label">每年分红到账</span>
                  <span class="mini-value up">{{ fmtMoney(s.reinvest.actual_annual_dividend) }} 元</span></div>
              </template>
              <template v-else><a-empty description="未启用红利再投" /></template>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card class="strategy-card no_reinvest" size="small" title="🔵 分红不投（一次买足）">
              <a-statistic title="期初买入资金（元）" :value="s.no_reinvest.required_amount" :precision="0" />
              <div class="big-wan">{{ wan(s.no_reinvest.required_amount) }}</div>
              <div class="mini-item"><span class="mini-label">期初买入股数</span>
                <span class="mini-value">{{ s.no_reinvest.required_shares.toLocaleString() }} 股</span></div>
              <div class="mini-item"><span class="mini-label">每年分红到账</span>
                <span class="mini-value up">{{ fmtMoney(s.no_reinvest.actual_annual_dividend) }} 元</span></div>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card class="strategy-card saving" size="small" title="💰 再投策略省下的钱">
              <template v-if="s.saving_amount != null">
                <a-statistic title="少花的买入资金（元）" :value="s.saving_amount" :precision="0"
                             :value-style="{ color: '#3f8600' }" />
                <div class="big-wan green">{{ wan(s.saving_amount) }}</div>
                <div class="mini-item"><span class="mini-label">相对不复投</span>
                  <span class="mini-value down">-{{ s.saving_pct.toFixed(1) }}%</span></div>
                <div class="mini-item"><span class="mini-label">实际买入价</span>
                  <span class="mini-value">{{ s.buy_price.toFixed(2) }} 元</span></div>
                <div class="mini-item"><span class="mini-label">税后每股年分红</span>
                  <span class="mini-value">{{ s.reference.d_net_per_share.toFixed(4) }} 元</span></div>
              </template>
              <template v-else><a-empty description="未启用红利再投" /></template>
            </a-card>
          </a-col>
        </a-row>

        <!-- 资金对比图 -->
        <a-card title="📊 所需买入资金对比" size="small" style="margin-bottom: 16px">
          <div ref="chartRef" class="chart-container"></div>
        </a-card>

        <!-- 参考分红明细 -->
        <a-card :title="`📋 分红基准明细（${s.reference.label}）`" size="small">
          <a-table
            :columns="refColumns"
            :data-source="s.reference.dividends"
            :pagination="false"
            size="small"
            row-key="ex_dividend_date"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'cash_per_share'">
                {{ (record.cash_per_10 / 10).toFixed(4) }}
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
import { searchStockInfo, planDividendTarget } from '../api'

// ---- 参数 ----
const selectedStock = ref(null)
const stockOptions = ref([])
const buyDate = ref('2018-01-02')
const targetAnnual = ref(200000)
const reference = ref('last_year')
const taxRate = ref(0)
const reinvestSwitch = ref(true)

// ---- 状态 ----
const planning = ref(false)
const result = ref(null)
const chartRef = ref(null)
let chart = null

const s = computed(() => result.value?.summary || {})

// ---- 工具 ----
function fmtMoney(v) {
  return Number(v ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function wan(v) {
  return (Number(v ?? 0) / 10000).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) + ' 万'
}

// ---- 股票搜索（防抖） ----
let searchTimer = null
function onSearchStock(val) {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    if (!val) { stockOptions.value = []; return }
    try {
      const { data } = await searchStockInfo(val)
      stockOptions.value = (data || []).map(x => ({
        value: x.stock_code,
        label: `${x.stock_code} ${x.stock_name}`,
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

// ---- 图表：所需资金对比（万元） ----
function renderChart() {
  const sum = s.value
  if (!sum || !chartRef.value) return
  if (chart) { chart.dispose(); chart = null }
  chart = echarts.init(chartRef.value)

  const names = sum.reinvest ? ['红利再投', '分红不投'] : ['分红不投']
  const values = sum.reinvest
    ? [sum.reinvest.required_amount / 10000, sum.no_reinvest.required_amount / 10000]
    : [sum.no_reinvest.required_amount / 10000]

  chart.setOption({
    tooltip: { trigger: 'axis', valueFormatter: v => Number(v).toFixed(1) + ' 万' },
    grid: { left: 80, right: 40, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: names },
    yAxis: { type: 'value', name: '万元' },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: sum.reinvest ? ['#cf1322', '#1890ff'][i] : '#1890ff' },
      })),
      barWidth: '45%',
      label: { show: true, position: 'top', formatter: p => p.value.toFixed(1) + ' 万', fontWeight: 'bold' },
    }],
  })

  const onResize = () => chart && chart.resize()
  window.addEventListener('resize', onResize)
  chart._onResize = onResize
}

// ---- 测算 ----
async function handlePlan() {
  if (!selectedStock.value) {
    message.warning('请先选择股票')
    return
  }
  if (!buyDate.value) {
    message.warning('请输入买入日期')
    return
  }
  planning.value = true
  try {
    const { data } = await planDividendTarget(selectedStock.value, {
      buy_date: buyDate.value,
      target_annual_dividend: targetAnnual.value,
      tax_rate: taxRate.value,
      reinvest: reinvestSwitch.value,
      reference: reference.value,
    })
    result.value = data
    await nextTick()
    renderChart()
    message.success('测算完成')
  } catch (e) {
    message.error(e.response?.data?.detail || e.message || '测算失败')
  } finally {
    planning.value = false
  }
}

onMounted(() => {
  // 默认中国石油，方便演示
  selectedStock.value = '601857'
  handlePlan()
})

onBeforeUnmount(() => {
  if (chart) {
    window.removeEventListener('resize', chart._onResize)
    chart.dispose()
    chart = null
  }
})

const refColumns = [
  { title: '除息日', dataIndex: 'ex_dividend_date', key: 'ex_dividend_date', width: 120 },
  { title: '报告期', dataIndex: 'report_date', key: 'report_date', width: 120 },
  { title: '每10股派息(元)', dataIndex: 'cash_per_10', key: 'cash_per_10', width: 120 },
  { title: '每股(元)', key: 'cash_per_share', width: 100 },
]
</script>

<style scoped>
.dividend-target {
  max-width: 1400px;
  margin: 0 auto;
}
.strategy-card.reinvest {
  border: 2px solid #ffa39e;
}
.strategy-card.no_reinvest {
  border: 2px solid #91caff;
}
.strategy-card.saving {
  border: 2px solid #95de64;
}
.big-wan {
  font-size: 22px;
  font-weight: bold;
  margin: 4px 0 8px;
}
.big-wan.green {
  color: #3f8600;
}
.mini-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 3px 0;
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
  height: 320px;
}
</style>
