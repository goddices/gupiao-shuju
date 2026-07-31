"""股票行情数据查询服务"""
import sys
import os
import json
import asyncio
import numpy as np
from datetime import date, datetime, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy import func, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StockDailyQuote, StockDividendEvent, StockInfo, StockCoreData, StockCookie, StockWeekdayStats
from emdata import get_stock_list_reader, SEED_COOKIE
from config.datasource import is_eastmoney
from database import SessionLocal

# 删除失败的 Cookie 阈值
COOKIE_MAX_FAILS = 5


def get_fallback_cookies(db) -> list[str]:
    """从 DB 获取备用 Cookie 列表（按失败次数升序）"""
    rows = db.query(StockCookie).filter(StockCookie.fail_count < COOKIE_MAX_FAILS).order_by(StockCookie.fail_count).limit(10).all()
    cookies = [r.cookie for r in rows]
    if not cookies:
        cookies = [SEED_COOKIE]
    return cookies


def save_working_cookie(db, cookie: str):
    """保存验证成功的 Cookie（幂等）"""
    existing = db.query(StockCookie).filter(StockCookie.cookie == cookie).first()
    if existing:
        existing.fail_count = 0
    else:
        db.add(StockCookie(cookie=cookie, fail_count=0))
    db.commit()


def mark_cookie_failed(db, cookie: str):
    """标记 Cookie 失败，达阈值则删除"""
    row = db.query(StockCookie).filter(StockCookie.cookie == cookie).first()
    if row:
        row.fail_count += 1
        if row.fail_count >= COOKIE_MAX_FAILS:
            db.delete(row)
        db.commit()


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
        reader = get_stock_list_reader(db_cookies=get_fallback_cookies(db))
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


def _stock_info_to_dict(info) -> dict:
    """StockInfo dataclass → dict"""
    return {
        "stock_code": info.stock_code,
        "market": info.market,
        "stock_name": info.stock_name,
        "total_market_cap": info.total_market_cap,
        "float_market_cap": info.float_market_cap,
        "eps": info.eps,
        "pe_dynamic": info.pe_dynamic,
        "navps": info.navps,
        "pb": info.pb,
        "revenue": info.revenue,
        "revenue_yoy": info.revenue_yoy,
        "net_profit": info.net_profit,
        "profit_yoy": info.profit_yoy,
        "gross_margin": info.gross_margin,
        "net_margin": info.net_margin,
        "roe": info.roe,
        "debt_ratio": info.debt_ratio,
        "total_shares": info.total_shares,
        "float_shares": info.float_shares,
        "retained_eps": info.retained_eps,
        "list_date": str(info.list_date) if info.list_date else None,
        "change_pct": info.change_pct,
    }


def get_stock_core_data(db: Session, stock_code: str) -> Optional[dict]:
    """从数据库获取个股核心数据"""
    row = db.query(StockCoreData).filter(StockCoreData.stock_code == stock_code).first()
    if not row:
        return None

    def _f(val):
        return float(val) if val else None

    return {
        "stock_code": row.stock_code,
        "market": row.market,
        "stock_name": row.stock_name,
        "total_market_cap": _f(row.total_market_cap),
        "float_market_cap": _f(row.float_market_cap),
        "eps": _f(row.eps),
        "pe_dynamic": _f(row.pe_dynamic),
        "navps": _f(row.navps),
        "pb": _f(row.pb),
        "revenue": _f(row.revenue),
        "revenue_yoy": _f(row.revenue_yoy),
        "net_profit": _f(row.net_profit),
        "profit_yoy": _f(row.profit_yoy),
        "gross_margin": _f(row.gross_margin),
        "net_margin": _f(row.net_margin),
        "roe": _f(row.roe),
        "debt_ratio": _f(row.debt_ratio),
        "total_shares": _f(row.total_shares),
        "float_shares": _f(row.float_shares),
        "retained_eps": _f(row.retained_eps),
        "list_date": row.list_date,
        "change_pct": _f(row.change_pct),
        "last_sync_time": row.last_sync_time,
        "data_source_type": row.data_source_type,
    }


