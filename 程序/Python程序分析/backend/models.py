"""SQLAlchemy ORM 模型"""
from sqlalchemy import (
    Column, Integer, String, Date, BigInteger, Numeric, TIMESTAMP, DateTime, UniqueConstraint
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StockDailyQuote(Base):
    __tablename__ = "stock_daily_quote"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uq_stock_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open_price = Column(Numeric(12, 4), nullable=False)
    high_price = Column(Numeric(12, 4), nullable=False)
    low_price = Column(Numeric(12, 4), nullable=False)
    close_price = Column(Numeric(12, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)
    amount = Column(Numeric(20, 4), nullable=False)
    created_at = Column(TIMESTAMP, server_default=None)

    # 复权价格（由 get_adjust_price.py 填充）
    forward_open = Column(Numeric(12, 4))
    forward_high = Column(Numeric(12, 4))
    forward_low = Column(Numeric(12, 4))
    forward_close = Column(Numeric(12, 4))
    backward_open = Column(Numeric(12, 4))
    backward_high = Column(Numeric(12, 4))
    backward_low = Column(Numeric(12, 4))
    backward_close = Column(Numeric(12, 4))


class StockInfo(Base):
    """股票基本信息（代码、名称、市场）"""
    __tablename__ = "stock_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, unique=True, index=True)
    stock_name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False, comment="市场: SH=上海, SZ=深圳")
    created_at = Column(TIMESTAMP, server_default=None)
    updated_at = Column(TIMESTAMP, server_default=None)


class StockDividendEvent(Base):
    __tablename__ = "stock_dividend_events"
    __table_args__ = (
        UniqueConstraint("stock_code", "ex_dividend_date", name="uq_stock_exdate"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)
    event_name = Column(String(50))
    record_date = Column(Date)
    ex_dividend_date = Column(Date, nullable=False)
    payment_date = Column(Date)
    cash_per_10 = Column(Numeric(12, 6), default=0)
    bonus_per_10 = Column(Numeric(12, 6), default=0)
    conversion_per_10 = Column(Numeric(12, 6), default=0)
    created_at = Column(TIMESTAMP, server_default=None)


class StockCoreData(Base):
    """个股核心数据（PE、PB、ROE、市值、营收等）"""
    __tablename__ = "stock_core_data"
    __table_args__ = (
        UniqueConstraint("stock_code", name="uq_stock_core_code"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, unique=True, index=True)
    stock_name = Column(String(100))
    market = Column(String(10))
    total_market_cap = Column(Numeric(24, 4))   # 总市值（亿元）
    float_market_cap = Column(Numeric(24, 4))   # 流通市值（亿元）
    eps = Column(Numeric(24, 4))                # 每股收益
    pe_dynamic = Column(Numeric(24, 4))         # PE(动)
    navps = Column(Numeric(24, 4))              # 每股净资产
    pb = Column(Numeric(24, 4))                 # 市净率
    revenue = Column(Numeric(24, 4))            # 总营收（亿元）
    revenue_yoy = Column(Numeric(24, 4))        # 营收同比（%）
    net_profit = Column(Numeric(24, 4))         # 净利润（亿元）
    profit_yoy = Column(Numeric(24, 4))         # 净利润同比（%）
    gross_margin = Column(Numeric(24, 4))       # 毛利率（%）
    net_margin = Column(Numeric(24, 4))         # 净利率（%）
    roe = Column(Numeric(24, 4))                # ROE（%）
    debt_ratio = Column(Numeric(24, 4))         # 资产负债率（%）
    total_shares = Column(Numeric(24, 4))       # 总股本（亿股）
    float_shares = Column(Numeric(24, 4))       # 流通股本（亿股）
    retained_eps = Column(Numeric(24, 4))       # 每股未分配利润
    list_date = Column(String(20))              # 上市日期
    change_pct = Column(Numeric(24, 4))         # 涨跌幅（%）
    last_sync_time = Column(DateTime, nullable=True, comment="最近一次行情同步时间")
    data_source_type = Column(String(20), nullable=True, comment="同步时使用的数据源: eastmoney / akshare")
    updated_at = Column(TIMESTAMP, server_default=None)


class StockCookie(Base):
    """已验证可用的 Cookie"""
    __tablename__ = "stock_cookies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cookie = Column(String(4096), nullable=False)
    fail_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=None)


# ============================================================
#  模拟持仓
# ============================================================

class SimulationAccount(Base):
    """模拟交易账户"""
    __tablename__ = "simulation_account"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, default="默认账户")
    initial_cash = Column(Numeric(18, 2), nullable=False, default=100000)
    cash = Column(Numeric(18, 2), nullable=False, default=100000)
    commission_rate = Column(Numeric(8, 6), nullable=False, default=0.0001, comment="佣金费率（如 0.0001=万分之一）")
    min_commission = Column(Numeric(10, 2), nullable=False, default=5.00, comment="最低佣金（元）")
    stamp_tax_rate = Column(Numeric(8, 6), nullable=False, default=0.0005, comment="印花税率（卖出时收取，0.0005=万分之五）")
    created_at = Column(TIMESTAMP, server_default=None)


class SimulationPosition(Base):
    """模拟持仓"""
    __tablename__ = "simulation_position"
    __table_args__ = (
        UniqueConstraint("account_id", "stock_code", name="uq_position_account_stock"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(100))
    shares = Column(Integer, nullable=False, default=0, comment="持仓股数")
    avg_cost = Column(Numeric(12, 4), nullable=False, default=0, comment="平均成本价")
    total_cost = Column(Numeric(18, 2), nullable=False, default=0, comment="总成本（含买入费用）")
    current_price = Column(Numeric(12, 4), nullable=True, comment="最新市价")
    updated_at = Column(TIMESTAMP, server_default=None)


class SimulationTrade(Base):
    """模拟交易记录"""
    __tablename__ = "simulation_trade"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(100))
    trade_type = Column(String(10), nullable=False, comment="buy / sell")
    shares = Column(Integer, nullable=False, default=0)
    price = Column(Numeric(12, 4), nullable=False, comment="成交价")
    amount = Column(Numeric(18, 2), nullable=False, comment="成交金额")
    commission = Column(Numeric(12, 2), nullable=False, default=0, comment="佣金")
    stamp_tax = Column(Numeric(12, 2), nullable=False, default=0, comment="印花税")
    profit_loss = Column(Numeric(18, 2), nullable=True, comment="卖出时的盈亏")
    profit_loss_pct = Column(Numeric(12, 4), nullable=True, comment="卖出时的盈亏比例(%)")
    trade_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, server_default=None)


