"""
DB 数据装配层 —— 红利/大跌/目标测算类分析共用的「四件套」

把散落在各中文脚本（现合并为 股票分析.py，实现见 analysis/tools/）与
backend 各 *_service.py 中逐字重复的取数代码收敛到本模块，
股票分析.py 与 backend 服务统一 import:

    from analysis.data_access import (
        load_quotes, load_forward_quotes, load_dividends, ensure_dividends,
    )

返回结构均为引擎可直接消费的 list[dict]（见 dividend_reinvest_engine 的入参约定）。
"""
import os
import sys

# 本模块依赖 backend 的 models/database（backend 为命名空间包，其内部使用
# `from models import ...` 扁平导入），因此自行确保根目录与 backend 目录可导入
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
for _p in (_ROOT, _BACKEND):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from models import StockDailyQuote, StockDividendDetail

# 只统计"实施分配"的分红
IMPL_PROGRESS = "实施分配"


def load_quotes(db, stock_code: str, start_date=None, end_date=None,
                with_low: bool = False) -> list:
    """读不复权日线（升序，可按区间过滤）

    :param with_low: 额外返回盘中最低价（大跌分批买入策略用）
    :return: [{"trade_date", "close_price"(, "low_price")}]
    """
    cols = [StockDailyQuote.trade_date, StockDailyQuote.close_price]
    if with_low:
        cols.append(StockDailyQuote.low_price)
    q = db.query(*cols).filter(StockDailyQuote.stock_code == stock_code)
    if start_date:
        q = q.filter(StockDailyQuote.trade_date >= start_date)
    if end_date:
        q = q.filter(StockDailyQuote.trade_date <= end_date)
    rows = q.order_by(StockDailyQuote.trade_date.asc()).all()
    if with_low:
        return [
            {"trade_date": r.trade_date, "low_price": float(r.low_price),
             "close_price": float(r.close_price)}
            for r in rows
        ]
    return [
        {"trade_date": r.trade_date, "close_price": float(r.close_price)}
        for r in rows
    ]


def load_forward_quotes(db, stock_code: str, n_expected: int = None) -> list:
    """读前复权收盘价（成本前复权口径 / 回撤检测用）

    前复权数据未覆盖全部交易日时返回 None，由调用方回退不复权口径。
    :param n_expected: 期望条数；None 表示须覆盖该股全部行情行数
    """
    rows = (
        db.query(StockDailyQuote.trade_date, StockDailyQuote.forward_close)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.asc())
        .all()
    )
    result = [
        {"trade_date": r.trade_date, "close_price": float(r.forward_close)}
        for r in rows if r.forward_close is not None
    ]
    if n_expected is None:
        n_expected = len(rows)
    return result if len(result) == n_expected and result else None


def load_dividends(db, stock_code: str) -> list:
    """读已实施的分红明细（升序由调用方/引擎处理）"""
    rows = (
        db.query(StockDividendDetail)
        .filter(
            StockDividendDetail.stock_code == stock_code,
            StockDividendDetail.assign_progress == IMPL_PROGRESS,
        )
        .all()
    )
    return [
        {
            "ex_dividend_date": r.ex_dividend_date,
            "report_date": r.report_date,
            "cash_per_10": float(r.cash_per_10) if r.cash_per_10 else 0.0,
            "bonus_per_10": float(r.bonus_per_10) if r.bonus_per_10 else 0.0,
            "conversion_per_10": float(r.conversion_per_10) if r.conversion_per_10 else 0.0,
        }
        for r in rows
    ]


def ensure_dividends(db, stock_code: str, force_sync: bool = False,
                     log=print) -> list:
    """确保分红数据存在：缺失或 force_sync 时从东方财富拉取入库

    :param log: 日志函数（脚本传 saver.log，服务端可不传）
    """
    exists = (
        db.query(StockDividendDetail.id)
        .filter(StockDividendDetail.stock_code == stock_code)
        .first()
    )
    if exists and not force_sync:
        return load_dividends(db, stock_code)

    log(f"正在从东方财富同步 {stock_code} 的分红明细...")
    # 延迟导入：避免纯读场景拉入 backend.services 及其全部依赖
    from backend.services import sync_stock_dividends
    result = sync_stock_dividends(db, stock_code)
    log(result["message"])
    if result["status"] != "ok":
        return []
    return load_dividends(db, stock_code)
