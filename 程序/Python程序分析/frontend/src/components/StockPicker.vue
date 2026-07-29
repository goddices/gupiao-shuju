<template>
  <div class="stock-picker">
    <!-- 已添加的股票标签 -->
    <div v-if="items.length > 0" class="stock-tags">
      <a-tag
        v-for="s in items"
        :key="s.code"
        closable
        color="blue"
        @close="removeStock(s.code)"
      >
        {{ s.code }} {{ s.name || '' }}
      </a-tag>
    </div>

    <!-- 搜索/选择区域 -->
    <a-space direction="vertical" style="width: 100%">
      <!-- 从数据库搜索已有股票 -->
      <a-select
        v-model:value="selectedFromDB"
        mode="multiple"
        :options="options"
        :filter-option="() => true"
        placeholder="搜索数据库已有股票…"
        style="width: 100%"
        show-search
        :loading="loading"
        @search="(val) => $emit('search', val)"
        @change="onDBSelect"
      />

      <!-- 手动添加新股票（数据库中不存在的） -->
      <a-collapse :bordered="false" style="background: transparent">
        <a-collapse-panel key="1" header="＋ 手动添加（数据库中不存在的股票，需输入完整代码和名称）">
          <a-space :size="8">
            <a-input
              v-model:value="manualCode"
              placeholder="股票代码（如 688981）"
              style="width: 140px"
              maxlength="6"
              @press-enter="onManualAdd"
            />
            <a-input
              v-model:value="manualName"
              placeholder="股票名称（如 中芯国际）"
              style="width: 180px"
              @press-enter="onManualAdd"
            />
            <a-button
              type="primary"
              ghost
              @click="onManualAdd"
              :disabled="!canManualAdd"
            >
              添加
            </a-button>
          </a-space>
          <div style="color: #999; font-size: 12px; margin-top: 4px">
            手动添加需要同时填写代码和名称。已存在于数据库的股票请直接在上方搜索选择。
          </div>
        </a-collapse-panel>
      </a-collapse>
    </a-space>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { message as antMessage } from 'ant-design-vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  stockNameMap: { type: Object, default: () => ({}) },
  options: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'search'])

// ---- 所有 ref 和函数声明（在使用它们的 watch 之前） ----

const items = ref([])
const selectedFromDB = ref([])
const manualCode = ref('')
const manualName = ref('')

const canManualAdd = computed(() => {
  return manualCode.value.trim().length === 6 && manualName.value.trim().length > 0
})

function syncSelectValue() {
  selectedFromDB.value = items.value
    .filter(s => props.options?.find(o => o.value === s.code))
    .map(s => s.code)
}

function emitUpdate() {
  emit('update:modelValue', items.value.map(s => ({ ...s })))
}

function removeStock(code) {
  items.value = items.value.filter(s => s.code !== code)
  syncSelectValue()
  emitUpdate()
}

function onDBSelect(values) {
  const currentCodes = new Set(items.value.map(s => s.code))
  const added = values.filter(v => !currentCodes.has(v))
  for (const code of added) {
    const name = props.stockNameMap[code] || ''
    if (!items.value.find(s => s.code === code)) {
      items.value.push({ code, name })
    }
  }
  const keepSet = new Set(values)
  items.value = items.value.filter(s => keepSet.has(s.code) || !props.options?.find(o => o.value === s.code))
  syncSelectValue()
  emitUpdate()
}

function onManualAdd() {
  if (!canManualAdd.value) return
  const code = manualCode.value.trim()
  const name = manualName.value.trim()
  if (items.value.find(s => s.code === code)) {
    antMessage.warning(`股票 ${code} 已添加`)
    return
  }
  items.value.push({ code, name })
  syncSelectValue()
  emitUpdate()
  manualCode.value = ''
  manualName.value = ''
}

// ---- watch 放在最后，确保引用的所有 ref/function 都已初始化 ----

watch(() => props.modelValue, (val) => {
  items.value = val ? [...val] : []
  syncSelectValue()
}, { immediate: true })

watch(() => props.options, () => syncSelectValue())
</script>

<style scoped>
.stock-picker { width: 100%; }
.stock-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
</style>
