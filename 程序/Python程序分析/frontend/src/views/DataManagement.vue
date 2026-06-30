<template>
  <div>
    <h2 style="margin-bottom: 16px">数据管理</h2>

    <a-space direction="vertical" :size="16" style="width: 100%; max-width: 800px">
      <!-- 同步股票列表 -->
      <a-card title="同步股票代码列表">
        <p style="color: #666; margin-bottom: 12px">
          从东方财富同步全市场 A 股代码和名称到数据库，用于在列表和详情页显示股票名称。
        </p>
        <a-button type="primary" @click="syncStocks" :loading="syncing">
          同步股票列表
        </a-button>
        <a-alert
          v-if="syncMsg"
          :message="syncMsg"
          :type="syncMsgType"
          closable
          style="margin-top: 12px"
          @close="syncMsg = ''"
        />
      </a-card>

      <!-- 批量拉取 -->
      <a-card title="批量拉取行情数据">
        <p style="color: #666; margin-bottom: 12px">
          选择多只股票批量拉取行情。单只股票的同步建议在详情页点击「同步行情」按钮。
        </p>
        <a-form layout="vertical" :model="formState" @finish="onFetch">
          <a-form-item label="选择股票">
            <a-select
              v-model:value="formState.selectedCodes"
              mode="multiple"
              :options="stockOptions"
              :filter-option="filterOption"
              placeholder="搜索并选择股票（可多选）"
              style="width: 100%"
              show-search
              :loading="stockListLoading"
            />
          </a-form-item>
          <a-form-item>
            <a-button type="primary" html-type="submit" :loading="fetching">
              批量拉取
            </a-button>
          </a-form-item>
        </a-form>

        <div v-if="results.length > 0" style="margin-top: 16px">
          <a-alert
            v-for="r in results"
            :key="r.stock_code"
            :type="r.status === 'ok' ? 'success' : r.status === 'error' ? 'error' : 'info'"
            style="margin-bottom: 8px"
          >
            <template #message>
              <strong>{{ r.stock_code }}</strong>
              <span v-if="stockNameMap[r.stock_code]"> {{ stockNameMap[r.stock_code] }}</span>
              <span v-if="r.details?.length">: {{ r.details.join('；') }}</span>
              <span v-else>: {{ r.message || r.status }}</span>
            </template>
          </a-alert>
        </div>
      </a-card>
    </a-space>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getStockList, syncStockList, fetchStockQuotes } from '../api'

const formState = reactive({
  selectedCodes: [],
})

const fetching = ref(false)
const results = ref([])

const syncing = ref(false)
const syncMsg = ref('')
const syncMsgType = ref('success')

const stockListLoading = ref(false)
const stockOptions = ref([])
const stockNameMap = ref({})

function filterOption(input, option) {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

async function syncStocks() {
  syncing.value = true
  syncMsg.value = ''
  try {
    const { data } = await syncStockList()
    syncMsg.value = data.message || '同步完成'
    syncMsgType.value = data.status === 'ok' ? 'success' : 'warning'
    if (data.status === 'ok') {
      await loadStockOptions()
    }
  } catch (e) {
    syncMsg.value = '同步失败: ' + (e.response?.data?.detail || e.message)
    syncMsgType.value = 'error'
  } finally {
    syncing.value = false
  }
}

async function loadStockOptions() {
  stockListLoading.value = true
  try {
    const { data } = await getStockList()
    const map = {}
    stockOptions.value = data.map(s => {
      const label = s.stock_name ? `${s.stock_code} ${s.stock_name}` : s.stock_code
      map[s.stock_code] = s.stock_name || ''
      return { value: s.stock_code, label }
    })
    stockNameMap.value = map
  } finally {
    stockListLoading.value = false
  }
}

async function onFetch() {
  if (formState.selectedCodes.length === 0) return

  fetching.value = true
  results.value = []

  // 逐只拉取（三种复权并行在服务端已完成）
  for (const code of formState.selectedCodes) {
    try {
      const { data } = await fetchStockQuotes(code)
      results.value.push(data)
    } catch (e) {
      results.value.push({
        stock_code: code,
        status: 'error',
        details: [e.response?.data?.detail || e.message],
      })
    }
  }

  fetching.value = false
}

onMounted(() => {
  loadStockOptions()
})
</script>
