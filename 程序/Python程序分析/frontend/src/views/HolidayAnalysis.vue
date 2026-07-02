<template>
  <div class="holiday-analysis">
    <!-- 顶部工具栏 -->
    <a-card style="margin-bottom: 16px">
      <a-row :gutter="16" align="middle">
        <a-col :span="8">
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
        <a-col :span="8">
          <a-button type="primary" @click="handleRefresh" :loading="loading" :disabled="!selectedStock">
            加载分析
          </a-button>
        </a-col>
        <a-col :span="8" v-if="analysisData">
          <a-tag color="blue">数据区间: {{ analysisData.date_range_start }} ~ {{ analysisData.date_range_end }}</a-tag>
        </a-col>
      </a-row>
    </a-card>

    <!-- 加载或空状态 -->
    <a-card v-if="!analysisData && !loading">
      <a-empty description="请选择股票并点击「加载分析」查看节日涨跌分析" />
    </a-card>

    <a-spin :spinning="loading" tip="加载中...">
      <template v-if="analysisData">
        <!-- 节日综合概览卡片 -->
        <a-card title="📊 各节日涨跌综合概览" size="small" style="margin-bottom: 16px">
          <a-row :gutter="12">
            <a-col :span="4" v-for="item in analysisData.summary" :key="item.name">
              <a-card
                :class="['holiday-summary-card', { 'best-card': item.first_day_up_probability >= bestUpProb }]"
                size="small"
              >
                <div class="holiday-name">{{ item.name }}</div>
                <div class="holiday-count">{{ item.event_count }}年数据</div>
                <a-divider style="margin: 8px 0" />
                <div class="stat-row">
                  <span class="stat-label">节后首日</span>
                  <span :class="['stat-value', item.first_day_mean_change >= 0 ? 'up' : 'down']">
                    {{ item.first_day_mean_change.toFixed(2) }}%
                  </span>
                </div>
                <div class="stat-row">
                  <span class="stat-label">首日上涨率</span>
                  <span class="stat-value" style="color: #cf1322">{{ item.first_day_up_probability.toFixed(1) }}%</span>
                </div>
                <div class="stat-row">
                  <span class="stat-label">节前7日累计</span>
                  <span :class="['stat-value', item.cumulative_before_mean >= 0 ? 'up' : 'down']">
                    {{ item.cumulative_before_mean.toFixed(2) }}%
                  </span>
                </div>
                <div class="stat-row">
                  <span class="stat-label">节后7日累计</span>
                  <span :class="['stat-value', item.cumulative_after_mean >= 0 ? 'up' : 'down']">
                    {{ item.cumulative_after_mean.toFixed(2) }}%
                  </span>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </a-card>

        <!-- 整体走势图 -->
        <a-card title="📈 各节日前后7日平均涨跌幅走势" size="small" style="margin-bottom: 16px">
          <div ref="trendChartRef" style="width: 100%; height: 400px"></div>
        </a-card>

        <!-- 节后首日热力图 -->
        <a-card title="🔥 各节日节后首日逐年涨跌" size="small" style="margin-bottom: 16px">
          <div ref="heatmapChartRef" style="width: 100%; height: 300px"></div>
        </a-card>

        <!-- 各节日详细分析 -->
        <a-card title="📋 各节日详细数据分析" size="small">
          <a-tabs v-model:activeKey="activeTab" type="card">
            <a-tab-pane
              v-for="holiday in analysisData.analysis"
              :key="holiday.name"
              :tab="holiday.name"
            >
              <!-- 节日概览 -->
              <a-row :gutter="16" style="margin-bottom: 16px">
                <a-col :span="6">
                  <a-statistic title="数据年数" :value="holiday.event_count" suffix="年" />
                </a-col>
                <a-col :span="6">
                  <a-statistic
                    title="节后首日上涨概率"
                    :value="holiday.first_day_after?.up_probability || 0"
                    suffix="%"
                    :value-style="{ color: (holiday.first_day_after?.up_probability || 0) >= 50 ? '#cf1322' : '#3f8600' }"
                  />
                </a-col>
                <a-col :span="6">
                  <a-statistic
                    title="节后首日均值"
                    :value="holiday.first_day_after?.mean_change || 0"
                    :precision="2"
                    suffix="%"
                    :value-style="{ color: (holiday.first_day_after?.mean_change || 0) >= 0 ? '#cf1322' : '#3f8600' }"
                  />
                </a-col>
                <a-col :span="6">
                  <a-statistic
                    title="节后7日累计均值"
                    :value="holiday.cumulative_after?.mean_change || 0"
                    :precision="2"
                    suffix="%"
                    :value-style="{ color: (holiday.cumulative_after?.mean_change || 0) >= 0 ? '#cf1322' : '#3f8600' }"
                  />
                </a-col>
              </a-row>

              <!-- 前后7日详细表格 -->
              <a-table
                :columns="detailColumns"
                :data-source="holiday.daily_stats"
                :pagination="false"
                size="small"
                row-key="position"
                style="margin-bottom: 16px"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'position_label'">
                    <a-tag :color="record.position < 0 ? 'orange' : 'blue'">{{ record.position_label }}</a-tag>
                  </template>
                  <template v-if="column.key === 'up_probability'">
                    <span :style="{ color: record.up_probability >= 50 ? '#cf1322' : '#3f8600', fontWeight: 'bold' }">
                      {{ record.up_probability.toFixed(1) }}%
                    </span>
                  </template>
                  <template v-if="column.key === 'mean_change'">
                    <span :style="{ color: record.mean_change >= 0 ? '#cf1322' : '#3f8600', fontWeight: 'bold' }">
                      {{ record.mean_change.toFixed(3) }}%
                    </span>
                  </template>
                  <template v-if="column.key === 'max_gain'">
                    <span style="color: #cf1322">{{ record.max_gain.toFixed(2) }}%</span>
                  </template>
                  <template v-if="column.key === 'max_loss'">
                    <span style="color: #3f8600">{{ record.max_loss.toFixed(2) }}%</span>
                  </template>
                </template>
              </a-table>

              <!-- 逐年记录 -->
              <a-divider>节后首日逐年涨跌幅</a-divider>
              <div ref="yearBarRefs" :data-holiday="holiday.name" style="width: 100%; height: 250px"></div>
              <a-table
                :columns="yearColumns"
                :data-source="holiday.year_records"
                :pagination="false"
                size="small"
                row-key="year"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'change_pct'">
                    <a-tag :color="record.change_pct >= 0 ? 'red' : 'green'">
                      {{ record.change_pct.toFixed(2) }}%
                    </a-tag>
                  </template>
                </template>
              </a-table>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { getHolidayAnalysis, searchStockInfo } from '../api'
