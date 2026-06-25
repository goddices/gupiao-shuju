<template>
  <div>
    <h2 style="margin-bottom: 16px">数据管理</h2>

    <a-card title="拉取股票数据" style="max-width: 600px">
      <a-form layout="vertical" @finish="onFetch">
        <a-form-item label="股票代码（多个用逗号分隔）">
          <a-input
            v-model:value="stockCodes"
            placeholder="如: 601857,600036,000858"
          />
        </a-form-item>
        <a-form-item label="起始日期">
          <a-input v-model:value="startDate" placeholder="2006-01-01" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="fetching">
            开始拉取
          </a-button>
        </a-form-item>
      </a-form>

      <!-- 结果展示 -->
      <div v-if="results.length > 0" style="margin-top: 16px">
        <a-alert
          v-for="r in results"
          :key="r.stock_code"
          :type="r.new_rows > 0 ? 'success' : 'info'"
          :message="`${r.stock_code}: ${r.message}`"
          style="margin-bottom: 8px"
        />
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { fetchStockData } from '../api'

const stockCodes = ref('')
const startDate = ref('2006-01-01')
const fetching = ref(false)
const results = ref([])

async function onFetch() {
  const codes = stockCodes.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  if (codes.length === 0) return

  fetching.value = true
  results.value = []
  try {
    const { data } = await fetchStockData(codes, startDate.value)
    results.value = data.details || []
  } finally {
    fetching.value = false
  }
}
</script>