def sync_stock_core_data(db: Session, stock_code: str) -> dict:
    """
    获取个股核心数据并保存到数据库（支持多数据源）
    :return: {"status": str, "message": str, "data": dict|None}
    """
    from emdata import get_core_data_reader, Market

    market = Market.SHANGHAI if stock_code.startswith("6") else Market.SHENGZHEN

    # 仅在东方财富数据源下获取 cookie 兜底列表
    fallback_cookies = get_fallback_cookies(db) if is_eastmoney() else None

    reader = get_core_data_reader(db_cookies=get_fallback_cookies(db))
    async def _fetch():
        return await reader.fetch_stock_info_async(market, stock_code, fallback_cookies)

    try:
        info = asyncio.run(_fetch())
    except Exception as e:
        return {"status": "error", "message": f"网络请求失败: {str(e)}", "data": None}

    if info is None:
        return {"status": "error", "message": "获取核心数据为空", "data": None}

    # 保存成功的 Cookie 到 DB（仅东方财富数据源有此机制）
    if is_eastmoney() and hasattr(reader, 'last_used_cookie') and reader.last_used_cookie:
        save_working_cookie(db, reader.last_used_cookie)

    data = _stock_info_to_dict(info)

    # 写入或更新数据库
    existing = db.query(StockCoreData).filter(StockCoreData.stock_code == stock_code).first()
    if existing:
        for key, val in data.items():
            if key != "stock_code":
                setattr(existing, key, val)
    else:
        db.add(StockCoreData(**data))

    db.commit()

    return {"status": "ok", "message": "核心数据同步成功", "data": data}


def get_latest_trade_date(db: Session, stock_code: str) -> Optional[date]:
    """获取某只股票的最新交易日期"""
    row = (
        db.query(StockDailyQuote.trade_date)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.desc())
        .first()
    )
    return row.trade_date if row else None


# ---- 行情自动同步（本地优先 + 新鲜度检查） ----
import threading

# 正在同步的股票集合,避免同一股票并发重复同步
_syncing_stocks = set()
_syncing_stocks_lock = threading.Lock()


def _try_start_sync(stock_code: str) -> bool:
    """登记股票为同步中,返回是否可启动(防止并发重复同步)"""
    with _syncing_stocks_lock:
        if stock_code in _syncing_stocks:
            return False
        _syncing_stocks.add(stock_code)
    return True


def _sync_quote_in_background(stock_code: str) -> Optional[threading.Thread]:
    """在后台线程中同步股票行情（使用独立数据库会话）"""
    if not _try_start_sync(stock_code):
        return None

    def _sync():
        from data_fetcher import fetch_stock_data_full
        try:
            sdb = SessionLocal()
            try:
                fetch_stock_data_full(sdb, stock_code)
                sdb.commit()
                print(f"[auto-sync] {stock_code} 后台同步完成")
            except Exception as e:
                sdb.rollback()
                print(f"[auto-sync] {stock_code} 同步失败: {e}")
            finally:
                sdb.close()
        finally:
            with _syncing_stocks_lock:
                _syncing_stocks.discard(stock_code)

    t = threading.Thread(target=_sync, daemon=True, name=f"auto-sync-{stock_code}")
    t.start()
    return t


def _is_quote_fresh(db: Session, stock_code: str) -> bool:
    """判断行情是否最新: 最新交易日 >= 2 天前（覆盖周末/节假日）"""
    latest = get_latest_trade_date(db, stock_code)
    if latest is None:
        return False
    return latest >= date.today() - timedelta(days=2)


def ensure_quote_available(db: Session, stock_code: str):
    """确保行情数据可用: 本地优先,数据缺失/过期时自动同步

    - 有数据且最新: 直接使用本地数据,不触发同步
    - 有数据但过期: 后台同步,本次先返回本地旧数据
    - 无数据: 限时同步(最多 10 秒),本次请求即可返回远程同步的数据
    """
    has_data = get_latest_trade_date(db, stock_code) is not None
    if not has_data:
        # 无数据: 限时等待同步完成,让用户第一次请求就看到远程数据
        t = _sync_quote_in_background(stock_code)
        if t is not None:
            t.join(timeout=10.0)
        # 后台线程可能已提交新数据,结束当前事务以便后续查询可见
        try:
            db.rollback()
        except Exception:
            pass
    elif not _is_quote_fresh(db, stock_code):
        # 有数据但过期: 后台同步,立即返回现有数据
        _sync_quote_in_background(stock_code)


# ---- 星期涨跌分析 ----
WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五"]
WEEKDAY_EN_TO_CN = {
    "Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三",
    "Thursday": "星期四", "Friday": "星期五",
    "Saturday": "星期六", "Sunday": "星期日",
}


