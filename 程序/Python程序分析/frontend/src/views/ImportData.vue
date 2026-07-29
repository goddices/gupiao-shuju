<template>
  <div>
    <h2 style="margin-bottom: 16px">📥 数据导入</h2>

    <a-tabs v-model:activeKey="activeTab">
      <!-- ========== 行情导入 ========== -->
      <a-tab-pane key="quotes" tab="📊 行情导入">
        <a-card style="max-width: 860px">
          <a-form layout="vertical" @finish="onImportQuotes">
            <!-- 数据源选择 -->
            <a-form-item label="数据源">
              <a-radio-group v-model:value="quoteForm.dataSource">
                <a-radio-button value="eastmoney">东方财富 (默认)</a-radio-button>
                <a-radio-button value="akshare">AKShare</a-radio-button>
              </a-radio-group>
              <div style="color: #999; font-size: 12px; margin-top: 4px">
                选择从哪个数据源拉取行情。东方财富支持并行三路复权；AKShare 串行获取。
              </div>
            </a-form-item>

            <!-- OHLC 字段映射说明 -->
            <a-form-item label="行情字段映射 (OHLC)">
              <a-table
                :data-source="ohlcMapping"
                :columns="ohlcColumns"
                :pagination="false"
                size="small"
                :bordered="true"
                style="max-width: 700px"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'field'">
                    <span :style="{ fontWeight: 600, color: record.color }">{{ record.label }}</span>
                    <div style="font-size: 11px; color: #999">{{ record.desc }}</div>
                  </template>
                  <template v-else-if="column.key === 'eastmoney'">
                    <code style="font-size: 12px">{{ record.eastmoney }}</code>
                  </template>
                  <template v-else-if="column.key === 'akshare'">
                    <code style="font-size: 12px">{{ record.akshare }}</code>
                  </template>
                  <template v-else-if="column.key === 'db'">
                    <code style="font-size: 12px; color: #1677ff">{{ record.db }}</code>
                  </template>
                </template>
              </a-table>
              <div style="color: #999; font-size: 11px; margin-top: 4px">
                每只股票拉取 <b>三套复权</b>：不复权填入基础列，前复权填 forward_* 列，后复权填 backward_* 列。
              </div>
            </a-form-item>

            <!-- 股票选择区域 -->
            <a-form-item label="选择股票">
              <StockPicker
                v-model="quoteForm.stockList"
                :stock-name-map="stockNameMap"
                @search="onSearchInput"
                :loading="stockListLoading"
                :options="stockOptions"
              />
            </a-form-item>

            <!-- 日期范围 -->
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item label="起始日期">
                  <a-date-picker v-model:value="quoteForm.startDate" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="结束日期（留空 = 今天）">
                  <a-date-picker v-model:value="quoteForm.endDate" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>

            <a-form-item>
              <a-button
                type="primary"
                html-type="submit"
                :loading="importingQuotes"
                :disabled="quoteForm.stockList.length === 0"
                size="large"
              >
                开始导入行情
              </a-button>
              <span style="margin-left: 12px; color: #999; font-size: 12px">
                已添加 {{ quoteForm.stockList.length }} 只股票
              </span>
            </a-form-item>
          </a-form>

          <!-- 导入结果 -->
          <div v-if="quoteResults.length > 0" style="margin-top: 16px">
            <a-divider>导入结果</a-divider>
            <a-alert
              v-for="r in quoteResults"
              :key="r.stock_code"
              :type="r.status === 'ok' || r.status === 'no_new_data' ? 'success' : r.status === 'error' ? 'error' : 'warning'"
              style="margin-bottom: 8px; white-space: pre-wrap"
            >
              <template #message>
                <strong>{{ r.stock_code }}</strong>
                <span v-if="stockNameMap[r.stock_code]"> {{ stockNameMap[r.stock_code] }}</span>
                <span v-else-if="getManualName(r.stock_code, 'quote')"> {{ getManualName(r.stock_code, 'quote') }}</span>
                : {{ r.msg }} ({{ r.rows || 0 }} 行)
              </template>
            </a-alert>
          </div>
        </a-card>
      </a-tab-pane>

      <!-- ========== 基础信息导入 ========== -->
      <a-tab-pane key="basic" tab="🏷️ 基础信息导入">
        <a-card style="max-width: 860px">
          <a-form layout="vertical" @finish="onImportBasic">
            <!-- 数据源选择 -->
            <a-form-item label="数据源">
              <a-radio-group v-model:value="basicForm.dataSource">
                <a-radio-button value="eastmoney">东方财富 (默认)</a-radio-button>
                <a-radio-button value="akshare">AKShare</a-radio-button>
              </a-radio-group>
            </a-form-item>

            <!-- 同步股票列表 -->
            <a-form-item label="同步全市场股票列表">
              <a-switch v-model:checked="basicForm.syncList" />
              <span style="margin-left: 8px; color: #666; font-size: 13px">
                勾选后先从数据源拉取全部 A 股代码和名称，写入 stock_info 表
              </span>
            </a-form-item>

            <!-- 个股核心数据 -->
            <a-form-item label="导入核心数据（PE/PB/ROE/市值等）">
              <StockPicker
                v-model="basicForm.stockList"
                :stock-name-map="stockNameMap"
                @search="onSearchInput"
                :loading="stockListLoading"
                :options="stockOptions"
              />
              <div style="color: #999; font-size: 12px; margin-top: 4px">
                留空则只执行「同步全市场股票列表」
              </div>
            </a-form-item>

            <a-form-item>
              <a-button
                type="primary"
                html-type="submit"
                :loading="importingBasic"
                size="large"
              >
                开始导入基础信息
              </a-button>
            </a-form-item>
          </a-form>

          <!-- 导入结果 -->
          <div v-if="basicResults.length > 0" style="margin-top: 16px">
            <a-divider>导入结果</a-divider>
            <a-alert
              v-for="(r, i) in basicResults"
              :key="i"
              :type="r.status === 'ok' ? 'success' : r.status === 'error' ? 'error' : 'warning'"
              style="margin-bottom: 8px"
            >
              <template #message>
                <template v-if="r.stock_code === '*'">全量股票列表</template>
                <template v-else><strong>{{ r.stock_code }}</strong></template>
                : {{ r.msg || r.status }}
              </template>
            </a-alert>
          </div>
        </a-card>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { searchStockInfo, importQuotes, importBasicInfo } from '../api'
