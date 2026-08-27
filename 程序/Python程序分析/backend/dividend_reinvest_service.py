"""红利再投模拟服务 —— DB 加载数据 → 调根目录引擎 → 返回结构化结果"""
import sys
import os
from typing import Optional

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StockDailyQuote, StockDividendDetail
from dividend_reinvest_engine import simulate_dividend_reinvest


def run_dividend_reinvest(
    db: Session,
    stock_code: str,
    start_date=None,
    end_date=None,
    initial_cash: float = 100000,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    lot_size: int = 100,
) -> dict:
    """
    红利再投模拟

    :param db: 数据库会话
    :param stock_code: 股票代码
    :param start_date: 起始日期（可选）
    :param end_date: 结束日期（可选）
    :param initial_cash: 初始资金
    :param tax_rate: 分红税率（0~1）
    :param reinvest: True=红利再投；False=分红不投
    :param lot_size: 买入整数倍股数（A股=100）
    :return: 引擎原始结果 dict（status/summary/dividend_events/equity_curve/warnings）
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
    return simulate_dividend_reinvest(
        quotes=quotes,
        dividends=dividends,
        initial_cash=initial_cash,
        start_date=start_date,
        end_date=end_date,
        tax_rate=tax_rate,
        reinvest=reinvest,
        lot_size=lot_size,
    )