class StockWeekdayStats(Base):
    """个股按星期几统计的涨跌分布"""
    __tablename__ = "stock_weekday_stats"
    __table_args__ = (
        UniqueConstraint("stock_code", "weekday", name="uq_stock_weekday"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)
    weekday = Column(String(10), nullable=False, comment="星期几: 星期一~星期五")
    total_count = Column(Integer, nullable=False, default=0, comment="该星期几的交易日总数")
    up_count = Column(Integer, nullable=False, default=0, comment="上涨天数")
    down_count = Column(Integer, nullable=False, default=0, comment="下跌天数")
    flat_count = Column(Integer, nullable=False, default=0, comment="平盘天数")
    up_pct = Column(Numeric(8, 4), nullable=False, default=0, comment="上涨概率(%)")
    down_pct = Column(Numeric(8, 4), nullable=False, default=0, comment="下跌概率(%)")
    mean_change = Column(Numeric(12, 6), nullable=False, default=0, comment="平均涨跌幅(%)")
    median_change = Column(Numeric(12, 6), nullable=True, comment="中位数涨跌幅(%)")
    std_change = Column(Numeric(12, 6), nullable=True, comment="涨跌幅标准差")
    max_gain = Column(Numeric(12, 6), nullable=True, comment="最大涨幅(%)")
    max_loss = Column(Numeric(12, 6), nullable=True, comment="最大跌幅(%)")
    updated_at = Column(TIMESTAMP, server_default=None)
