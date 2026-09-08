<template>
  <a-config-provider :theme="themeConfig">
    <a-layout style="min-height: 100vh" :class="{ dark: isDark }">
      <a-layout-sider
        v-model:collapsed="collapsed"
        collapsible
        :theme="isDark ? 'dark' : 'light'"
        :width="220"
        class="sider"
      >
        <div class="logo">
          <span v-if="!collapsed">📈 股票分析系统</span>
          <span v-else>📈</span>
        </div>
        <a-menu
          v-model:selectedKeys="selectedKeys"
          v-model:openKeys="openKeys"
          :theme="isDark ? 'dark' : 'light'"
          mode="inline"
          :items="menuItems"
          @click="onMenuClick"
        />
        <div class="theme-toggle">
          <a-switch :checked="isDark" @change="toggleTheme">
            <template #checkedChildren><BulbFilled /></template>
            <template #unCheckedChildren><BulbOutlined /></template>
          </a-switch>
          <span v-if="!collapsed" class="theme-label">{{ isDark ? '暗色模式' : '亮色模式' }}</span>
        </div>
      </a-layout-sider>
      <a-layout-content class="content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { computed, h, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { theme } from 'ant-design-vue'
import {
  LineChartOutlined,
  UnorderedListOutlined,
  BarChartOutlined,
  CalendarOutlined,
  GiftOutlined,
  ExperimentOutlined,
  ReloadOutlined,
  CalculatorOutlined,
  FallOutlined,
  PlayCircleOutlined,
  DatabaseOutlined,
  ImportOutlined,
  ExportOutlined,
  ToolOutlined,
  BulbOutlined,
  BulbFilled,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()

const menuItems = [
  {
    key: 'market',
    label: '行情数据',
    icon: () => h(LineChartOutlined),
    children: [
      { key: '/stocks', label: '股票列表', icon: () => h(UnorderedListOutlined) },
    ],
  },
  {
    key: 'analysis',
    label: '统计分析',
    icon: () => h(BarChartOutlined),
    children: [
      { key: '/weekday', label: '星期分析', icon: () => h(CalendarOutlined) },
      { key: '/holiday', label: '节日分析', icon: () => h(GiftOutlined) },
    ],
  },
  {
    key: 'strategy',
    label: '策略回测',
    icon: () => h(ExperimentOutlined),
    children: [
      { key: '/dividend-reinvest', label: '红利再投', icon: () => h(ReloadOutlined) },
      { key: '/dividend-target', label: '分红测算', icon: () => h(CalculatorOutlined) },
      { key: '/dip-buy', label: '大跌买入', icon: () => h(FallOutlined) },
      { key: '/simulation', label: '模拟交易', icon: () => h(PlayCircleOutlined) },
    ],
  },
  {
    key: 'data',
    label: '数据管理',
    icon: () => h(DatabaseOutlined),
    children: [
      { key: '/import', label: '数据导入', icon: () => h(ImportOutlined) },
      { key: '/export', label: '数据导出', icon: () => h(ExportOutlined) },
      { key: '/manage', label: '数据管理', icon: () => h(ToolOutlined) },
    ],
  },
]

const selectedKeys = computed(() => {
  const path = route.path
  if (path.startsWith('/stocks')) return ['/stocks']
  return [path]
})

function groupOf(path) {
  if (path.startsWith('/stocks')) return 'market'
  if (['/weekday', '/holiday'].some((p) => path.startsWith(p))) return 'analysis'
  if (['/dividend-reinvest', '/dividend-target', '/dip-buy', '/simulation'].some((p) => path.startsWith(p)))
    return 'strategy'
  return 'data'
}

const collapsed = ref(false)
const openKeys = ref([groupOf(route.path)])
let savedOpenKeys = [...openKeys.value]

watch(
  () => route.path,
  (path) => {
    const g = groupOf(path)
    if (!collapsed.value && !openKeys.value.includes(g)) {
      openKeys.value = [...openKeys.value, g]
    }
  },
)

watch(collapsed, (v) => {
  if (v) {
    savedOpenKeys = [...openKeys.value]
    openKeys.value = []
  } else {
    openKeys.value = savedOpenKeys.length ? savedOpenKeys : [groupOf(route.path)]
  }
})

// 主题切换（亮 / 暗），记忆用户选择
const isDark = ref(localStorage.getItem('app-theme') === 'dark')
const themeConfig = computed(() => ({
  algorithm: isDark.value ? theme.darkAlgorithm : theme.defaultAlgorithm,
}))

function toggleTheme(v) {
  isDark.value = v
  localStorage.setItem('app-theme', v ? 'dark' : 'light')
}

function onMenuClick({ key }) {
  if (key.startsWith('/')) router.push(key)
}
</script>

<style>
.sider {
  position: relative;
}
.sider .ant-layout-sider-children {
  display: flex;
  flex-direction: column;
}
.sider .ant-menu {
  flex: 1;
  overflow-y: auto;
}
.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  color: rgba(0, 0, 0, 0.85);
}
.dark .logo {
  color: #fff;
}
.content {
  padding: 24px;
  background: #f5f5f5;
  transition: background 0.3s;
}
.dark .content {
  background: #141414;
}
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 0;
  margin-bottom: 48px; /* 留出折叠按钮的位置 */
}
.theme-label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}
.dark .theme-label {
  color: rgba(255, 255, 255, 0.45);
}
</style>