def compute_weekday_stats(db: Session, stock_code: str) -> dict:
    """
    从 stock_daily_quote 计算星期涨跌分布，结果存入 stock_weekday_stats 表。
    返回 {"status": str, "message": str}
    """
    # 查询该股票的所有日线数据，按日期排序
    rows = (
        db.query(StockDailyQuote)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.asc())
        .all()
    )

    if not rows:
        return {"status": "error", "message": f"股票 {stock_code} 无行情数据"}

    # 用 Python 计算（因为需要 weekday 判断，MySQL 的 DAYOFWEEK 和 Python 的 weekday 不完全对齐）
    from collections import defaultdict
    weekday_data = defaultdict(list)

    for i in range(1, len(rows)):
        prev_close = float(rows[i - 1].close_price)
        curr_close = float(rows[i].close_price)
        if prev_close == 0:
            continue
        change_pct = (curr_close - prev_close) / prev_close * 100
        en_name = rows[i].trade_date.strftime("%A")
        cn_name = WEEKDAY_EN_TO_CN.get(en_name)
        if cn_name and cn_name in WEEKDAY_NAMES:
            weekday_data[cn_name].append(change_pct)

    # 计算统计并写入数据库
    import statistics
    saved = 0
    for wd in WEEKDAY_NAMES:
        changes = weekday_data.get(wd, [])
        total = len(changes)
        if total == 0:
            up = down = flat = 0
            up_pct = down_pct = mean_val = 0.0
            median_val = std_val = max_gain = max_loss = None
        else:
            up = sum(1 for c in changes if c > 0)
            down = sum(1 for c in changes if c < 0)
            flat = sum(1 for c in changes if c == 0)
            up_pct = round(up / total * 100, 4)
            down_pct = round(down / total * 100, 4)
            mean_val = round(sum(changes) / total, 6)
            median_val = round(statistics.median(changes), 6) if total >= 2 else round(changes[0], 6)
            std_val = round(statistics.stdev(changes), 6) if total >= 2 else 0.0
            max_gain = round(max(changes), 6)
            max_loss = round(min(changes), 6)

        # Upsert
        existing = (
            db.query(StockWeekdayStats)
            .filter(StockWeekdayStats.stock_code == stock_code, StockWeekdayStats.weekday == wd)
            .first()
        )
        if existing:
            existing.total_count = total
            existing.up_count = up
            existing.down_count = down
            existing.flat_count = flat
            existing.up_pct = up_pct
            existing.down_pct = down_pct
            existing.mean_change = mean_val
            existing.median_change = median_val
            existing.std_change = std_val
            existing.max_gain = max_gain
            existing.max_loss = max_loss
        else:
            db.add(StockWeekdayStats(
                stock_code=stock_code,
                weekday=wd,
                total_count=total,
                up_count=up,
                down_count=down,
                flat_count=flat,
                up_pct=up_pct,
                down_pct=down_pct,
                mean_change=mean_val,
                median_change=median_val,
                std_change=std_val,
                max_gain=max_gain,
                max_loss=max_loss,
            ))
        saved += 1

    db.commit()
    return {"status": "ok", "message": f"已计算并保存 {saved} 个星期统计"}