import StockPicker from '../components/StockPicker.vue'

const activeTab = ref('quotes')

// ========== OHLC 字段映射表 ==========
const ohlcColumns = [
  { title: '行情字段', key: 'field', width: 120 },
  { title: '东方财富 (位置)', key: 'eastmoney' },
  { title: 'AKShare (列名)', key: 'akshare' },
  { title: '数据库列', key: 'db' },
]

const ohlcMapping = [
  { label: '开盘价', desc: 'Open',   color: '#e74c3c', eastmoney: 'data[1]', akshare: 'row["开盘"]',  db: 'open_price' },
  { label: '最高价', desc: 'High',   color: '#e67e22', eastmoney: 'data[3]', akshare: 'row["最高"]',  db: 'high_price' },
  { label: '最低价', desc: 'Low',    color: '#2ecc71', eastmoney: 'data[4]', akshare: 'row["最低"]',  db: 'low_price' },
  { label: '收盘价', desc: 'Close',  color: '#3498db', eastmoney: 'data[2]', akshare: 'row["收盘"]',  db: 'close_price' },
  { label: '成交量', desc: 'Volume', color: '#9b59b6', eastmoney: 'data[5]', akshare: 'row["成交量"]', db: 'volume' },
  { label: '成交额', desc: 'Amount', color: '#1abc9c', eastmoney: 'data[6]', akshare: 'row["成交额"]', db: 'amount' },
]

// ========== 股票搜索（共享） ==========
const stockListLoading = ref(false)
const stockOptions = ref([])
const stockNameMap = ref({})
let searchTimer = null

function onSearchInput(value) {
  clearTimeout(searchTimer)
  if (!value || !value.trim()) { stockOptions.value = []; return }
  searchTimer = setTimeout(() => doSearch(value.trim()), 300)
}

async function doSearch(keyword) {
  if (!keyword) return
  stockListLoading.value = true
  try {
    const { data } = await searchStockInfo(keyword)
    const map = {}
    stockOptions.value = data.map(s => {
      const label = s.stock_name ? `${s.stock_code} ${s.stock_name}` : s.stock_code
      map[s.stock_code] = s.stock_name || ''
      return { value: s.stock_code, label }
    })
    Object.assign(stockNameMap.value, map)
  } catch (e) {
    stockOptions.value = []
  } finally {
    stockListLoading.value = false
  }
}

// 当股票不在 DB (stockNameMap) 中时，从手动添加列表里获取名称
function getManualName(code, form) {
  const list = form === 'quote' ? quoteForm.stockList : basicForm.stockList
  const item = list.find(s => s.code === code)
  return item?.name || ''
}

// ========== 行情导入 ==========
const quoteForm = reactive({
  dataSource: 'eastmoney',
  stockList: [],
  startDate: null,
  endDate: null,
})

const importingQuotes = ref(false)
const quoteResults = ref([])

async function onImportQuotes() {
  if (quoteForm.stockList.length === 0) {
    message.warning('请添加至少一只股票')
    return
  }

  importingQuotes.value = true
  quoteResults.value = []

  const codes = quoteForm.stockList.map(s => s.code)
  const startDate = quoteForm.startDate
    ? dayjs(quoteForm.startDate).format('YYYY-MM-DD')
    : '2006-01-01'
  const endDate = quoteForm.endDate
    ? dayjs(quoteForm.endDate).format('YYYYMMDD')
    : null

  try {
    const { data } = await importQuotes(codes, startDate, endDate, quoteForm.dataSource)
    quoteResults.value = data.details || []
    const okCount = data.ok || 0
    const failCount = data.fail || 0
    if (failCount === 0) {
      message.success(`行情导入完成: ${okCount} 只股票成功`)
    } else {
      message.warning(`行情导入完成: ${okCount} 成功, ${failCount} 失败`)
    }
  } catch (e) {
    message.error('导入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    importingQuotes.value = false
  }
}

// ========== 基础信息导入 ==========
const basicForm = reactive({
  dataSource: 'eastmoney',
  syncList: true,
  stockList: [],
})

const importingBasic = ref(false)
const basicResults = ref([])

async function onImportBasic() {
  importingBasic.value = true
  basicResults.value = []

  const codes = basicForm.stockList.length > 0 ? basicForm.stockList.map(s => s.code) : null

  try {
    const { data } = await importBasicInfo(codes, basicForm.syncList, basicForm.dataSource)
    basicResults.value = data.details || []
    const okCount = data.ok || 0
    const failCount = data.fail || 0
    if (failCount === 0) {
      message.success(`基础信息导入完成: ${okCount} 项成功`)
    } else {
      message.warning(`基础信息导入完成: ${okCount} 成功, ${failCount} 失败`)
    }
  } catch (e) {
    message.error('导入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    importingBasic.value = false
  }
}
</script>
