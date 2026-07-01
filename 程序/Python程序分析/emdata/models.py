"""
数据模型：K线数据、行情数据、核心数据
"""
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass


class StockQuoteLine:
    """股票行情K线数据"""

    def __init__(
        self,
        trade_date: datetime,
        open_price: float,
        close_price: float,
        high_price: float,
        low_price: float,
        trade_volume: float,
        trade_amount: float,
    ):
        self.trade_date = trade_date
        self.open = open_price
        self.close = close_price
        self.high = high_price
        self.low = low_price
        self.volume = trade_volume
        self.amount = trade_amount

    def __repr__(self):
        return (
            f"StockQuoteLine(date={self.trade_date}, open={self.open}, close={self.close}, "
            f"high={self.high}, low={self.low}, volume={self.volume}, amount={self.amount})"
        )


class StockQuote:
    """股票行情数据"""

    def __init__(
        self,
        stock_name: str,
        quote_lines: List[StockQuoteLine],
        period_type,
    ):
        self.stock_name = stock_name
        self.quote_lines = quote_lines
        self.period_type = period_type

    def __repr__(self):
        return (
            f"StockQuote(stock_name={self.stock_name}, period_type={self.period_type}, "
            f"lines_count={len(self.quote_lines)})"
        )


class QuoteMappers:
    """行情数据映射器"""

    @staticmethod
    def get_adjust_price_parameter_value(adjust_type) -> int:
        """获取复权类型对应的参数值"""
        return adjust_type

    @staticmethod
    def get_period_type_param_value(period_type) -> int:
        """获取周期类型对应的参数值"""
        return period_type


@dataclass
class StockInfo:
    """个股核心数据"""

    stock_code: str
    market: str
    stock_name: Optional[str] = None        # f58: 股票名称
    total_market_cap: Optional[float] = None  # f57: 总市值（亿元）
    float_market_cap: Optional[float] = None  # f107: 流通市值（亿元）
    eps: Optional[float] = None             # f162: 每股收益
    pe_dynamic: Optional[float] = None      # f183: PE(动)
    navps: Optional[float] = None           # f59: 每股净资产
    pb: Optional[float] = None              # f62: 市净率
    revenue: Optional[float] = None         # f184: 总营收（亿元）
    revenue_yoy: Optional[float] = None     # f85: 营收同比（%）
    net_profit: Optional[float] = None      # f185: 净利润（亿元）
    profit_yoy: Optional[float] = None      # f117: 净利润同比（%）
    gross_margin: Optional[float] = None    # f186: 毛利率（%）
    net_margin: Optional[float] = None      # f187: 净利率（%）
    roe: Optional[float] = None             # f173: ROE（%）
    debt_ratio: Optional[float] = None      # f188: 资产负债率（%）
    total_shares: Optional[float] = None    # f92: 总股本（亿股）
    float_shares: Optional[float] = None    # f105: 流通股本（亿股）
    retained_eps: Optional[float] = None    # f116: 每股未分配利润
    list_date: Optional[str] = None         # f84: 上市日期
    change_pct: Optional[float] = None      # f55: 涨跌幅（%）
