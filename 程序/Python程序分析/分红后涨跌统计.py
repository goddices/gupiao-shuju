"""
分红后涨跌统计 —— 分红除息后 N 个交易日，下跌概率是多少？

以分红**除息日**为锚点（当天收盘价已是除息后价格，价格缺口已剔除），
统计除息日后第 1~N 个交易日的累计涨跌幅：
    - 各窗口（如 5/10/30 日）下跌概率、平均涨跌幅、中位数、最大跌幅/涨幅
    - 每笔分红明细（除息日/每10股派息/除息日收盘/各窗口涨跌幅）
    - 图表：各窗口下跌概率柱状图 + 除息后逐日平均累计涨跌幅曲线（事件研究）

数据来源: MySQL stock_daily_quote(不复权收盘价) + stock_dividend_detail(东财分红明细)。
分红数据缺失时自动从东方财富拉取并入库。

用法:
    python3 分红后涨跌统计.py --code 601857 --days 5,10,30
    python3 分红后涨跌统计.py --code 601728 --days 5,10,30 --start 2021-08-20 --no-chart
"""
import argparse
import os
import sys
import warnings as py_warnings

py_warnings.filterwarnings("ignore")

# 根目录 + backend 目录入 sys.path（backend 为命名空间包，其内部使用 `from models import ...`）
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
for p in (ROOT_DIR, BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib.pyplot as plt

from backend.database import SessionLocal, engine
from backend.models import Base, StockDailyQuote, StockDividendDetail
from backend.services import sync_stock_dividends, get_stock_name
from result_saver import reset_saver

plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 只统计"实施分配"的分红
IMPL_PROGRESS = "实施分配"


def parse_args():
    parser = argparse.ArgumentParser(
        description="分红后涨跌统计：以除息日为锚点，统计之后 N 个交易日下跌概率"
    )
    parser.add_argument("--code", default="601857", help="股票代码（默认 601857 中国石油）")
    parser.add_argument("--start", default=None, help="观察起点 YYYY-MM-DD（默认：数据最早）")
    parser.add_argument("--end", default=None, help="观察终点 YYYY-MM-DD（默认：数据最晚）")
    parser.add_argument("--days", default="5,10,30",
                        help="统计窗口（逗号分隔的交易日天数，默认 5,10,30）")
    parser.add_argument("--sync", action="store_true", help="强制重新从东方财富拉取分红明细")
    parser.add_argument("--no-chart", action="store_true", help="不弹出图形窗口（图片仍会保存到 results 目录）")
    return parser.parse_args()


def load_quotes(db, stock_code: str, start_date=None, end_date=None) -> list:
    """读不复权收盘价（升序，可按区间过滤）"""
    q = db.query(StockDailyQuote.trade_date, StockDailyQuote.close_price).filter(
        StockDailyQuote.stock_code == stock_code
    )
    if start_date:
        q = q.filter(StockDailyQuote.trade_date >= start_date)
    if end_date:
        q = q.filter(StockDailyQuote.trade_date <= end_date)
    rows = q.order_by(StockDailyQuote.trade_date.asc()).all()
    return [{"trade_date": r.trade_date, "close_price": float(r.close_price)} for r in rows]


def load_dividends(db, stock_code: str) -> list:
    """读已实施的分红明细"""
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
            "cash_per_10": float(r.cash_per_10) if r.cash_per_10 else 0.0,
            "bonus_per_10": float(r.bonus_per_10) if r.bonus_per_10 else 0.0,
            "conversion_per_10": float(r.conversion_per_10) if r.conversion_per_10 else 0.0,
        }
        for r in rows
    ]


def ensure_dividends(db, stock_code: str, force_sync: bool, log) -> list:
    """确保分红数据存在：缺失或 --sync 时从东方财富拉取入库"""
    exists = (
        db.query(StockDividendDetail.id)
        .filter(StockDividendDetail.stock_code == stock_code)
        .first()
    )
    if exists and not force_sync:
        return load_dividends(db, stock_code)

    log(f"正在从东方财富同步 {stock_code} 的分红明细...")
    result = sync_stock_dividends(db, stock_code)
    log(result["message"])
    if result["status"] != "ok":
        return []
    return load_dividends(db, stock_code)


