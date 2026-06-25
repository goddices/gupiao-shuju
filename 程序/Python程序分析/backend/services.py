"""股票行情数据查询服务"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from models import StockDailyQuote, StockDividendEvent


def get_available_stocks(db: Session) -> list[dict]:
    """获取数据库中有数据的所有股票概要"""
    rows = (
        db.query(
            StockDailyQuote.stock_code,
            func.count(StockDailyQuote.id).label("total_records"),
            func.min(StockDailyQuote.trade_date).label("earliest_date"),
            func.max(StockDailyQuote.trade_date).label("latest_date"),
        )
        .group_by(StockDailyQuote.stock_code)
        .order_by(StockDailyQuote.stock_code)
        .all()
    )
    return [
        {
            "stock_code": r.stock_code,
            "total_records": r.total_records,
            "earliest_date": r.earliest_date,
            "latest_date": r.latest_date,
        }
        for r in rows
    ]


def get_stock_quotes(
    db: Session,
    stock_code: str,
    adjust_type: str = "none",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    """分页获取单只股票的日K线数据"""
    query = db.query(StockDailyQuote).filter(
        StockDailyQuote.stock_code == stock_code
    )

    if start_date:
        query = query.filter(StockDailyQuote.trade_date >= start_date)
    if end_date:
        query = query.filter(StockDailyQuote.trade_date <= end_date)

    total = query.count()

    # 按日期倒序
    query = query.order_by(StockDailyQuote.trade_date.desc())
    offset = (page - 1) * page_size
    rows = query.offset(offset).limit(page_size).all()

    # 根据复权类型选择价格字段
    if adjust_type == "forward":
        data = [_to_forward_quote(r) for r in rows]
    elif adjust_type == "backward":
        data = [_to_backward_quote(r) for r in rows]
    else:
        data = [_to_raw_quote(r) for r in rows]

    return {
        "stock_code": stock_code,
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": data,
    }


def get_stock_stats(db: Session, stock_code: str) -> dict:
    """获取单只股票的统计信息"""
    stats = (
        db.query(
            func.count(StockDailyQuote.id).label("total_records"),
            func.min(StockDailyQuote.trade_date).label("earliest_date"),
            func.max(StockDailyQuote.trade_date).label("latest_date"),
            func.max(StockDailyQuote.close_price).label("max_close"),
            func.min(StockDailyQuote.close_price).label("min_close"),
        )
        .filter(StockDailyQuote.stock_code == stock_code)
        .first()
    )

    if not stats or not stats.total_records:
        return {
            "stock_code": stock_code,
            "total_records": 0,
            "earliest_date": None,
            "latest_date": None,
            "latest_close": None,
            "max_close": None,
            "min_close": None,
        }

    # 获取最新收盘价
    latest = (
        db.query(StockDailyQuote)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.desc())
        .first()
    )

    return {
        "stock_code": stock_code,
        "total_records": stats.total_records,
        "earliest_date": stats.earliest_date,
        "latest_date": stats.latest_date,
        "latest_close": float(latest.close_price) if latest else None,
        "max_close": float(stats.max_close) if stats.max_close else None,
        "min_close": float(stats.min_close) if stats.min_close else None,
    }


def get_stock_dividends(
    db: Session,
    stock_code: str,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """分页获取分红事件"""
    query = db.query(StockDividendEvent).filter(
        StockDividendEvent.stock_code == stock_code
    )
    total = query.count()

    rows = (
        query
        .order_by(StockDividendEvent.ex_dividend_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "stock_code": stock_code,
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [_to_dividend_dict(r) for r in rows],
    }


def get_latest_trade_date(db: Session, stock_code: str) -> Optional[date]:
    """获取某只股票的最新交易日期"""
    row = (
        db.query(StockDailyQuote.trade_date)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.desc())
        .first()
    )
    return row.trade_date if row else None


# ---- 内部辅助函数 ----
def _to_raw_quote(r: StockDailyQuote) -> dict:
    return {
        "trade_date": r.trade_date,
        "open_price": float(r.open_price),
        "high_price": float(r.high_price),
        "low_price": float(r.low_price),
        "close_price": float(r.close_price),
        "volume": r.volume,
        "amount": float(r.amount),
    }


def _to_forward_quote(r: StockDailyQuote) -> dict:
    return {
        "trade_date": r.trade_date,
        "open_price": float(r.forward_open) if r.forward_open else float(r.open_price),
        "high_price": float(r.forward_high) if r.forward_high else float(r.high_price),
        "low_price": float(r.forward_low) if r.forward_low else float(r.low_price),
        "close_price": float(r.forward_close) if r.forward_close else float(r.close_price),
        "volume": r.volume,
        "amount": float(r.amount),
    }


def _to_backward_quote(r: StockDailyQuote) -> dict:
    return {
        "trade_date": r.trade_date,
        "open_price": float(r.backward_open) if r.backward_open else float(r.open_price),
        "high_price": float(r.backward_high) if r.backward_high else float(r.high_price),
        "low_price": float(r.backward_low) if r.backward_low else float(r.low_price),
        "close_price": float(r.backward_close) if r.backward_close else float(r.close_price),
        "volume": r.volume,
        "amount": float(r.amount),
    }


def _to_dividend_dict(r: StockDividendEvent) -> dict:
    return {
        "id": r.id,
        "stock_code": r.stock_code,
        "event_name": r.event_name,
        "record_date": r.record_date,
        "ex_dividend_date": r.ex_dividend_date,
        "payment_date": r.payment_date,
        "cash_per_10": float(r.cash_per_10) if r.cash_per_10 else None,
        "bonus_per_10": float(r.bonus_per_10) if r.bonus_per_10 else None,
        "conversion_per_10": float(r.conversion_per_10) if r.conversion_per_10 else None,
    }
