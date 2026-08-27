import { createRouter, createWebHistory } from 'vue-router'
import StockList from '../views/StockList.vue'
import StockDetail from '../views/StockDetail.vue'
import DataManagement from '../views/DataManagement.vue'
import ImportData from '../views/ImportData.vue'
import WeekdayAnalysis from '../views/WeekdayAnalysis.vue'
import HolidayAnalysis from '../views/HolidayAnalysis.vue'
import Simulation from '../views/Simulation.vue'
import ExportData from '../views/ExportData.vue'
import DividendReinvest from '../views/DividendReinvest.vue'
import DividendTarget from '../views/DividendTarget.vue'
import DipBuy from '../views/DipBuy.vue'

const routes = [
  { path: '/', redirect: '/stocks' },
  { path: '/stocks', name: 'StockList', component: StockList },
  { path: '/stocks/:code', name: 'StockDetail', component: StockDetail },
  { path: '/manage', name: 'DataManagement', component: DataManagement },
  { path: '/import', name: 'ImportData', component: ImportData },
  { path: '/simulation', name: 'Simulation', component: Simulation },
  { path: '/weekday', name: 'WeekdayAnalysis', component: WeekdayAnalysis },
  { path: '/holiday', name: 'HolidayAnalysis', component: HolidayAnalysis },
  { path: '/dividend-reinvest', name: 'DividendReinvest', component: DividendReinvest },
  { path: '/dividend-target', name: 'DividendTarget', component: DividendTarget },
  { path: '/dip-buy', name: 'DipBuy', component: DipBuy },
  { path: '/export', name: 'ExportData', component: ExportData },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
