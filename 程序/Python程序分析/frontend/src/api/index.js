import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 120000,
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

// 同步股票代码列表
export function syncStockList() {
  return api.post('/stocks/sync')
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

export default api
