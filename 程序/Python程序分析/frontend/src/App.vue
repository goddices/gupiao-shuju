<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header class="header">
      <div class="logo">📈 股票分析系统</div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        theme="dark"
        mode="horizontal"
        :items="menuItems"
        @click="onMenuClick"
      />
    </a-layout-header>
    <a-layout-content class="content">
      <router-view />
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const menuItems = [
  { key: '/stocks', label: '股票列表' },
  { key: '/weekday', label: '星期分析' },
  { key: '/holiday', label: '节日分析' },
  { key: '/import', label: '数据导入' },
  { key: '/export', label: '数据导出' },
  { key: '/simulation', label: '模拟交易' },
  { key: '/manage', label: '数据管理' },
]

const selectedKeys = computed(() => {
  const path = route.path
  if (path.startsWith('/stocks')) return ['/stocks']
  if (path.startsWith('/weekday')) return ['/weekday']
  if (path.startsWith('/holiday')) return ['/holiday']
  return [path]
})

function onMenuClick({ key }) {
  router.push(key)
}
</script>

<style>
.header {
  display: flex;
  align-items: center;
  gap: 24px;
}
.logo {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  white-space: nowrap;
}
.content {
  padding: 24px;
  background: #f5f5f5;
}
</style>
