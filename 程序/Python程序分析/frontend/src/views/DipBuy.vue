<template>
  <div class="dip-buy">
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
          <a-select v-model:value="strategy" @change="onStockChange" style="width: 100%">
            <a-select-option value="drawdown">高点回撤买入</a-select-option>
            <a-select-option value="daily_drop">当日大跌分批买入</a-select-option>
          </a-select>
        </a-col>
        <template v-if="strategy === 'drawdown'">
          <a-col :span="4">
            <a-input-number v-model:value="dipPct" :min="0" :max="90" :step="1" style="width: 100%">
              <template #addonBefore>回撤</template>
              <template #addonAfter>%</template>
            </a-input-number>
          </a-col>
          <a-col :span="4">
            <a-input-number v-model:value="buyAmount" :min="1" :step="5" style="width: 100%">
              <template #addonBefore>买入</template>
              <template #addonAfter>万</template>
            </a-input-number>
          </a-col>
        </template>
        <template v-else>
          <a-col :span="4">
            <a-input-number v-model:value="dipPct" :min="0" :max="20" :step="0.5" style="width: 100%">
              <template #addonBefore>当日跌</template>
              <template #addonAfter>%</template>
            </a-input-number>
          </a-col>
          <a-col :span="4">
            <a-input-number v-model:value="totalPosition" :min="1" :step="10" style="width: 100%">
              <template #addonBefore>总仓位</template>
              <template #addonAfter>万</template>
            </a-input-number>
          </a-col>
          <a-col :span="3">
            <a-input-number v-model:value="buyRatio" :min="1" :max="100" :step="1" style="width: 100%">
              <template #addonBefore>每笔</template>
              <template #addonAfter>%</template>
            </a-input-number>
          </a-col>
        </template>
        <a-col :span="3">
          <a-date-picker
            v-model:value="startDate"
            value-format="YYYY-MM-DD"
            placeholder="观察起点(可选)"
            style="width: 100%"
          />
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
        <a-col :span="5">
          <a-space>
            <a-button type="primary" @click="handleSimulate" :loading="simulating">开始模拟</a-button>
            <a-button @click="handleSync" :loading="syncing" :disabled="!selectedStock">同步分红</a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 空状态 -->
    <a-card v-if="!result && !simulating">
      <a-empty description="选择股票后点击「开始模拟」：大跌买入 + 红利再投，两种策略可选" />
    </a-card>

    <a-spin :spinning="simulating || syncing" tip="计算中...">
      <template v-if="result">
        <!-- 策略参数 / 买入触发信息 -->
        <a-card size="small" style="margin-bottom: 16px" v-if="isDaily">
          <a-space wrap>
            <a-tag color="blue">{{ result.stock_name }}({{ result.stock_code }})</a-tag>
            <a-tag color="orange">当日大跌分批买入</a-tag>
            <a-tag>总仓位 {{ fmtMoney(params.total_position) }} 元</a-tag>
            <a-tag>每笔 总仓位 {{ params.buy_ratio }}%（{{ fmtMoney(summary.tranche) }} 元）</a-tag>
            <a-tag color="red">触发: 盘中最低价较前收盘跌 ≥{{ params.dip_pct }}% → 按当日最低价买入</a-tag>
            <a-tag color="purple">共 {{ summary.trigger_count }} 次买入，投入 {{ fmtMoney(summary.total_invested) }} 元
              （{{ (summary.total_invested / params.total_position * 100).toFixed(1) }}%），
              剩余现金 {{ fmtMoney(summary.leftover_cash) }} 元</a-tag>
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

        <a-card size="small" style="margin-bottom: 16px" v-else>
          <a-space wrap>
            <a-tag color="blue">{{ result.stock_name }}({{ result.stock_code }})</a-tag>
            <a-tag color="orange">触发口径: {{ trigger.trigger_series }}</a-tag>
            <a-tag>期间最高: {{ trigger.peak_price.toFixed(2) }} 元({{ trigger.peak_date }})</a-tag>
            <a-tag color="red">首次回撤 ≥{{ trigger.dip_pct }}%: {{ trigger.buy_date }} @ {{ trigger.buy_price.toFixed(2) }} 元
              (实际 {{ trigger.actual_dip_pct.toFixed(2) }}%)</a-tag>
            <a-tag color="purple">买入 {{ fmtMoney(trigger.buy_amount) }} 元 → {{ trigger.initial_shares.toLocaleString() }} 股</a-tag>
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

        <!-- 分批买入明细（仅当日大跌模式） -->
        <a-card title="📋 每笔买入明细（当日最低价成交）" size="small" style="margin-bottom: 16px" v-if="isDaily">
          <a-table
            :columns="buyColumns"
            :data-source="result.triggers"
            :pagination="{ pageSize: 10, showTotal: t => `共 ${t} 笔` }"
            size="small"
            row-key="buy_date"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'drop_pct'">
                <span class="up">-{{ record.drop_pct.toFixed(2) }}%</span>
              </template>
              <template v-if="column.key === 'buy_price' || column.key === 'prev_close'">
                {{ record[column.key].toFixed(2) }}
              </template>
              <template v-if="column.key === 'buy_amount'">
                {{ fmtMoney(record.buy_amount) }}
              </template>
              <template v-if="column.key === 'buy_shares'">
                {{ record.buy_shares.toLocaleString() }}
              </template>
            </template>
          </a-table>
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
                <a-col :span="24" v-if="line.data.total_reinvested != null">
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
          title="📒 每笔交易明细（主策略线：日期/价格/数量 + 当日前复权价）"
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
        <a-card title="📋 分红事件明细（买入后，仅实施分配）" size="small">
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
import { searchStockInfo, syncDividendReinvest, simulateDipBuy } from '../api'

