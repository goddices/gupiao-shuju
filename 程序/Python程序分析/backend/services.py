"""股票行情数据查询服务"""
import sys
import os
import asyncio
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StockDailyQuote, StockDividendEvent, StockInfo
from eastmoney_quote_reader import EastmoneyStockListReader


def get_available_stocks(db: Session) -> list[dict]:
    """获取数据库中有数据的所有股票概要（含名称）"""
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
    # 批量查询股票名称
    codes = [r.stock_code for r in rows]
    name_map = {}
    if codes:
        info_rows = (
            db.query(StockInfo.stock_code, StockInfo.stock_name)
            .filter(StockInfo.stock_code.in_(codes))
            .all()
        )
        name_map = {r.stock_code: r.stock_name for r in info_rows}

    return [
        {
            "stock_code": r.stock_code,
            "stock_name": name_map.get(r.stock_code),
            "total_records": r.total_records,
            "earliest_date": r.earliest_date,
            "latest_date": r.latest_date,
        }
        for r in rows
    ]


def get_all_stock_infos(db: Session, q: str = None) -> list[dict]:
    """获取 stock_info 中全部股票，支持按代码或名称搜索"""
    query = db.query(StockInfo.stock_code, StockInfo.stock_name, StockInfo.market)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            StockInfo.stock_code.like(pattern) |
            StockInfo.stock_name.like(pattern)
        )
    rows = query.order_by(StockInfo.stock_code).limit(100).all()
    return [
        {"stock_code": r.stock_code, "stock_name": r.stock_name, "market": r.market}
        for r in rows
    ]


def get_stock_name(db: Session, stock_code: str) -> Optional[str]:
    """获取单只股票的名称"""
    row = (
        db.query(StockInfo.stock_name)
        .filter(StockInfo.stock_code == stock_code)
        .first()
    )
    return row.stock_name if row else None


def sync_stock_list(db: Session) -> dict:
    """
    从东方财富同步全市场股票代码和名称到 stock_info 表。
    返回 {"status": str, "message": str, "total": int}
    """
    # 全A股过滤条件: 沪市主板+科创板 + 深市主板+创业板
    fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"

    async def _sync():
        reader = EastmoneyStockListReader()
        stocks = await reader.fetch_all_stocks(fs, size=100, max_pages=200)
        return stocks

    try:
        stocks = asyncio.run(_sync())
    except Exception as e:
        return {"status": "error", "message": f"同步失败: {str(e)}", "total": 0}

    if not stocks:
        return {"status": "ok", "message": "未获取到股票数据", "total": 0}

    new_count = 0
    update_count = 0
    for s in stocks:
        market = "SH" if s["market"] == 1 else "SZ"
        existing = (
            db.query(StockInfo)
            .filter(StockInfo.stock_code == s["code"])
            .first()
        )
        if existing:
            if existing.stock_name != s["name"]:
                existing.stock_name = s["name"]
                update_count += 1
        else:
            db.add(StockInfo(
                stock_code=s["code"],
                stock_name=s["name"],
                market=market,
            ))
            new_count += 1

    db.commit()
    return {
        "status": "ok",
        "message": f"同步完成: 新增 {new_count} 只, 更新 {update_count} 只",
        "total": new_count + update_count,
    }


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
        "stock_name": get_stock_name(db, stock_code),
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
        "stock_name": get_stock_name(db, stock_code),
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
