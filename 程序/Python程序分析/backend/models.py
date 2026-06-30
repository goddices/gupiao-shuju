"""SQLAlchemy ORM 模型"""
from sqlalchemy import (
    Column, Integer, String, Date, BigInteger, Numeric, TIMESTAMP, UniqueConstraint
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
