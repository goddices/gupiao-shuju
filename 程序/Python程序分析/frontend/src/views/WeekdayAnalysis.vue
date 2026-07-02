<template>
  <div class="weekday-analysis">
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
          <a-space>
            <a-button type="primary" @click="handleCompute" :loading="computing">
              计算星期统计
            </a-button>
            <a-button @click="handleRefresh" :loading="loading" :disabled="!selectedStock">
              刷新数据
            </a-button>
          </a-space>
        </a-col>
        <a-col :span="8" v-if="analysisData">
          <a-tag color="blue">统计区间: {{ analysisData.date_range_start }} ~ {{ analysisData.date_range_end }}</a-tag>
          <a-tag color="purple" style="margin-left: 8px">共 {{ analysisData.total_trading_days }} 个交易日</a-tag>
        </a-col>
      </a-row>
    </a-card>

    <!-- 加载或空状态 -->
    <a-card v-if="!analysisData && !loading">
      <a-empty description="请选择股票并点击「计算星期统计」或「刷新数据」" />
    </a-card>

    <a-spin :spinning="loading || computing" tip="加载中...">
      <template v-if="analysisData">
        <!-- 星期统计卡片 -->
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="4" v-for="wd in weekdayOrder" :key="wd">
            <a-card
              :class="['weekday-stat-card', getCardClass(wd)]"
              size="small"
              @click="selectedWeekday = wd"
            >
              <div class="stat-card-header">{{ wd }}</div>
              <div class="stat-card-body">
                <div class="stat-item">
                  <span class="stat-label">上涨</span>
                  <span class="stat-value up">{{ getStat(wd).up_pct.toFixed(1) }}%</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">下跌</span>
                  <span class="stat-value down">{{ getStat(wd).down_pct.toFixed(1) }}%</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">均值</span>
                  <span :class="['stat-value', getStat(wd).mean_change >= 0 ? 'up' : 'down']">
                    {{ getStat(wd).mean_change.toFixed(2) }}%
                  </span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">样本</span>
                  <span class="stat-value">{{ getStat(wd).total_count }}天</span>
                </div>
              </div>
            </a-card>
          </a-col>
        </a-row>

        <!-- 日历视图 + 详细统计 -->
        <a-row :gutter="16">
          <!-- 左侧：日历 -->
          <a-col :span="14">
            <a-card title="📅 月度概率日历" size="small">
              <template #extra>
                <a-space>
                  <a-button size="small" @click="prevMonth">&lt;</a-button>
                  <span style="font-weight: bold">{{ calendarTitle }}</span>
                  <a-button size="small" @click="nextMonth">&gt;</a-button>
                  <a-button size="small" @click="goToToday">今天</a-button>
                </a-space>
              </template>
              <div class="calendar-legend">
                <span class="legend-item"><span class="legend-dot" style="background: #cf1322"></span> 涨&gt;55%</span>
                <span class="legend-item"><span class="legend-dot" style="background: #ff7875"></span> 涨&gt;50%</span>
                <span class="legend-item"><span class="legend-dot" style="background: #d9d9d9"></span> 持平</span>
                <span class="legend-item"><span class="legend-dot" style="background: #95de64"></span> 跌&gt;50%</span>
                <span class="legend-item"><span class="legend-dot" style="background: #389e0d"></span> 跌&gt;55%</span>
              </div>
              <div class="calendar-grid">
                <div class="calendar-header" v-for="d in dayHeaders" :key="d">{{ d }}</div>
                <div
                  v-for="(cell, idx) in calendarCells"
                  :key="idx"
                  :class="['calendar-cell', cell.cssClass]"
                  :title="cell.tooltip"
                >
                  <span class="cell-date">{{ cell.day }}</span>
                  <span v-if="cell.prob !== null" class="cell-prob">{{ cell.prob }}%</span>
                </div>
              </div>
            </a-card>
          </a-col>

          <!-- 右侧：详细统计 + 预测 -->
          <a-col :span="10">
            <a-card title="📊 未来5个交易日预测" size="small" style="margin-bottom: 16px">
              <a-table
                :columns="predictionColumns"
                :data-source="analysisData.predictions"
                :pagination="false"
                size="small"
                row-key="date"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'up_probability'">
                    <span style="color: #cf1322; font-weight: bold">{{ record.up_probability.toFixed(1) }}%</span>
                  </template>
                  <template v-if="column.key === 'down_probability'">
                    <span style="color: #3f8600; font-weight: bold">{{ record.down_probability.toFixed(1) }}%</span>
                  </template>
                  <template v-if="column.key === 'mean_change'">
                    <span :style="{ color: record.mean_change >= 0 ? '#cf1322' : '#3f8600' }">
                      {{ record.mean_change.toFixed(2) }}%
                    </span>
                  </template>
                </template>
              </a-table>
            </a-card>

            <a-card title="📋 星期详细统计" size="small">
              <a-table
                :columns="detailColumns"
                :data-source="analysisData.weekday_stats"
                :pagination="false"
                size="small"
                row-key="weekday"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'up_pct'">
                    <span style="color: #cf1322">{{ record.up_pct.toFixed(1) }}%</span>
                  </template>
                  <template v-if="column.key === 'down_pct'">
                    <span style="color: #3f8600">{{ record.down_pct.toFixed(1) }}%</span>
                  </template>
                  <template v-if="column.key === 'mean_change'">
                    <span :style="{ color: record.mean_change >= 0 ? '#cf1322' : '#3f8600' }">
                      {{ record.mean_change.toFixed(3) }}%
                    </span>
                  </template>
                </template>
              </a-table>
              <a-divider />
              <div v-if="analysisData.best_weekday">
                <a-tag color="red">最佳: {{ analysisData.best_weekday }} (均值最高)</a-tag>
                <a-tag color="green" style="margin-left: 8px">最差: {{ analysisData.worst_weekday }} (均值最低)</a-tag>
              </div>
            </a-card>
          </a-col>
        </a-row>
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { getWeekdayAnalysis, computeWeekdayStats, searchStockInfo } from '../api'

