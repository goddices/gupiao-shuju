<template>
  <div ref="chartRef" :style="{ height: height }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
  height: { type: String, default: '400px' },
})

const chartRef = ref(null)
let chart = null

function buildOption(rawData) {
  if (!rawData || rawData.length === 0) return {}

  const dates = rawData.map((d) => d.trade_date)
  const ohlc = rawData.map((d) => [
    d.open_price,
    d.close_price,
    d.low_price,
    d.high_price,
  ])
  const volumes = rawData.map((d) => d.volume)
  const changes = rawData.map((d) => d._change || 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        const k = params.find((p) => p.seriesName === 'K线')
        const v = params.find((p) => p.seriesName === '成交量')
        const date = params[0].axisValue
        if (!k) return ''
        const vals = k.data
        return `
          日期: ${date}<br/>
          开盘: ${vals[1]}<br/>
          收盘: ${vals[2]}<br/>
          最低: ${vals[3]}<br/>
          最高: ${vals[4]}<br/>
          成交量: ${v ? (v.data / 10000).toFixed(0) + '万' : '-'}
        `
      },
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
    },
    grid: [
      { left: '3%', right: '8%', top: '5%', height: '60%' },
      { left: '3%', right: '8%', top: '72%', height: '15%' },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: true,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax',
        axisLabel: { show: false },
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        scale: true,
        boundaryGap: true,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        min: 'dataMin',
        max: 'dataMax',
      },
    ],
    yAxis: [
      {
        scale: true,
        splitArea: { show: true },
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 50, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], start: 50, end: 100, bottom: '5%' },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        itemStyle: {
          color: '#cf1322',
          color0: '#3f8600',
          borderColor: '#cf1322',
          borderColor0: '#3f8600',
        },
      },
      {
        name: 'MA5',
        type: 'line',
        data: calcMA(rawData, 5),
        smooth: true,
        lineStyle: { width: 1, opacity: 0.8 },
        symbol: 'none',
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      {
        name: 'MA10',
        type: 'line',
        data: calcMA(rawData, 10),
        smooth: true,
        lineStyle: { width: 1, opacity: 0.8 },
        symbol: 'none',
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      {
        name: 'MA20',
        type: 'line',
        data: calcMA(rawData, 20),
        smooth: true,
        lineStyle: { width: 1, opacity: 0.6 },
        symbol: 'none',
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes.map((v, i) => {
          const change = changes[i]
          return {
            value: v,
            itemStyle: {
              color: change >= 0 ? '#cf1322' : '#3f8600',
            },
          }
        }),
      },
    ],
  }
}

function calcMA(data, days) {
  const result = []
  for (let i = 0; i < data.length; i++) {
    if (i < days - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = 0; j < days; j++) {
        sum += data[i - j].close_price
      }
      result.push(+(sum / days).toFixed(2))
    }
  }
  return result
}

function render() {
  if (!chart || !chartRef.value) return
  const option = buildOption(props.data)
  chart.setOption(option, true)
}

onMounted(() => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
    render()
  }
})

onUnmounted(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
})

watch(() => props.data, () => {
  render()
}, { deep: true })

// 响应窗口大小变化
const resizeObserver = new ResizeObserver(() => {
  chart?.resize()
})
onMounted(() => {
  if (chartRef.value) resizeObserver.observe(chartRef.value)
})
onUnmounted(() => {
  resizeObserver.disconnect()
})
</script>
