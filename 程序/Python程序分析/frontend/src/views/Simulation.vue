<template>
  <div>
    <h2 style="margin-bottom: 16px">📊 模拟交易</h2>

    <!-- ====== 账户概览 ====== -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="6">
        <a-card size="small" title="💰 现金">
          <span style="font-size: 22px; font-weight: bold; color: #1677ff">
            {{ fmt(account.cash) }}
          </span>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" title="📦 持仓市值">
          <span style="font-size: 22px; font-weight: bold">
            {{ fmt(account.total_market_value) }}
          </span>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" title="💎 总资产">
          <span style="font-size: 22px; font-weight: bold; color: #52c41a">
            {{ fmt(account.total_assets) }}
          </span>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" title="📈 总盈亏">
          <span
            :style="{ fontSize: '22px', fontWeight: 'bold', color: account.total_pl >= 0 ? '#cf1322' : '#3f8600' }"
          >
            {{ fmt(account.total_pl) }}
          </span>
          <span
            :style="{ fontSize: '13px', marginLeft: '6px', color: account.total_pl_pct >= 0 ? '#cf1322' : '#3f8600' }"
          >
            ({{ account.total_pl_pct >= 0 ? '+' : '' }}{{ account.total_pl_pct }}%)
          </span>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16" style="margin-bottom: 16px">
      <!-- ====== 费率配置 ====== -->
      <a-col :span="8">
        <a-card title="⚙️ 费率设置" size="small">
          <a-form layout="vertical" :model="feeForm" size="small">
            <a-form-item label="佣金费率">
              <a-input-group compact>
                <a-input-number
                  v-model:value="feeForm.commission_rate"
                  :step="0.0001"
                  :min="0"
                  style="width: 70%"
                  :formatter="v => v ? (v * 10000).toFixed(1) + '‱' : ''"
                  :parser="v => parseFloat(v) / 10000"
                />
                <a-button style="width: 30%" disabled>万分之{{ (feeForm.commission_rate * 10000).toFixed(1) }}</a-button>
              </a-input-group>
            </a-form-item>
            <a-form-item label="最低佣金（元）">
              <a-input-number v-model:value="feeForm.min_commission" :min="0" :step="1" style="width: 100%" />
            </a-form-item>
            <a-form-item label="印花税率（卖出）">
              <a-input-group compact>
                <a-input-number
                  v-model:value="feeForm.stamp_tax_rate"
                  :step="0.0001"
                  :min="0"
                  style="width: 70%"
                  :formatter="v => v ? (v * 10000).toFixed(1) + '‱' : ''"
                  :parser="v => parseFloat(v) / 10000"
                />
                <a-button style="width: 30%" disabled>万分之{{ (feeForm.stamp_tax_rate * 10000).toFixed(1) }}</a-button>
              </a-input-group>
            </a-form-item>
            <a-button type="primary" size="small" @click="saveFeeConfig" :loading="savingFee">保存费率</a-button>
          </a-form>
        </a-card>
      </a-col>

      <!-- ====== 买入 ====== -->
      <a-col :span="8">
        <a-card title="🟢 买入" size="small">
          <a-form layout="vertical" :model="buyForm" @finish="onBuy" size="small">
            <a-form-item label="股票代码">
              <a-input v-model:value="buyForm.stock_code" placeholder="如 600519" maxlength="6" />
            </a-form-item>
            <a-form-item label="股数（100的整数倍）">
              <a-input-number v-model:value="buyForm.shares" :min="100" :step="100" style="width: 100%" />
            </a-form-item>
            <a-form-item label="价格（留空=市价）">
              <a-input-number v-model:value="buyForm.price" :min="0.01" :step="0.01" style="width: 100%" placeholder="留空使用最新收盘价" />
            </a-form-item>
            <a-form-item>
              <span v-if="buyPreview" style="color: #666; font-size: 12px">
                预估: 成交 {{ fmt(buyPreview.amount) }} + 佣金 {{ fmt(buyPreview.commission) }} = {{ fmt(buyPreview.total) }}
              </span>
            </a-form-item>
            <a-button type="primary" html-type="submit" :loading="buying" block>确认买入</a-button>
          </a-form>
        </a-card>
      </a-col>

      <!-- ====== 卖出 ====== -->
      <a-col :span="8">
        <a-card title="🔴 卖出" size="small">
          <a-form layout="vertical" :model="sellForm" @finish="onSell" size="small">
            <a-form-item label="持仓股票">
              <a-select
                v-model:value="sellForm.stock_code"
                placeholder="选择持仓股票"
                :options="positionOptions"
                @change="onSellStockChange"
              />
            </a-form-item>
            <a-form-item label="股数">
              <a-input-number v-model:value="sellForm.shares" :min="100" :step="100" :max="sellMaxShares" style="width: 100%" />
            </a-form-item>
            <a-form-item label="价格（留空=市价）">
              <a-input-number v-model:value="sellForm.price" :min="0.01" :step="0.01" style="width: 100%" placeholder="留空使用最新收盘价" />
            </a-form-item>
            <a-form-item>
              <span v-if="sellPreview" style="color: #666; font-size: 12px">
                成交 {{ fmt(sellPreview.amount) }} - 佣金 {{ fmt(sellPreview.commission) }} - 印花税 {{ fmt(sellPreview.stamp_tax) }} = {{ fmt(sellPreview.net) }}
              </span>
            </a-form-item>
            <a-button type="primary" danger html-type="submit" :loading="selling" :disabled="!sellForm.stock_code" block>确认卖出</a-button>
          </a-form>
        </a-card>
      </a-col>
    </a-row>

    <!-- ====== 持仓明细 ====== -->
    <a-card title="📋 持仓明细" size="small" style="margin-bottom: 16px">
      <a-table
        :data-source="account.positions"
        :pagination="false"
        size="small"
        row-key="stock_code"
      >
        <a-table-column title="代码" data-index="stock_code" :width="90" />
        <a-table-column title="名称" data-index="stock_name" :width="100" />
        <a-table-column title="股数" data-index="shares" :width="80" />
        <a-table-column title="成本价" :width="90">
          <template #default="{ record }">{{ record.avg_cost.toFixed(2) }}</template>
        </a-table-column>
        <a-table-column title="现价" :width="90">
          <template #default="{ record }">{{ record.current_price ? record.current_price.toFixed(2) : '-' }}</template>
        </a-table-column>
        <a-table-column title="市值" :width="110">
          <template #default="{ record }">{{ record.market_value ? fmt(record.market_value) : '-' }}</template>
        </a-table-column>
        <a-table-column title="盈亏" :width="120">
          <template #default="{ record }">
            <span :style="{ color: record.pl >= 0 ? '#cf1322' : '#3f8600' }">
              {{ fmt(record.pl) }}
            </span>
          </template>
        </a-table-column>
        <a-table-column title="盈亏%" :width="80">
          <template #default="{ record }">
            <span :style="{ color: record.pl_pct >= 0 ? '#cf1322' : '#3f8600' }">
              {{ record.pl_pct >= 0 ? '+' : '' }}{{ record.pl_pct }}%
            </span>
          </template>
        </a-table-column>
      </a-table>
      <a-empty v-if="!account.positions || account.positions.length === 0" description="暂无持仓" style="margin: 24px 0" />
    </a-card>

    <!-- ====== 交易记录 & 重置 ====== -->
    <a-card size="small">
      <template #title>
        <a-space>
          <span>📜 交易记录</span>
          <a-button size="small" @click="loadTrades">刷新</a-button>
          <a-popconfirm
            title="确定要重置账户吗？所有持仓和交易记录将被清空。"
            @confirm="onReset"
            ok-text="确定"
            cancel-text="取消"
          >
            <a-button size="small" danger>重置账户</a-button>
          </a-popconfirm>
        </a-space>
      </template>
      <a-table
        :data-source="trades"
        :pagination="false"
        size="small"
        row-key="id"
      >
        <a-table-column title="时间" data-index="trade_date" :width="110" />
        <a-table-column title="类型" :width="60">
          <template #default="{ record }">
            <a-tag :color="record.trade_type === 'buy' ? 'green' : 'red'" size="small">
              {{ record.trade_type === 'buy' ? '买入' : '卖出' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="代码" data-index="stock_code" :width="80" />
        <a-table-column title="名称" data-index="stock_name" :width="80" />
        <a-table-column title="股数" data-index="shares" :width="70" />
        <a-table-column title="价格" :width="80">
          <template #default="{ record }">{{ record.price.toFixed(2) }}</template>
        </a-table-column>
        <a-table-column title="金额" :width="100">
          <template #default="{ record }">{{ fmt(record.amount) }}</template>
        </a-table-column>
        <a-table-column title="佣金" :width="70">
          <template #default="{ record }">{{ record.commission.toFixed(2) }}</template>
        </a-table-column>
        <a-table-column title="印花税" :width="70">
          <template #default="{ record }">{{ record.stamp_tax.toFixed(2) }}</template>
        </a-table-column>
        <a-table-column title="盈亏" :width="100">
          <template #default="{ record }">
            <span v-if="record.profit_loss != null" :style="{ color: record.profit_loss >= 0 ? '#cf1322' : '#3f8600' }">
              {{ fmt(record.profit_loss) }}
            </span>
            <span v-else>-</span>
          </template>
        </a-table-column>
      </a-table>
      <a-empty v-if="trades.length === 0" description="暂无交易" style="margin: 24px 0" />
    </a-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  getSimAccount, simBuy, simSell, getSimTrades,
  resetSimAccount, updateFeeConfig,
} from '../api'

// ====== 账户数据 ======
const account = ref({
  cash: 0, total_market_value: 0, total_assets: 0, total_cost: 0,
  total_pl: 0, total_pl_pct: 0,
  commission_rate: 0.0001, min_commission: 5, stamp_tax_rate: 0.0005,
  positions: [],
})
const trades = ref([])
const buying = ref(false)
const selling = ref(false)
const savingFee = ref(false)

function fmt(v) {
  if (v == null) return '-'
  return '¥' + Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadAccount() {
  try {
    const { data } = await getSimAccount()
    account.value = data
    // 同步费率到表单
    feeForm.commission_rate = data.commission_rate
    feeForm.min_commission = data.min_commission
    feeForm.stamp_tax_rate = data.stamp_tax_rate
  } catch (e) {
    message.error('加载账户失败')
  }
}

async function loadTrades() {
  try {
    const { data } = await getSimTrades(50)
    trades.value = data
  } catch (e) {
    message.error('加载交易记录失败')
  }
}

onMounted(() => {
  loadAccount()
  loadTrades()
})

// ====== 费率 ======
const feeForm = reactive({
  commission_rate: 0.0001,
  min_commission: 5,
  stamp_tax_rate: 0.0005,
})

async function saveFeeConfig() {
  savingFee.value = true
  try {
    await updateFeeConfig({
      commission_rate: feeForm.commission_rate,
      min_commission: feeForm.min_commission,
      stamp_tax_rate: feeForm.stamp_tax_rate,
    })
    message.success('费率已保存')
  } catch (e) {
    message.error('保存失败')
  } finally {
    savingFee.value = false
  }
}

// ====== 买入 ======
const buyForm = reactive({ stock_code: '', shares: 100, price: null })
const buyPreview = computed(() => {
  if (!buyForm.stock_code || !buyForm.shares) return null
  const price = buyForm.price || 0
  const amount = price * buyForm.shares
  const comm = Math.max(amount * feeForm.commission_rate, feeForm.min_commission)
  return { amount, commission: comm, total: amount + comm }
})

async function onBuy() {
  if (!buyForm.stock_code) { message.warning('请输入股票代码'); return }
  buying.value = true
  try {
    const { data } = await simBuy({
      stock_code: buyForm.stock_code,
      shares: buyForm.shares,
      price: buyForm.price || undefined,
    })
    if (data.status === 'ok') {
      message.success(data.message)
      buyForm.stock_code = ''
      buyForm.shares = 100
      buyForm.price = null
      loadAccount()
      loadTrades()
    } else {
      message.error(data.message)
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '买入失败')
  } finally {
    buying.value = false
  }
}

// ====== 卖出 ======
const sellForm = reactive({ stock_code: null, shares: 100, price: null })
const sellMaxShares = ref(0)

const positionOptions = computed(() =>
  account.value.positions.map(p => ({
    value: p.stock_code,
    label: `${p.stock_code} ${p.stock_name} (${p.shares}股)`,
  }))
)

function onSellStockChange(code) {
  const pos = account.value.positions.find(p => p.stock_code === code)
  if (pos) {
    sellMaxShares.value = pos.shares
    sellForm.shares = Math.min(sellForm.shares, pos.shares)
  }
}

const sellPreview = computed(() => {
  if (!sellForm.stock_code || !sellForm.shares) return null
  const price = sellForm.price || 0
  const amount = price * sellForm.shares
  const comm = Math.max(amount * feeForm.commission_rate, feeForm.min_commission)
  const tax = amount * feeForm.stamp_tax_rate
  return { amount, commission: comm, stamp_tax: tax, net: amount - comm - tax }
})

async function onSell() {
  if (!sellForm.stock_code) { message.warning('请选择持仓股票'); return }
  selling.value = true
  try {
    const { data } = await simSell({
      stock_code: sellForm.stock_code,
      shares: sellForm.shares,
      price: sellForm.price || undefined,
    })
    if (data.status === 'ok') {
      message.success(data.message + (data.profit_loss != null ? ` | 盈亏: ¥${data.profit_loss.toFixed(2)} (${data.profit_loss_pct}%)` : ''))
      sellForm.stock_code = null
      sellForm.shares = 100
      sellForm.price = null
      loadAccount()
      loadTrades()
    } else {
      message.error(data.message)
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '卖出失败')
  } finally {
    selling.value = false
  }
}

// ====== 重置 ======
async function onReset() {
  try {
    await resetSimAccount(100000)
    message.success('账户已重置')
    loadAccount()
    loadTrades()
  } catch (e) {
    message.error('重置失败')
  }
}
</script>
