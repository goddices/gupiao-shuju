"""股票行情数据查询服务"""
import sys
import os
import asyncio
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StockDailyQuote, StockDividendEvent, StockInfo, StockCoreData, StockCookie, StockWeekdayStats
from emdata import EastmoneyStockListReader, SEED_COOKIE

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
    }


def sync_stock_core_data(db: Session, stock_code: str) -> dict:
    """
    从东方财富获取个股核心数据并保存到数据库
    :return: {"status": str, "message": str, "data": dict|None}
    """
    from emdata import EastmoneyCurrentCoreDataReader, Market

    market = Market.SHANGHAI if stock_code.startswith("6") else Market.SHENGZHEN
    fallback_cookies = get_fallback_cookies(db)

    reader = EastmoneyCurrentCoreDataReader()
    async def _fetch():
        return await reader.fetch_stock_info_async(market, stock_code, fallback_cookies)

    try:
        info = asyncio.run(_fetch())
    except Exception as e:
        return {"status": "error", "message": f"网络请求失败: {str(e)}", "data": None}

    if info is None:
        return {"status": "error", "message": "获取核心数据为空", "data": None}

    # 保存成功的 Cookie 到 DB
    if reader.last_used_cookie:
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