def compute_events(quotes: list, dividends: list, windows: list) -> dict:
    """以除息日为锚点计算各窗口累计涨跌幅

    :param quotes: 不复权行情（升序）
    :param dividends: 分红明细（实施分配）
    :param windows: 统计窗口列表（交易日天数，升序）
    :return: {"events": [...], "daily_curve": [(day, 平均累计涨跌幅, 下跌概率)], "warnings": [...]}
    """
    dates = [q["trade_date"] for q in quotes]
    closes = [q["close_price"] for q in quotes]
    date_idx = {d: i for i, d in enumerate(dates)}
    max_w = max(windows)
    warnings = []

    # 先解析每个除息日的锚点行（除息日无行情 → 顺延到下一交易日）
    anchors = []
    for dv in dividends:
        ex = dv["ex_dividend_date"]
        i = date_idx.get(ex)
        if i is None:
            for j, d in enumerate(dates):
                if d > ex:
                    warnings.append(f"除息日 {ex} 无行情，顺延到 {dates[j]} 统计")
                    i = j
                    break
        if i is None:
            continue
        if i + max_w >= len(closes):
            warnings.append(f"除息日 {ex} 之后不足 {max_w} 个交易日，已跳过")
            continue
        anchors.append((dv, i))

    events = []
    for dv, i in anchors:
        close0 = closes[i]
        rets = {w: round((closes[i + w] / close0 - 1) * 100, 2) for w in windows}
        events.append({
            "ex_dividend_date": str(dv["ex_dividend_date"]),
            "cash_per_10": round(dv["cash_per_10"], 4),
            "close0": close0,
            "rets": rets,
        })

    # 逐日曲线（1 ~ max_w 日的平均累计涨跌幅与下跌概率，事件研究口径）
    daily_curve = []
    for k in range(1, max_w + 1):
        rets = [(closes[i + k] / closes[i] - 1) * 100 for dv, i in anchors]
        if rets:
            daily_curve.append({
                "day": k,
                "avg_return": round(sum(rets) / len(rets), 2),
                "down_pct": round(sum(1 for r in rets if r < 0) / len(rets) * 100, 1),
                "n": len(rets),
            })
    return {"events": events, "daily_curve": daily_curve, "warnings": warnings}


