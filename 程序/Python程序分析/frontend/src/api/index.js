import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 股票列表
export function getStockList() {
  return api.get('/stocks')
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

// 触发数据拉取
export function fetchStockData(stockCodes, startDate = '2006-01-01') {
  return api.post('/data/fetch', {
    stock_codes: stockCodes,
    start_date: startDate,
  })
}

export default api
