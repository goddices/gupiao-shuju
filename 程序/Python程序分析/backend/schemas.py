"""Pydantic 请求和响应模型"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


# ---- 日K线行情 ----
class DailyQuoteOut(BaseModel):
    """日K线行情响应"""
    trade_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    amount: float

    model_config = {"from_attributes": True}


class QuoteListResponse(BaseModel):
    """日K线分页响应"""
    stock_code: str
    stock_name: Optional[str] = None
    total: int
    page: int
    page_size: int
    data: list[DailyQuoteOut]


# ---- 股票统计 ----
class StockStatsOut(BaseModel):
    """单只股票统计"""
    stock_code: str
    stock_name: Optional[str] = None
    total_records: int
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None
    latest_close: Optional[float] = None
    max_close: Optional[float] = None
    min_close: Optional[float] = None


# ---- 股票信息 ----
class StockInfoOut(BaseModel):
    """股票基本信息"""
    stock_code: str
    stock_name: str
    market: str

    model_config = {"from_attributes": True}


class StockInfoSyncOut(BaseModel):
    """股票列表同步结果"""
    status: str
    message: str
    total: int = 0


# ---- 股票概要 ----
class StockSummaryOut(BaseModel):
    """股票列表项"""
    stock_code: str
    stock_name: Optional[str] = None
    total_records: int
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None


# ---- 分红事件 ----
class DividendEventOut(BaseModel):
    """分红事件响应"""
    id: int
    stock_code: str
    event_name: Optional[str] = None
    record_date: Optional[date] = None
    ex_dividend_date: date
    payment_date: Optional[date] = None
    cash_per_10: Optional[float] = None
    bonus_per_10: Optional[float] = None
    conversion_per_10: Optional[float] = None

    model_config = {"from_attributes": True}


class DividendDetailOut(BaseModel):
    """分红明细响应（东方财富 stock_dividend_detail 表）"""
    id: int
    stock_code: str
    stock_name: Optional[str] = None
    report_date: Optional[date] = None
    record_date: Optional[date] = None
    ex_dividend_date: date
    notice_date: Optional[date] = None
    plan_notice_date: Optional[date] = None
    assign_progress: Optional[str] = None
    impl_plan_profile: Optional[str] = None
    cash_per_10: Optional[float] = None
    bonus_per_10: Optional[float] = None
    conversion_per_10: Optional[float] = None
    basic_eps: Optional[float] = None
    bvps: Optional[float] = None
    dividend_ratio: Optional[float] = None
    total_shares: Optional[float] = None
    ex_dividend_days: Optional[int] = None

    model_config = {"from_attributes": True}


class DividendSimulateRequest(BaseModel):
    """红利再投模拟请求"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_cash: float = 100000
    tax_rate: float = 0.0
    reinvest: bool = True


class DividendTargetRequest(BaseModel):
    """分红目标测算请求"""
    buy_date: date
    target_annual_dividend: float = 200000
    tax_rate: float = 0.0
    reinvest: bool = True
    reference: str = "last_year"  # last_year=去年全年 / trailing=最近12个月


class DipBuyRequest(BaseModel):
    """大跌买入 + 红利再投模拟请求"""
    strategy: str = "drawdown"  # drawdown=高点回撤一次性买入；daily_drop=当日大跌分批买入
    dip_pct: float = 20.0  # drawdown: 从高点回撤 %；daily_drop: 当日盘中跌幅 %
    buy_amount: float = 10.0  # drawdown 模式买入金额（万元）
    total_position: float = 100.0  # daily_drop 模式总仓位（万元）
    buy_ratio: float = 5.0  # daily_drop 模式每笔买入占总仓位比例（%）
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tax_rate: float = 0.0
    reinvest: bool = True


# ---- 数据拉取 ----
class FetchRequest(BaseModel):
    """触发数据拉取请求"""
    stock_codes: list[str]
    start_date: Optional[str] = "2006-01-01"