def _stats(events: list, w: int) -> dict:
    rets = [e["rets"][w] for e in events]
    downs = sum(1 for r in rets if r < 0)
    return {
        "n": len(rets),
        "down": downs,
        "pct": round(downs / len(rets) * 100, 1) if rets else 0.0,
        "avg": round(sum(rets) / len(rets), 2) if rets else 0.0,
        "median": round(sorted(rets)[len(rets) // 2], 2) if rets else 0.0,
        "max_draw": round(min(rets), 2) if rets else 0.0,
        "max_gain": round(max(rets), 2) if rets else 0.0,
    }


def print_report(events: list, windows: list, daily_curve: list, warnings_list: list,
                 stock_name: str, stock_code: str, log):
    log("=" * 78)
    log(f"        {stock_name}({stock_code}) 分红后涨跌统计报告")
    log("=" * 78)

    log(f"\n1. 口径说明:")
    log("   锚点: 分红除息日（当天收盘已是除息后价格，价格缺口已剔除）")
    log("   下跌判定: 第 N 个交易日收盘 < 除息日收盘（N 日累计涨跌幅为负）")
    log(f"   统计窗口: {', '.join(str(w) + ' 日' for w in windows)}")

    log(f"\n2. 结论速览（有效样本 {len(events)} 次分红）:")
    log(f"   {'窗口':>6}{'下跌次数':>9}{'下跌概率':>10}{'平均涨跌幅':>11}"
        f"{'中位数':>9}{'最大跌幅':>10}{'最大涨幅':>10}")
    for w in windows:
        s = _stats(events, w)
        down_n = f"{s['down']}/{s['n']}"
        pct = str(s['pct']) + '%'
        log(f"   {str(w) + ' 日':>6}{down_n:>9}{pct:>10}"
            f"{s['avg']:>+10.2f}%{s['median']:>+9.2f}%{s['max_draw']:>+10.2f}%{s['max_gain']:>+10.2f}%")

    log(f"\n3. 每笔分红明细:")
    header = (f"   {'除息日':<12}{'每10股派息':>10}{'除息日收盘':>10}"
              + "".join(f"{str(w) + '日涨跌幅':>11}" for w in windows))
    log(header)
    for e in events:
        cols = "".join(f"{e['rets'][w]:>+10.2f}%" for w in windows)
        log(f"   {e['ex_dividend_date']:<12}{e['cash_per_10']:>10.4f}{e['close0']:>10.2f}{cols}")

    if daily_curve:
        log(f"\n4. 除息后逐日平均累计涨跌幅（1~{daily_curve[-1]['day']} 日）:")
        for d in daily_curve:
            log(f"   第 {d['day']:>2} 日: 平均 {d['avg_return']:>+7.2f}%  "
                f"下跌概率 {d['down_pct']:>5.1f}%（{d['n']} 个样本）")

    if warnings_list:
        log("\n5. 提示:")
        for w in warnings_list:
            log(f"   - {w}")

    log("=" * 78)


def make_chart(events: list, windows: list, daily_curve: list,
               stock_name: str, stock_code: str, saver, show: bool = True):
    """图1: 各窗口下跌概率柱状图（50% 参考线）；图2: 除息后逐日平均累计涨跌幅曲线"""
    fig = plt.figure(figsize=(16, 9))

    ax1 = plt.subplot(1, 2, 1)
    labels = [f"{w} 日" for w in windows]
    pcts = [_stats(events, w)["pct"] for w in windows]
    bars = ax1.bar(labels, pcts, color=["#cf1322" if p >= 50 else "#1890ff" for p in pcts],
                   alpha=0.85)
    ax1.axhline(50, color="#8c8c8c", linestyle="--", linewidth=1, label="50% 参考线")
    ax1.set_title(f"{stock_name}({stock_code}) 除息后 N 日下跌概率\n（有效样本 {len(events)} 次分红）")
    ax1.set_ylabel("下跌概率 (%)")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.legend()
    for bar, p in zip(bars, pcts):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f"{p:.1f}%", ha="center", fontsize=11, fontweight="bold")

    ax2 = plt.subplot(1, 2, 2)
    if daily_curve:
        days = [d["day"] for d in daily_curve]
        avgs = [d["avg_return"] for d in daily_curve]
        ax2.plot(days, avgs, marker="o", color="#cf1322", linewidth=1.6,
                 label="平均累计涨跌幅")
        ax2.fill_between(days, 0, avgs, alpha=0.12, color="#cf1322")
        ax2.axhline(0, color="#8c8c8c", linestyle="--", linewidth=1)
        ax2.set_title(f"除息后逐日平均累计涨跌幅（事件研究，1~{daily_curve[-1]['day']} 日）")
        ax2.set_xlabel("除息后第 N 个交易日")
        ax2.set_ylabel("平均累计涨跌幅 (%)")
        ax2.grid(True, alpha=0.3)
        ax2.legend()
    else:
        ax2.text(0.5, 0.5, "无足够样本", ha="center", va="center",
                 transform=ax2.transAxes, fontsize=14, color="#999")
        ax2.set_axis_off()

    plt.tight_layout()
    if show:
        plt.show()
    chart_path = saver.save_chart(f"{stock_code}_分红后涨跌统计.jpg")
    plt.close(fig)
    return chart_path


def main():
    os.chdir(ROOT_DIR)
    args = parse_args()
    stock_code = args.code.strip()

    # 解析窗口
    try:
        windows = sorted({int(x) for x in args.days.split(",") if x.strip()})
    except ValueError:
        print("--days 参数无效，应为逗号分隔的整数，如 5,10,30")
        return
    if not windows or any(w <= 0 for w in windows):
        print("--days 参数无效，天数必须大于 0")
        return

    saver = reset_saver("分红后涨跌统计")
    saver.set_tag(stock_code)
    log = saver.log

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stock_name = get_stock_name(db, stock_code) or stock_code
        log(f"正在读取 {stock_name}({stock_code}) 的不复权行情...")
        quotes = load_quotes(db, stock_code, args.start, args.end)
        if not quotes:
            log(f"数据库中没有 {stock_code} 的行情数据，请先同步行情（导入数据功能或 /api/stocks/{stock_code}/fetch）")
            return
        log(f"共 {len(quotes)} 个交易日（{quotes[0]['trade_date']} ~ {quotes[-1]['trade_date']}）")

        dividends = ensure_dividends(db, stock_code, args.sync, log)
        log(f"分红明细: {len(dividends)} 笔（仅统计已实施分配）")

        result = compute_events(quotes, dividends, windows)
        events = result["events"]
        if not events:
            log("区间内无有效样本（无分红记录或除息日后行情不足），无法统计")
            return

        print_report(events, windows, result["daily_curve"], result["warnings"],
                     stock_name, stock_code, log)
        make_chart(events, windows, result["daily_curve"],
                   stock_name, stock_code, saver, show=not args.no_chart)
    finally:
        db.close()

    saver.finalize()


if __name__ == "__main__":
    main()