import * as echarts from 'echarts'

const HOLIDAY_COLORS = {
  '春节': '#E53935', '国庆节': '#FF6D00', '劳动节': '#1E88E5',
  '端午节': '#43A047', '中秋节': '#FDD835', '清明节': '#8D6E63', '元旦': '#00838F'
}

// 股票选择
const selectedStock = ref('000001')
const stockOptions = ref([{ value: '000001', label: '000001 上证指数' }])
const loading = ref(false)
const analysisData = ref(null)
const activeTab = ref('春节')

// 图表引用
const trendChartRef = ref(null)
const heatmapChartRef = ref(null)
const yearBarRefs = ref(null)

let trendChart = null
let heatmapChart = null
const yearCharts = {}

const bestUpProb = computed(() => {
  if (!analysisData.value) return 0
  return Math.max(...analysisData.value.summary.map(s => s.first_day_up_probability))
})

// 表格列定义
const detailColumns = [
  { title: '位置', dataIndex: 'position_label', key: 'position_label', width: 80 },
  { title: '样本数', dataIndex: 'count', key: 'count', width: 70 },
  { title: '上涨次数', dataIndex: 'up_count', key: 'up_count', width: 80 },
  { title: '下跌次数', dataIndex: 'down_count', key: 'down_count', width: 80 },
  { title: '上涨概率', dataIndex: 'up_probability', key: 'up_probability', width: 90 },
  { title: '平均涨跌', dataIndex: 'mean_change', key: 'mean_change', width: 100 },
  { title: '最大涨幅', dataIndex: 'max_gain', key: 'max_gain', width: 90 },
  { title: '最大跌幅', dataIndex: 'max_loss', key: 'max_loss', width: 90 },
]

const yearColumns = [
  { title: '年份', dataIndex: 'year', key: 'year', width: 80 },
  { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
  { title: '涨跌幅', dataIndex: 'change_pct', key: 'change_pct', width: 120 },
]

// 搜索股票
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
  analysisData.value = null
}

async function handleRefresh() {
  if (!selectedStock.value) return
  loading.value = true
  try {
    const { data } = await getHolidayAnalysis(selectedStock.value)
    analysisData.value = data
    if (data.analysis.length > 0) {
      activeTab.value = data.analysis[0].name
    }
    await nextTick()
    renderTrendChart()
    renderHeatmapChart()
    setTimeout(() => renderYearCharts(), 200)
  } catch (e) {
    if (e.response?.status === 404) {
      message.warning('该股票暂无行情数据')
      analysisData.value = null
    } else {
      message.error(e.response?.data?.detail || e.message || '加载失败')
    }
  } finally {
    loading.value = false
  }
}