class FetchResponse(BaseModel):
    """拉取结果"""
    status: str
    message: str
    details: list[dict] = []


class StockFetchOut(BaseModel):
    """单只股票行情同步结果"""
    stock_code: str
    status: str  # ok / no_new_data / partial_error / error
    total_rows: int
    details: list[str] = []


# ---- 个股核心数据 ----
class StockCoreDataOut(BaseModel):
    """个股核心数据（PE、PB、ROE、市值、营收等）"""
    stock_code: str
    market: Optional[str] = None
    stock_name: Optional[str] = None
    total_market_cap: Optional[float] = None
    float_market_cap: Optional[float] = None
    eps: Optional[float] = None
    pe_dynamic: Optional[float] = None
    navps: Optional[float] = None
    pb: Optional[float] = None
    revenue: Optional[float] = None
    revenue_yoy: Optional[float] = None
    net_profit: Optional[float] = None
    profit_yoy: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    debt_ratio: Optional[float] = None
    total_shares: Optional[float] = None
    float_shares: Optional[float] = None
    retained_eps: Optional[float] = None
    list_date: Optional[str] = None
    change_pct: Optional[float] = None
    last_sync_time: Optional[datetime] = None
    data_source_type: Optional[str] = None


class StockCoreDataSyncOut(BaseModel):
    """核心数据同步结果"""
    status: str
    message: str
    data: Optional[StockCoreDataOut] = None


# ---- 星期涨跌分析 ----
class WeekdayStatItem(BaseModel):
    """单个星期几的统计数据"""
    weekday: str
    total_count: int
    up_count: int
    down_count: int
    flat_count: int
    up_pct: float
    down_pct: float
    mean_change: float
    median_change: Optional[float] = None
    std_change: Optional[float] = None
    max_gain: Optional[float] = None
    max_loss: Optional[float] = None

    model_config = {"from_attributes": True}


class DayPrediction(BaseModel):
    """单个交易日的涨跌预测"""
    date: str
    weekday: str
    up_probability: float
    down_probability: float
    mean_change: float
    sample_count: int


class WeekdayAnalysisResponse(BaseModel):
    """星期涨跌分析完整响应"""
    stock_code: str
    stock_name: Optional[str] = None
    total_trading_days: int
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    weekday_stats: list[WeekdayStatItem]
    predictions: list[DayPrediction]
    best_weekday: Optional[str] = None
    worst_weekday: Optional[str] = None


# ---- 节日涨跌分析 ----
class HolidayDayStat(BaseModel):
    """单日节日前后统计"""
    position: int  # -7~-1, 1~7
    position_label: str  # "节前7天", "节后1天" 等
    count: int
    up_count: int
    down_count: int
    up_probability: float
    down_probability: float
    mean_change: float
    median_change: float
    max_gain: float
    max_loss: float


class HolidayCumulativeStat(BaseModel):
    """累计涨跌统计"""
    count: int
    up_count: int
    down_count: int
    up_probability: float
    mean_change: float
    max_gain: float
    max_loss: float


class HolidayYearRecord(BaseModel):
    """逐年记录"""
    year: int
    date: str
    change_pct: float


class SingleHolidayAnalysis(BaseModel):
    """单个节日的完整分析"""
    name: str
    name_cn: str
    event_count: int  # 有多少年的数据
    year_range: str  # 如 "2008-2026"
    daily_stats: list[HolidayDayStat]  # 前后各7天共14条
    cumulative_before: Optional[HolidayCumulativeStat] = None
    cumulative_after: Optional[HolidayCumulativeStat] = None
    first_day_after: Optional[HolidayCumulativeStat] = None
    year_records: list[HolidayYearRecord] = []  # 节后首日逐年记录


class HolidayAnalysisResponse(BaseModel):
    """节日涨跌分析完整响应"""
    stock_code: str
    stock_name: Optional[str] = None
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    holidays: list[str]  # 节日名称列表
    analysis: list[SingleHolidayAnalysis]
    summary: list[dict]  # 综合对比摘要
