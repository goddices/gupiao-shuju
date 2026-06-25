import { createRouter, createWebHistory } from 'vue-router'
import StockList from '../views/StockList.vue'
import StockDetail from '../views/StockDetail.vue'
import DataManagement from '../views/DataManagement.vue'

const routes = [
  { path: '/', redirect: '/stocks' },
  { path: '/stocks', name: 'StockList', component: StockList },
  { path: '/stocks/:code', name: 'StockDetail', component: StockDetail },
  { path: '/manage', name: 'DataManagement', component: DataManagement },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