def get_weekday_analysis(db: Session, stock_code: str) -> Optional[dict]:
    """
    获取星期涨跌分析数据（从 stock_weekday_stats 表读取），
    并生成未来5个交易日的预测。
    """
    # 读取已保存的星期统计
    stats_rows = (
        db.query(StockWeekdayStats)
        .filter(StockWeekdayStats.stock_code == stock_code)
        .order_by(StockWeekdayStats.weekday)
        .all()
    )

    if not stats_rows:
        return None

    def _to_stat_dict(r: StockWeekdayStats) -> dict:
        return {
            "weekday": r.weekday,
            "total_count": r.total_count,
            "up_count": r.up_count,
            "down_count": r.down_count,
            "flat_count": r.flat_count,
            "up_pct": float(r.up_pct),
            "down_pct": float(r.down_pct),
            "mean_change": float(r.mean_change),
            "median_change": float(r.median_change) if r.median_change else None,
            "std_change": float(r.std_change) if r.std_change else None,
            "max_gain": float(r.max_gain) if r.max_gain else None,
            "max_loss": float(r.max_loss) if r.max_loss else None,
        }

    weekday_stats = [_to_stat_dict(r) for r in stats_rows]

    # 确保 5 天都有数据
    existing_weekdays = {s["weekday"] for s in weekday_stats}
    for wd in WEEKDAY_NAMES:
        if wd not in existing_weekdays:
            weekday_stats.append({
                "weekday": wd, "total_count": 0, "up_count": 0,
                "down_count": 0, "flat_count": 0, "up_pct": 0.0,
                "down_pct": 0.0, "mean_change": 0.0,
                "median_change": None, "std_change": None,
                "max_gain": None, "max_loss": None,
            })

    weekday_stats.sort(key=lambda s: WEEKDAY_NAMES.index(s["weekday"]))

    # 计算总交易日数
    total_trading_days = sum(s["total_count"] for s in weekday_stats)

    # 日期范围
    date_range = (
        db.query(
            func.min(StockDailyQuote.trade_date).label("start"),
            func.max(StockDailyQuote.trade_date).label("end"),
        )
        .filter(StockDailyQuote.stock_code == stock_code)
        .first()
    )

    # 生成未来5个交易日预测（从最新交易日的下一天开始）
    latest_date = get_latest_trade_date(db, stock_code)
    predictions = []
    if latest_date:
        from datetime import timedelta
        current = latest_date
        stats_map = {s["weekday"]: s for s in weekday_stats}
        for _ in range(5):
            current = current + timedelta(days=1)
            while current.weekday() >= 5:  # 跳过周末
                current = current + timedelta(days=1)
            en_name = current.strftime("%A")
            cn_name = WEEKDAY_EN_TO_CN.get(en_name, "")
            ws = stats_map.get(cn_name, {})
            predictions.append({
                "date": current.strftime("%Y-%m-%d"),
                "weekday": cn_name,
                "up_probability": ws.get("up_pct", 0.0),
                "down_probability": ws.get("down_pct", 0.0),
                "mean_change": ws.get("mean_change", 0.0),
                "sample_count": ws.get("total_count", 0),
            })

    # 最佳/最差星期
    best_weekday = max(
        [s for s in weekday_stats if s["total_count"] > 0],
        key=lambda s: s["mean_change"], default=None
    )
    worst_weekday = min(
        [s for s in weekday_stats if s["total_count"] > 0],
        key=lambda s: s["mean_change"], default=None
    )

    stock_name = get_stock_name(db, stock_code)

    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "total_trading_days": total_trading_days,
        "date_range_start": date_range.start.strftime("%Y-%m-%d") if date_range and date_range.start else None,
        "date_range_end": date_range.end.strftime("%Y-%m-%d") if date_range and date_range.end else None,
        "weekday_stats": weekday_stats,
        "predictions": predictions,
        "best_weekday": best_weekday["weekday"] if best_weekday else None,
        "worst_weekday": worst_weekday["weekday"] if worst_weekday else None,
    }


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


# ==================== 节日涨跌分析服务 ====================

# 主要节日列表
MAJOR_HOLIDAYS = ["春节", "国庆节", "劳动节", "端午节", "中秋节", "清明节", "元旦"]