const WEEKDAY_ORDER = ['星期一', '星期二', '星期三', '星期四', '星期五']
const DAY_HEADERS = ['一', '二', '三', '四', '五', '六', '日']

// 股票选择
const selectedStock = ref(null)
const stockOptions = ref([])
const computing = ref(false)
const loading = ref(false)
const analysisData = ref(null)

// 日历
const calendarYear = ref(new Date().getFullYear())
const calendarMonth = ref(new Date().getMonth() + 1)
const selectedWeekday = ref(null)

const calendarTitle = computed(() => `${calendarYear.value}年${calendarMonth.value}月`)

const dayHeaders = DAY_HEADERS

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

async function handleCompute() {
  if (!selectedStock.value) {
    message.warning('请先选择股票')
    return
  }
  computing.value = true
  try {
    const { data } = await computeWeekdayStats(selectedStock.value)
    message.success(data.message || '计算完成')
    await handleRefresh()
  } catch (e) {
    message.error(e.response?.data?.detail || e.message || '计算失败')
  } finally {
    computing.value = false
  }
}

async function handleRefresh() {
  if (!selectedStock.value) return
  loading.value = true
  try {
    const { data } = await getWeekdayAnalysis(selectedStock.value)
    analysisData.value = data
  } catch (e) {
    if (e.response?.status === 404) {
      message.warning('暂无星期统计数据，请先点击「计算星期统计」')
      analysisData.value = null
    } else {
      message.error(e.response?.data?.detail || e.message || '加载失败')
    }
  } finally {
    loading.value = false
  }
}

// 获取某星期的统计数据
function getStat(wd) {
  const s = (analysisData.value?.weekday_stats || []).find(i => i.weekday === wd)
  return s || { up_pct: 0, down_pct: 0, mean_change: 0, total_count: 0, up_count: 0, down_count: 0 }
}

function getCardClass(wd) {
  if (selectedWeekday.value === wd) return 'selected'
  return ''
}

// 日历单元格
const calendarCells = computed(() => {
  const year = calendarYear.value
  const month = calendarMonth.value
  const firstDay = new Date(year, month - 1, 1)
  const lastDay = new Date(year, month, 0)
  const daysInMonth = lastDay.getDate()
  // 周一=0, 周日=6 (这里用中国习惯: 周一=0)
  const startDayOfWeek = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1

  const statsMap = {}
  if (analysisData.value) {
    for (const s of analysisData.value.weekday_stats) {
      statsMap[s.weekday] = s
    }
  }

  const today = new Date()
  const cells = []

  // 前置空白格
  for (let i = 0; i < startDayOfWeek; i++) {
    cells.push({ day: '', prob: null, cssClass: 'empty', tooltip: '' })
  }

  // 日期格
  for (let d = 1; d <= daysInMonth; d++) {
    const date = new Date(year, month - 1, d)
    const isToday = date.toDateString() === today.toDateString()
    const isWeekend = date.getDay() === 0 || date.getDay() === 6

    let cssClass = ''
    let prob = null
    let tooltip = ''

    if (isWeekend) {
      cssClass = 'weekend'
      tooltip = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')} 周末休市`
      if (isToday) cssClass += ' today'
    } else {
      const cnName = WEEKDAY_ORDER[date.getDay() === 0 ? 6 : date.getDay() - 1]
      const stat = statsMap[cnName]
      if (stat && stat.total_count > 0) {
        prob = stat.up_pct
        const upPct = stat.up_pct
        if (upPct > 55) {
          cssClass = 'prob-high-up'
        } else if (upPct > 50) {
          cssClass = 'prob-mid-up'
        } else if (upPct < 45) {
          cssClass = 'prob-high-down'
        } else if (upPct < 50) {
          cssClass = 'prob-mid-down'
        } else {
          cssClass = 'prob-even'
        }
        tooltip = `${cnName} | 涨:${stat.up_pct.toFixed(1)}% 跌:${stat.down_pct.toFixed(1)}% | 样本:${stat.total_count}天 | 均值:${stat.mean_change.toFixed(2)}%`
      } else {
        cssClass = 'no-data'
        tooltip = `${cnName} - 无数据`
      }
      if (isToday) cssClass += ' today'
    }

    cells.push({ day: d, prob: prob !== null ? Math.round(prob) : null, cssClass, tooltip })
  }

  return cells
})