// ---- 参数 ----
const selectedStock = ref(null)
const stockOptions = ref([])
const strategy = ref('daily_drop') // drawdown=高点回撤；daily_drop=当日大跌分批
const dipPct = ref(20)
const buyAmount = ref(10) // 万元（drawdown）
const totalPosition = ref(100) // 万元（daily_drop）
const buyRatio = ref(5) // %（daily_drop）
const startDate = ref(null)
const taxRate = ref(0)
const reinvestSwitch = ref(true)

// ---- 状态 ----
const syncing = ref(false)
const simulating = ref(false)
const result = ref(null)
const chartRef = ref(null)
let chart = null

const isDaily = computed(() => strategy.value === 'daily_drop')
const trigger = computed(() => result.value?.trigger || {})
const params = computed(() => result.value?.params || {})
const summary = computed(() => result.value?.summary || {})

// ---- 工具 ----
function fmtMoney(v) {
  return Number(v ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
  if (isDaily.value) {
    const s = summary.value
    if (!s.staged_reinvest) return []
    return [
      { key: 'staged_reinvest', title: '🔴 分批买入+红利再投（本策略）', data: s.staged_reinvest },
      { key: 'lump_reinvest', title: '🔵 首触全仓+红利再投', data: s.lump_reinvest },
      { key: 'lump_no_reinvest', title: '⚪ 首触全仓+分红不投', data: s.lump_no_reinvest },
    ]
  }
  const s = summary.value
  if (!s.reinvest) return []
  return [
    { key: 'reinvest', title: '🔴 红利再投（分红无脑买入）', data: s.reinvest },
    { key: 'no_reinvest', title: '🔵 分红不投（现金留存）', data: s.no_reinvest },
    { key: 'price_only', title: '⚪ 纯股价（忽略分红）', data: s.price_only },
  ]
})

// ---- 每笔交易明细（前复权成本口径，主策略线 = 第一张策略卡） ----
const tradeList = computed(() => {
  const trades = strategyCards.value[0]?.data?.trades
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
  if (isDaily.value) {
    const s = summary.value
    if (!s.staged_reinvest) return { isWin: false, title: '', subTitle: '' }
    const st = s.staged_reinvest
    const lr = s.lump_reinvest
    const diff = st.final_asset - lr.final_asset
    const isWin = diff > 0
    return {
      isWin,
      title: `分批买入比「首触全仓」${isWin ? '多赚' : '少赚'} ${Math.abs(diff).toLocaleString('zh-CN', { maximumFractionDigits: 0 })} 元`,
      subTitle: `共 ${s.trigger_count} 次触发买入（投入 ${fmtMoney(s.total_invested)} 元，剩余现金 ${fmtMoney(s.leftover_cash)} 元）` +
        `；分批较全仓 ${diff >= 0 ? '+' : ''}${(diff / lr.final_asset * 100).toFixed(2)}%` +
        `；期间股价涨跌 ${s.period_return_pct.toFixed(2)}%` +
        (st.total_reinvested != null
          ? `；累计分红 ${fmtMoney(st.total_dividends)} 元，再投 ${fmtMoney(st.total_reinvested)} 元（${st.reinvest_count} 次）`
          : ''),
    }
  }
  const s = summary.value
  if (!s.reinvest) return { isWin: false, title: '', subTitle: '' }
  const ri = s.reinvest
  const nr = s.no_reinvest
  const diff = ri.final_asset - nr.final_asset
  const isWin = diff > 0
  return {
    isWin,
    title: `红利再投比「分红不投」${isWin ? '多赚' : '少赚'} ${Math.abs(diff).toLocaleString('zh-CN', { maximumFractionDigits: 0 })} 元`,
    subTitle: `累计分红到账 ${fmtMoney(ri.total_dividends)} 元，其中再投 ${fmtMoney(ri.total_reinvested)} 元（${ri.reinvest_count} 次）` +
      `；比「分红不投」${diff >= 0 ? '+' : ''}${(diff / nr.final_asset * 100).toFixed(2)}%` +
      `；期间股价涨跌 ${s.period_return_pct.toFixed(2)}%`,
  }
})

