"""分红目标测算服务 —— DB 加载数据 → 调根目录引擎 → 返回结构化结果"""
import sys
import os

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StockDailyQuote, StockDividendDetail
from dividend_reinvest_engine import plan_dividend_target


def plan_target(
    db: Session,
    stock_code: str,
    buy_date,
    target_annual_dividend: float,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    reference: str = "last_year",
    lot_size: int = 100,
) -> dict:
    """
    分红目标测算：目标每年分红到账 X 元，需要在买入日投入多少钱？

    :param db: 数据库会话
    :param stock_code: 股票代码
    :param buy_date: 买入日期（非交易日顺延到下一交易日）
    :param target_annual_dividend: 目标每年分红到账金额（元）
    :param tax_rate: 分红税率（0~1）
    :param reinvest: True=红利再投；False=分红不投
    :param reference: 每股年分红基准 — "last_year"=去年全年 / "trailing"=最近12个月
    :param lot_size: 买入整数倍股数（A股=100）
    :return: 引擎原始结果 dict（status/summary）
    """
    # 1. 不复权收盘价（升序）
    quote_rows = (
        db.query(StockDailyQuote.trade_date, StockDailyQuote.close_price)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.asc())
        .all()
    )
    quotes = [
        {"trade_date": r.trade_date, "close_price": float(r.close_price)}
        for r in quote_rows
    ]

    # 2. 分红明细（仅已实施分配）
    div_rows = (
        db.query(StockDividendDetail)
        .filter(
            StockDividendDetail.stock_code == stock_code,
            StockDividendDetail.assign_progress == "实施分配",
        )
        .all()
    )
    dividends = [
        {
            "ex_dividend_date": r.ex_dividend_date,
            "report_date": r.report_date,
            "cash_per_10": float(r.cash_per_10) if r.cash_per_10 else 0.0,
            "bonus_per_10": float(r.bonus_per_10) if r.bonus_per_10 else 0.0,
            "conversion_per_10": float(r.conversion_per_10) if r.conversion_per_10 else 0.0,
        }
        for r in div_rows
    ]

    # 3. 调引擎
    return plan_dividend_target(
        quotes=quotes,
        dividends=dividends,
        buy_date=buy_date,
        target_annual_dividend=target_annual_dividend,
        tax_rate=tax_rate,
        reinvest=reinvest,
        reference=reference,
        lot_size=lot_size,
    )
