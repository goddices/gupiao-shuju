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

// 节日涨跌分析
export function getHolidayAnalysis(code) {
  return api.get('/holiday/analysis', { params: { stock_code: code } })
}

// ====== 红利再投 ======

// 分红明细列表
export function getDividendDetails(code, params = {}) {
  return api.get(`/dividend-reinvest/${code}/dividends`, { params })
}

// 同步分红明细（从东方财富拉取入库）
export function syncDividendReinvest(code) {
  return api.post(`/dividend-reinvest/${code}/sync`)
}

// 红利再投模拟
export function simulateDividendReinvest(code, payload) {
  return api.post(`/dividend-reinvest/${code}/simulate`, payload)
}

// ====== 分红目标测算 ======

// 目标年分红测算：买入日 + 目标年分红 → 所需买入资金
export function planDividendTarget(code, payload) {
  return api.post(`/dividend-target/${code}/plan`, payload)
}

// ====== 大跌买入 + 红利再投 ======

// 回撤 x% 买入 y 万 + 红利再投模拟
export function simulateDipBuy(code, payload) {
  return api.post(`/dip-buy/${code}/simulate`, payload)
}

// ====== 数据导入 ======

// 导入行情数据
export function importQuotes(stockCodes, startDate = '2006-01-01', endDate = null, dataSource = 'eastmoney') {
  return api.post('/import/quotes', {
    stock_codes: stockCodes,
    start_date: startDate,
    end_date: endDate,
    data_source: dataSource,
  })
}

// 导入基础信息（股票列表 + 核心数据）
export function importBasicInfo(stockCodes = null, syncList = true, dataSource = 'eastmoney') {
  return api.post('/import/basic-info', {
    stock_codes: stockCodes,
    sync_stock_list: syncList,
    data_source: dataSource,
  })
}

// 获取当前数据源
export function getDatasource() {
  return api.get('/import/datasource')
}

// ====== 模拟交易 ======

// 账户概览
export function getSimAccount() {
  return api.get('/simulation/account')
}

// 买入
export function simBuy(params) {
  return api.post('/simulation/buy', null, { params })
}

// 卖出
export function simSell(params) {
  return api.post('/simulation/sell', null, { params })
}

// 交易记录
export function getSimTrades(limit = 50) {
  return api.get('/simulation/trades', { params: { limit } })
}

// 重置账户
export function resetSimAccount(initialCash = 100000) {
  return api.post('/simulation/reset', null, { params: { initial_cash: initialCash } })
}

// 更新费率
export function updateFeeConfig(params) {
  return api.put('/simulation/fee-config', null, { params })
}

// ====== 数据导出 ======

// 启动全库 SQL 导出
export function startExport() {
  return api.post('/export/sql')
}

// 查询导出进度
export function getExportProgress(taskId) {
  return api.get(`/export/progress/${taskId}`)
}

// 下载导出的 SQL 文件
export function downloadExport(taskId) {
  return api.get(`/export/download/${taskId}`, { responseType: 'blob' })
}

export default api