function prevMonth() {
  if (calendarMonth.value === 1) {
    calendarMonth.value = 12
    calendarYear.value--
  } else {
    calendarMonth.value--
  }
}

function nextMonth() {
  if (calendarMonth.value === 12) {
    calendarMonth.value = 1
    calendarYear.value++
  } else {
    calendarMonth.value++
  }
}

function goToToday() {
  const today = new Date()
  calendarYear.value = today.getFullYear()
  calendarMonth.value = today.getMonth() + 1
}

// 预测表格列定义
const predictionColumns = [
  { title: '日期', dataIndex: 'date', key: 'date' },
  { title: '星期', dataIndex: 'weekday', key: 'weekday' },
  { title: '上涨概率', dataIndex: 'up_probability', key: 'up_probability' },
  { title: '下跌概率', dataIndex: 'down_probability', key: 'down_probability' },
  { title: '均值涨跌', dataIndex: 'mean_change', key: 'mean_change' },
  { title: '历史样本', dataIndex: 'sample_count', key: 'sample_count' },
]

// 详细统计表格列定义
const detailColumns = [
  { title: '星期', dataIndex: 'weekday', key: 'weekday', width: 70 },
  { title: '交易日', dataIndex: 'total_count', key: 'total_count', width: 60 },
  { title: '上涨', dataIndex: 'up_count', key: 'up_count', width: 50 },
  { title: '下跌', dataIndex: 'down_count', key: 'down_count', width: 50 },
  { title: '上涨率', dataIndex: 'up_pct', key: 'up_pct', width: 80 },
  { title: '下跌率', dataIndex: 'down_pct', key: 'down_pct', width: 80 },
  { title: '均值%', dataIndex: 'mean_change', key: 'mean_change', width: 80 },
  { title: '最大涨%', dataIndex: 'max_gain', key: 'max_gain', width: 80 },
  { title: '最大跌%', dataIndex: 'max_loss', key: 'max_loss', width: 80 },
]
</script>

<style scoped>
.weekday-analysis {
  max-width: 1400px;
  margin: 0 auto;
}

/* 星期统计卡片 */
.weekday-stat-card {
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}
.weekday-stat-card:hover {
  border-color: #1890ff;
}
.weekday-stat-card.selected {
  border-color: #1890ff;
  box-shadow: 0 0 8px rgba(24, 144, 255, 0.3);
}
.stat-card-header {
  text-align: center;
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
}
.stat-card-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.stat-label {
  color: #888;
}
.stat-value {
  font-weight: bold;
}
.stat-value.up { color: #cf1322; }
.stat-value.down { color: #3f8600; }

/* 日历 */
.calendar-legend {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  font-size: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.legend-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  text-align: center;
}
.calendar-header {
  font-weight: bold;
  padding: 8px 0;
  background: #fafafa;
  font-size: 14px;
}
.calendar-cell {
  aspect-ratio: 1.2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: default;
  font-size: 14px;
  position: relative;
}
.calendar-cell.empty {
  background: transparent;
}
.calendar-cell.weekend {
  background: #f5f5f5;
  color: #bbb;
}
.calendar-cell.no-data {
  background: #fafafa;
  color: #999;
}
.calendar-cell.prob-high-up {
  background: #ffccc7;
  color: #a8071a;
}
.calendar-cell.prob-mid-up {
  background: #ffd8bf;
  color: #ad4e00;
}
.calendar-cell.prob-even {
  background: #f0f0f0;
  color: #666;
}
.calendar-cell.prob-mid-down {
  background: #d9f7be;
  color: #135200;
}
.calendar-cell.prob-high-down {
  background: #b7eb8f;
  color: #135200;
}
.calendar-cell.today {
  border: 2px solid #1890ff !important;
  font-weight: bold;
}
.calendar-cell:hover {
  filter: brightness(0.95);
}
.cell-date {
  font-size: 15px;
  font-weight: 500;
}
.cell-prob {
  font-size: 10px;
  margin-top: 2px;
}
</style>
