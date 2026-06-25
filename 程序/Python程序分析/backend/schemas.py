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
    total: int
    page: int
    page_size: int
    data: list[DailyQuoteOut]


# ---- 股票统计 ----
class StockStatsOut(BaseModel):
    """单只股票统计"""
    stock_code: str
    total_records: int
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None
    latest_close: Optional[float] = None
    max_close: Optional[float] = None
    min_close: Optional[float] = None


# ---- 股票概要 ----
class StockSummaryOut(BaseModel):
    """股票列表项"""
    stock_code: str
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
