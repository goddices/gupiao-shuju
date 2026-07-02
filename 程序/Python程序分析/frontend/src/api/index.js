import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 120000,
})

// 股票列表
export function getStockList() {
  return api.get('/stocks')
}

// 全量股票代码和名称（用于数据管理页搜索选择）
export function searchStockInfo(q) {
  return api.get('/stocks/info', { params: { q } })
}

// 日K线数据
export function getStockQuotes(code, params = {}) {
  return api.get(`/stocks/${code}/quotes`, { params })
}

// 股票统计
export function getStockStats(code) {
  return api.get(`/stocks/${code}/stats`)
}

// 分红事件
export function getStockDividends(code, params = {}) {
  return api.get(`/stocks/${code}/dividends`, { params })
}

// 同步股票代码列表
export function syncStockList() {
  return api.post('/stocks/sync')
}

// 获取个股核心数据（从数据库读取）
export function getStockCoreData(code) {
  return api.get(`/stocks/${code}/core-data`)
}

// 同步个股核心数据（从东方财富拉取并保存）
export function syncStockCoreData(code) {
  return api.post(`/stocks/${code}/fetch-core-data`)
}

// 同步单只股票行情（不复权+前复权+后复权）
export function fetchStockQuotes(code) {
  return api.post(`/stocks/${code}/fetch`)
}

// 触发数据拉取
export function fetchStockData(stockCodes, startDate = '2006-01-01') {
  return api.post('/data/fetch', {
    stock_codes: stockCodes,
    start_date: startDate,
  })
}

// 星期涨跌分析
export function getWeekdayAnalysis(code) {
  return api.get(`/stocks/${code}/weekday-analysis`)
}

// 计算并保存星期涨跌统计
export function computeWeekdayStats(code) {
  return api.post(`/stocks/${code}/compute-weekday-stats`)
}

export default api