// ---- 图表 ----
function renderChart() {
  const curve = result.value?.equity_curve || []
  if (!curve.length || !chartRef.value) return
  if (chart) { chart.dispose(); chart = null }
  chart = echarts.init(chartRef.value)

  const dates = curve.map(e => e.trade_date)

  let series, buyDates = []
  if (isDaily.value) {
    series = [
      {
        name: '分批买入+红利再投',
        type: 'line',
        data: curve.map(e => e.staged_asset),
        lineStyle: { width: 2, color: '#cf1322' },
        itemStyle: { color: '#cf1322' },
        symbol: 'none',
      },
      {
        name: '首触全仓+红利再投',
        type: 'line',
        data: curve.map(e => e.lump_re_asset),
        lineStyle: { width: 1.5, color: '#1890ff' },
        itemStyle: { color: '#1890ff' },
        symbol: 'none',
      },
      {
        name: '首触全仓+分红不投',
        type: 'line',
        data: curve.map(e => e.lump_nr_asset),
        lineStyle: { width: 1, color: '#8c8c8c', type: 'dashed' },
        itemStyle: { color: '#8c8c8c' },
        symbol: 'none',
      },
    ]
    buyDates = (result.value?.triggers || []).map(t => t.buy_date)
  } else {
    series = [
      {
        name: '红利再投',
        type: 'line',
        data: curve.map(e => e.reinvest_asset),
        lineStyle: { width: 2, color: '#cf1322' },
        itemStyle: { color: '#cf1322' },
        symbol: 'none',
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
    ]
    buyDates = trigger.value.buy_date ? [trigger.value.buy_date] : []
  }

  // 买入日标记：分批模式竖线多，只标首触日；回撤模式标买入日
  const markDates = isDaily.value && buyDates.length ? [buyDates[0]] : buyDates
  series[0].markLine = markDates.length ? {
    symbol: 'none',
    label: { formatter: `买入日 ${markDates[0]}` },
    lineStyle: { color: '#d4b106', type: 'dashed' },
    data: markDates.map(d => ({ xAxis: d })),
  } : undefined

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      valueFormatter: v => Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 }),
    },
    legend: { data: series.map(s => s.name) },
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
    series,
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
      strategy: strategy.value,
      dip_pct: dipPct.value,
      tax_rate: taxRate.value,
      reinvest: reinvestSwitch.value,
    }
    if (strategy.value === 'drawdown') {
      payload.buy_amount = buyAmount.value
    } else {
      payload.total_position = totalPosition.value
      payload.buy_ratio = buyRatio.value
    }
    if (startDate.value) payload.start_date = startDate.value
    const { data } = await simulateDipBuy(selectedStock.value, payload)
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
  // 默认选中中国石油 + 当日大跌分批买入，方便演示
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
const buyColumns = [
  { title: '买入日期', dataIndex: 'buy_date', key: 'buy_date', width: 100 },
  { title: '前收盘', dataIndex: 'prev_close', key: 'prev_close', width: 90 },
  { title: '买入价(最低)', dataIndex: 'buy_price', key: 'buy_price', width: 110 },
  { title: '盘中跌幅', dataIndex: 'drop_pct', key: 'drop_pct', width: 100 },
  { title: '买入金额', dataIndex: 'buy_amount', key: 'buy_amount', width: 110 },
  { title: '股数', dataIndex: 'buy_shares', key: 'buy_shares', width: 90 },
]

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
.dip-buy {
  max-width: 1400px;
  margin: 0 auto;
}
.strategy-card.staged_reinvest,
.strategy-card.reinvest {
  border: 2px solid #ffa39e;
}
.strategy-card.lump_reinvest,
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
