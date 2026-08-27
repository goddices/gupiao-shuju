"""大跌买入 + 红利再投服务 —— DB 加载数据 → 调根目录引擎 → 返回结构化结果

两种策略:
    drawdown    观察期内从（滚动）历史高点首次回撤 ≥ dip_pct% 时，一次性买入 buy_amount 元
                （前复权价格检测回撤，不复权价格成交与模拟）
    daily_drop  每个交易日若盘中最低价较前收盘跌幅 ≥ dip_pct%（当天大跌），按当日最低价
                买入一笔（金额 = 总仓位 × buy_ratio%），直至现金用完（分批抄底）
"""
import sys
import os

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StockDailyQuote, StockDividendDetail
from dividend_reinvest_engine import simulate_dip_buy, simulate_staged_dip_buy


def run_dip_buy(
    db: Session,
    stock_code: str,
    dip_pct: float,
    buy_amount: float,
    start_date=None,
    end_date=None,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    lot_size: int = 100,
    strategy: str = "drawdown",
    total_position: float = None,
    buy_ratio: float = 5.0,
) -> dict:
    """
    大跌买入 + 红利再投模拟

    :param db: 数据库会话
    :param stock_code: 股票代码
    :param dip_pct: drawdown=回撤买入幅度（%）；daily_drop=当日盘中跌幅阈值（%）
    :param buy_amount: drawdown 模式买入金额（元）
    :param start_date/end_date: 观察区间（可选）
    :param tax_rate: 分红税率（0~1）
    :param reinvest: True=红利再投；False=分红不投
    :param lot_size: 买入整数倍股数（A股=100）
    :param strategy: "drawdown" | "daily_drop"
    :param total_position: daily_drop 模式总仓位（元）
    :param buy_ratio: daily_drop 模式每笔买入占总仓位比例（%）
    :return: 引擎原始结果 dict
    """
    # 1. 分红明细（仅已实施分配）
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

    # 2. 当日跌幅分批策略：不复权日线（含最低价）
    if strategy == "daily_drop":
        quote_rows = (
            db.query(StockDailyQuote.trade_date, StockDailyQuote.low_price,
                     StockDailyQuote.close_price)
            .filter(StockDailyQuote.stock_code == stock_code)
            .order_by(StockDailyQuote.trade_date.asc())
            .all()
        )
        quotes = [
            {"trade_date": r.trade_date, "low_price": float(r.low_price),
             "close_price": float(r.close_price)}
            for r in quote_rows
        ]
        return simulate_staged_dip_buy(
            quotes=quotes,
            dividends=dividends,
            total_position=total_position if total_position else 1000000.0,
            buy_ratio=buy_ratio,
            dip_pct=dip_pct,
            start_date=start_date,
            end_date=end_date,
            tax_rate=tax_rate,
            reinvest=reinvest,
            lot_size=lot_size,
        )

    # 3. drawdown 策略：不复权收盘价 + 前复权收盘价（回撤检测）
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

    forward_rows = (
        db.query(StockDailyQuote.trade_date, StockDailyQuote.forward_close)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.asc())
        .all()
    )
    forward_quotes = [
        {"trade_date": r.trade_date, "close_price": float(r.forward_close)}
        for r in forward_rows if r.forward_close is not None
    ]
    if len(forward_quotes) != len(quotes):
        forward_quotes = None

    # 4. 调引擎
    return simulate_dip_buy(
        quotes=quotes,
        dividends=dividends,
        dip_pct=dip_pct,
        buy_amount=buy_amount,
        start_date=start_date,
        end_date=end_date,
        tax_rate=tax_rate,
        reinvest=reinvest,
        lot_size=lot_size,
        trigger_quotes=forward_quotes,
    )