def _load_holiday_data():
    """加载假日数据，返回 (holiday_events, non_trading_dates_set)"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    public_holidays = set()
    transfer_workdays = set()
    holiday_events_by_name = defaultdict(list)

    for year in range(2008, 2027):
        filename = os.path.join(script_dir, "public_data", "cn_holidays", f"china_holidays_{year}.json")
        if not os.path.exists(filename):
            continue
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("dates", []):
            d = entry["date"]
            if entry["type"] == "public_holiday":
                public_holidays.add(d)
                holiday_events_by_name[(entry["name"], year)].append(d)
            elif entry["type"] == "transfer_workday":
                transfer_workdays.add(d)

    # 构建假日事件
    holiday_events = []
    for (name, year), dates in holiday_events_by_name.items():
        if name not in MAJOR_HOLIDAYS:
            continue
        dates_sorted = sorted(dates)
        holiday_events.append({
            "name": name, "year": year,
            "start": dates_sorted[0], "end": dates_sorted[-1],
        })
    holiday_events.sort(key=lambda x: (x["year"], MAJOR_HOLIDAYS.index(x["name"])))

    # 构建非交易日集合
    non_trading = set()
    start = date(2008, 1, 1)
    end = date(2026, 12, 31)
    current = start
    while current <= end:
        d_str = current.strftime("%Y-%m-%d")
        is_weekend = current.weekday() >= 5
        is_holiday = d_str in public_holidays
        is_workday_transfer = d_str in transfer_workdays
        if (is_weekend or is_holiday) and not is_workday_transfer:
            non_trading.add(d_str)
        current += timedelta(days=1)

    return holiday_events, non_trading


def get_holiday_analysis(db: Session, stock_code: str) -> dict:
    """获取节日涨跌分析"""
    holiday_events, non_trading = _load_holiday_data()

    # 从数据库获取交易日和收盘价
    rows = (
        db.query(StockDailyQuote.trade_date, StockDailyQuote.close_price)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date)
        .all()
    )

    if not rows:
        return {"error": f"股票 {stock_code} 没有行情数据"}

    trading_dates_set = {r.trade_date.strftime("%Y-%m-%d") for r in rows}
    # 构建日期 -> 收盘价的映射
    date_price_map = {}
    for r in rows:
        date_price_map[r.trade_date.strftime("%Y-%m-%d")] = float(r.close_price)

    # 按日期排序的交易日列表
    trading_dates_sorted = sorted(trading_dates_set)

    # 辅助函数：找交易日
    def find_trading_days(target_str, direction, count):
        """从target_str开始，向前或向后找count个交易日"""
        result = []
        target = datetime.strptime(target_str, "%Y-%m-%d")
        current = target - timedelta(days=1) if direction == "before" else target + timedelta(days=1)
        iterations = 0
        while len(result) < count and iterations < 60:
            d_str = current.strftime("%Y-%m-%d")
            if d_str in trading_dates_set:
                result.append(d_str)
            current = current - timedelta(days=1) if direction == "before" else current + timedelta(days=1)
            iterations += 1
        return result

    def find_last_trading_before(date_str):
        days = find_trading_days(date_str, "before", 1)
        return days[0] if days else None

    def find_first_trading_after(date_str):
        days = find_trading_days(date_str, "after", 1)
        return days[0] if days else None

    def get_daily_change(d_str):
        """计算某日涨跌幅（相对于前一交易日）"""
        if d_str not in date_price_map:
            return None
        # 找前一个交易日
        prev = None
        for td in reversed(trading_dates_sorted):
            if td < d_str:
                prev = td
                break
        if prev and prev in date_price_map:
            return (date_price_map[d_str] - date_price_map[prev]) / date_price_map[prev] * 100
        return None

    # 按节日名收集数据
    raw_data = defaultdict(lambda: defaultdict(list))
    lookback, lookforward = 7, 7

    for event in holiday_events:
        name = event["name"]
        holiday_start = event["start"]
        holiday_end = event["end"]

        last_before = find_last_trading_before(holiday_start)
        first_after = find_first_trading_after(holiday_end)
        if last_before is None or first_after is None:
            continue

        # 节前N个交易日
        pre_dates = find_trading_days(holiday_start, "before", lookback)
        pre_dates = list(reversed(pre_dates))
        for i, d in enumerate(pre_dates):
            pos = -(lookback - i)
            chg = get_daily_change(d)
            if chg is not None:
                raw_data[name][f"day_{pos}"].append({
                    "year": event["year"], "date": d, "change_pct": round(chg, 4)
                })

        # 节后N个交易日
        post_dates = find_trading_days(holiday_end, "after", lookforward)
        for i, d in enumerate(post_dates):
            pos = i + 1
            chg = get_daily_change(d)
            if chg is not None:
                raw_data[name][f"day_{pos}"].append({
                    "year": event["year"], "date": d, "change_pct": round(chg, 4)
                })

        # 累计涨跌幅
        pre_changes = [get_daily_change(d) for d in pre_dates if get_daily_change(d) is not None]
        if pre_changes:
            cum = np.prod([1 + c / 100 for c in pre_changes]) - 1
            raw_data[name]["cumulative_before"].append({"year": event["year"], "change_pct": round(cum * 100, 4)})

        post_changes = [get_daily_change(d) for d in post_dates if get_daily_change(d) is not None]
        if post_changes:
            cum = np.prod([1 + c / 100 for c in post_changes]) - 1
            raw_data[name]["cumulative_after"].append({"year": event["year"], "change_pct": round(cum * 100, 4)})

        if post_changes:
            raw_data[name]["first_day_after"].append({"year": event["year"], "change_pct": post_changes[0]})

    # 汇总统计
    analysis_list = []
    summary_list = []

    for name in MAJOR_HOLIDAYS:
        if name not in raw_data:
            continue

        daily_stats = []
        for day in range(-lookback, 0):
            key = f"day_{day}"
            if key in raw_data[name]:
                changes = [r["change_pct"] for r in raw_data[name][key]]
                daily_stats.append(_build_holiday_stat(abs(day), f"节前{abs(day)}天", changes))

        for day in range(1, lookforward + 1):
            key = f"day_{day}"
            if key in raw_data[name]:
                changes = [r["change_pct"] for r in raw_data[name][key]]
                daily_stats.append(_build_holiday_stat(day, f"节后{day}天", changes))

        cb = None
        if "cumulative_before" in raw_data[name]:
            cb_changes = [r["change_pct"] for r in raw_data[name]["cumulative_before"]]
            cb = _build_cumulative_stat(cb_changes)

        ca = None
        if "cumulative_after" in raw_data[name]:
            ca_changes = [r["change_pct"] for r in raw_data[name]["cumulative_after"]]
            ca = _build_cumulative_stat(ca_changes)

        fd = None
        if "first_day_after" in raw_data[name]:
            fd_changes = [r["change_pct"] for r in raw_data[name]["first_day_after"]]
            fd = _build_cumulative_stat(fd_changes)

        year_records = []
        if "first_day_after" in raw_data[name]:
            for r in raw_data[name]["first_day_after"]:
                year_records.append({
                    "year": r["year"], "date": r.get("date", ""),
                    "change_pct": r["change_pct"]
                })
        year_records.sort(key=lambda x: x["year"])

        years_set = sorted(set(r["year"] for r in raw_data[name].get("first_day_after", [])))
        year_range = f"{years_set[0]}-{years_set[-1]}" if years_set else ""

        analysis_list.append({
            "name": name, "name_cn": name,
            "event_count": len(years_set),
            "year_range": year_range,
            "daily_stats": daily_stats,
            "cumulative_before": cb,
            "cumulative_after": ca,
            "first_day_after": fd,
            "year_records": year_records,
        })

        summary_list.append({
            "name": name,
            "event_count": len(years_set),
            "first_day_up_probability": fd["up_probability"] if fd else 0,
            "first_day_mean_change": fd["mean_change"] if fd else 0,
            "cumulative_before_mean": cb["mean_change"] if cb else 0,
            "cumulative_after_mean": ca["mean_change"] if ca else 0,
        })

    date_range_start = trading_dates_sorted[0] if trading_dates_sorted else None
    date_range_end = trading_dates_sorted[-1] if trading_dates_sorted else None

    return {
        "stock_code": stock_code,
        "stock_name": None,  # 调用方可补充
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "holidays": [h for h in MAJOR_HOLIDAYS if h in raw_data],
        "analysis": analysis_list,
        "summary": summary_list,
    }


def _build_holiday_stat(pos: int, label: str, changes: list) -> dict:
    """构建单日统计"""
    up = sum(1 for c in changes if c > 0)
    down = sum(1 for c in changes if c < 0)
    total = len(changes)
    return {
        "position": pos,
        "position_label": label,
        "count": total,
        "up_count": up,
        "down_count": down,
        "up_probability": round(up / total * 100, 2) if total > 0 else 0,
        "down_probability": round(down / total * 100, 2) if total > 0 else 0,
        "mean_change": round(float(np.mean(changes)), 4) if total > 0 else 0,
        "median_change": round(float(np.median(changes)), 4) if total > 0 else 0,
        "max_gain": round(max(changes), 4) if total > 0 else 0,
        "max_loss": round(min(changes), 4) if total > 0 else 0,
    }


def _build_cumulative_stat(changes: list) -> dict:
    """构建累计统计"""
    up = sum(1 for c in changes if c > 0)
    down = sum(1 for c in changes if c < 0)
    total = len(changes)
    return {
        "count": total,
        "up_count": up,
        "down_count": down,
        "up_probability": round(up / total * 100, 2) if total > 0 else 0,
        "mean_change": round(float(np.mean(changes)), 4) if total > 0 else 0,
        "max_gain": round(max(changes), 4) if total > 0 else 0,
        "max_loss": round(min(changes), 4) if total > 0 else 0,
    }