// 走势图
function renderTrendChart() {
  if (!trendChartRef.value || !analysisData.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  const xLabels = []
  for (let i = -7; i < 0; i++) xLabels.push(`节前${Math.abs(i)}天`)
  for (let i = 1; i <= 7; i++) xLabels.push(`节后${i}天`)

  const series = analysisData.value.analysis.map(h => {
    const data = xLabels.map((_, idx) => {
      const pos = idx < 7 ? -(7 - idx) : (idx - 6)
      const stat = (h.daily_stats || []).find(s => s.position === pos)
      return stat ? stat.mean_change : null
    })
    return {
      name: h.name,
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2 },
      itemStyle: { color: HOLIDAY_COLORS[h.name] || '#666' },
    }
  })

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        let html = `<b>${params[0].axisValue}</b><br/>`
        params.forEach(p => {
          if (p.value !== null) {
            html += `${p.marker} ${p.seriesName}: ${p.value.toFixed(3)}%<br/>`
          }
        })
        return html
      }
    },
    legend: { data: analysisData.value.analysis.map(h => h.name), bottom: 0 },
    grid: { left: 50, right: 30, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: xLabels,
      boundaryGap: false,
      axisLabel: { rotate: 30, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: '平均涨跌幅(%)',
      axisLabel: { formatter: '{value}%' },
    },
    series: series,
    dataZoom: [{ type: 'inside' }],
  })
}

// 热力图
function renderHeatmapChart() {
  if (!heatmapChartRef.value || !analysisData.value) return
  if (!heatmapChart) {
    heatmapChart = echarts.init(heatmapChartRef.value)
  }

  const holidays = analysisData.value.analysis.map(h => h.name)
  const allYears = new Set()
  const dataMap = {}
  analysisData.value.analysis.forEach(h => {
    dataMap[h.name] = {}
    h.year_records.forEach(r => {
      allYears.add(r.year)
      dataMap[h.name][r.year] = r.change_pct
    })
  })
  const years = [...allYears].sort()

  const heatData = []
  holidays.forEach((name, i) => {
    years.forEach((year, j) => {
      const val = dataMap[name]?.[year]
      if (val !== undefined) {
        heatData.push([j, i, val])
      }
    })
  })

  const maxAbs = Math.max(...heatData.map(d => Math.abs(d[2])), 0.5)

  heatmapChart.setOption({
    tooltip: {
      formatter: function(p) {
        return `${holidays[p.value[1]]} ${years[p.value[0]]}年<br/>涨跌: ${p.value[2].toFixed(2)}%`
      }
    },
    grid: { left: 80, right: 60, top: 10, bottom: 50 },
    xAxis: {
      type: 'category',
      data: years,
      axisLabel: { rotate: 45, fontSize: 9 },
      position: 'bottom',
    },
    yAxis: {
      type: 'category',
      data: holidays,
      axisLabel: { fontSize: 11 },
    },
    visualMap: {
      min: -maxAbs,
      max: maxAbs,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      inRange: { color: ['#3f8600', '#ffffff', '#cf1322'] },
    },
    series: [{
      type: 'heatmap',
      data: heatData,
      label: {
        show: true,
        fontSize: 9,
        formatter: p => p.value[2].toFixed(1) + '%'
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }
      },
    }],
  })
}

// 逐年柱状图
function renderYearCharts() {
  if (!analysisData.value) return
  analysisData.value.analysis.forEach(h => {
    const el = document.querySelector(`[data-holiday="${h.name}"]`)
    if (!el) return

    if (yearCharts[h.name]) {
      yearCharts[h.name].dispose()
    }
    const chart = echarts.init(el)
    yearCharts[h.name] = chart

    const years = h.year_records.map(r => r.year)
    const values = h.year_records.map(r => r.change_pct)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: function(p) {
          return `${p[0].axisValue}年<br/>涨跌: ${p[0].value.toFixed(2)}%`
        }
      },
      grid: { left: 50, right: 20, top: 10, bottom: 30 },
      xAxis: {
        type: 'category',
        data: years,
        axisLabel: { fontSize: 9 },
      },
      yAxis: {
        type: 'value',
        name: '涨跌幅(%)',
        axisLabel: { formatter: '{value}%' },
      },
      series: [{
        type: 'bar',
        data: values.map(v => ({
          value: v,
          itemStyle: { color: v >= 0 ? '#cf1322' : '#3f8600' }
        })),
        barMaxWidth: 30,
        label: {
          show: true,
          position: 'top',
          fontSize: 9,
          formatter: p => p.value.toFixed(2) + '%'
        },
      }],
      dataZoom: [{ type: 'inside' }],
    })
  })
}

// 监听tab切换重新渲染逐年图
watch(activeTab, () => {
  setTimeout(() => renderYearCharts(), 100)
})

// 窗口大小变化时重绘
window.addEventListener('resize', () => {
  trendChart?.resize()
  heatmapChart?.resize()
  Object.values(yearCharts).forEach(c => c.resize())
})

// 初始化加载
onMounted(() => {
  handleRefresh()
})
</script>

<style scoped>
.holiday-summary-card {
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}
.holiday-summary-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}
.holiday-summary-card.best-card {
  border: 2px solid #cf1322;
}
.holiday-name {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}
.holiday-count {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
  font-size: 12px;
}
.stat-label {
  color: #666;
}
.stat-value {
  font-weight: bold;
}
.stat-value.up {
  color: #cf1322;
}
.stat-value.down {
  color: #3f8600;
}
</style>
