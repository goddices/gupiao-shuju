"""
红利再投增强版 —— 大跌买入 + 红利再投，能赚多少？

策略: 观察期内股价从（滚动）历史最高点首次回撤 ≥ x% 时，按当日收盘价买入 y 万元，
之后每次分红到账"无脑买入"该股（红利再投），与「分红不投」「纯股价」对比收益率。

回撤检测使用前复权价格（避免送转除权造成假跌破），买入与模拟使用不复权价格，
分红数据缺失时自动从东方财富拉取并入库。

用法:
    python3 红利再投增强版.py --code 601857 --dip 20 --amount 10
    python3 红利再投增强版.py --code 600519 --dip 30 --amount 50 --start 2015-01-01 --tax 0.1
"""
import argparse
import os
import sys

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
from dividend_reinvest_engine import simulate_dip_buy
from result_saver import reset_saver

plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 只统计"实施分配"的分红
IMPL_PROGRESS = "实施分配"


def parse_args():
    parser = argparse.ArgumentParser(
        description="红利再投增强版：大跌 x% 买入 y 万 + 红利再投，计算收益率"
    )
    parser.add_argument("--code", default="601857", help="股票代码（默认 601857 中国石油）")
    parser.add_argument("--start", default=None, help="观察起点 YYYY-MM-DD（默认：数据最早）")
    parser.add_argument("--end", default=None, help="观察终点 YYYY-MM-DD（默认：数据最晚）")
    parser.add_argument("--dip", type=float, default=20.0, help="回撤买入幅度 %（默认 20 = 从高点跌 20%% 买入）")
    parser.add_argument("--amount", type=float, default=10.0, help="买入金额，万元（默认 10 万）")
    parser.add_argument("--tax", type=float, default=0.0, help="分红税率 0~1（默认 0 = 长期持有免税）")
    parser.add_argument("--sync", action="store_true", help="强制重新从东方财富拉取分红明细")
    parser.add_argument("--no-chart", action="store_true", help="不弹出图形窗口（图片仍会保存到 results 目录）")
    return parser.parse_args()


def load_quotes(db, stock_code: str) -> list:
    """读不复权收盘价（升序）"""
    rows = (
        db.query(StockDailyQuote.trade_date, StockDailyQuote.close_price)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.asc())
        .all()
    )
    return [{"trade_date": r.trade_date, "close_price": float(r.close_price)} for r in rows]


def load_forward_quotes(db, stock_code: str, n_expected: int) -> list:
    """读前复权收盘价（回撤检测用；不完整则返回 None 回退不复权）"""
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
    return result if len(result) == n_expected and result else None


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
            "report_date": r.report_date,
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


def print_report(result: dict, stock_name: str, stock_code: str, log):
    t = result["trigger"]
    s = result["summary"]

    log("=" * 76)
    log(f"        {stock_name}({stock_code}) 红利再投增强版报告（大跌买入）")
    log("=" * 76)

    log(f"\n1. 模拟区间（买入日起）: {s['start_date']} 至 {s['end_date']}（{s['trading_days']} 个交易日）")

    log(f"\n2. 大跌买入触发（{t['trigger_series']}口径检测）:")
    log(f"   期间最高价: {t['peak_price']:.2f} 元（{t['peak_date']}）")
    log(f"   首次回撤 ≥{t['dip_pct']:.1f}%: {t['buy_date']} 收盘 {t['buy_price']:.2f} 元"
        f"（实际回撤 {t['actual_dip_pct']:.2f}%）")

    log(f"\n3. 买入: {t['buy_amount']:,.0f} 元（{t['buy_amount']/10000:.1f} 万）"
        f" → {t['initial_shares']:,} 股 @ {t['buy_price']:.2f} 元")

    log(f"\n4. 三策略对比（买入日 至 {s['end_date']}）:")
    lines = [
        ("红利再投", s["reinvest"]),
        ("分红不投", s["no_reinvest"]),
        ("纯股价  ", s["price_only"]),
    ]
    for name, x in lines:
        ann = (f"{x['annual_return_pct']*100:.2f}%" if x["annual_return_pct"] is not None else "N/A")
        log(f"   【{name}】期末总资产: {x['final_asset']:>14,.2f} 元  "
            f"收益率: {x['total_return_pct']:>8.2f}%  年化: {ann}")
        log(f"            期末持股: {x['final_shares']:>10,} 股  "
            f"期末现金: {x['final_cash']:>12,.2f} 元  "
            f"最大回撤: {x['max_drawdown_pct']:.2f}%  累计分红: {x['total_dividends']:>12,.2f} 元")

    ri = s["reinvest"]
    nr = s["no_reinvest"]
    diff = ri["final_asset"] - nr["final_asset"]
    log("\n5. 红利再投的贡献:")
    log(f"   累计分红到账: {ri['total_dividends']:,.2f} 元，"
        f"其中再投 {ri['total_reinvested']:,.2f} 元（{ri['reinvest_count']} 次买入）")
    log(f"   红利再投比「分红不投」多赚: {diff:,.2f} 元（+{diff / nr['final_asset'] * 100:.2f}%）")
    log(f"   比「纯股价」多赚: {ri['final_asset'] - s['price_only']['final_asset']:,.2f} 元")

    events = result["dividend_events"]
    log("\n6. 分红事件明细:")
    if events:
        log(f"   {'除息日':<12}{'每10股派息':>10}{'送转(股)':>9}{'到账金额':>13}"
            f"{'再投股数':>10}{'再投金额':>13}{'当日收盘':>10}")
        for e in events:
            bonus = (e["bonus_per_10"] or 0) + (e["conversion_per_10"] or 0)
            log(f"   {e['ex_dividend_date']:<12}{e['cash_per_10']:>10.4f}{bonus:>9.1f}"
                f"{e['cash_received']:>13,.2f}{e['reinvest_shares']:>10,}"
                f"{e['reinvest_amount']:>13,.2f}{e['close_price']:>10.2f}")
    else:
        log("   （买入后无分红记录）")

    if result["warnings"]:
        log("\n7. 提示:")
        for w in result["warnings"]:
            log(f"   - {w}")

    log("=" * 76)


def make_chart(result: dict, stock_name: str, stock_code: str, saver, show: bool = True):
    """对比图：权益曲线（三线 + 买入日/除息日标记）+ 年度分红柱状图"""
    t = result["trigger"]
    equity_curve = result["equity_curve"]
    events = result["dividend_events"]

    dates = [e["trade_date"] for e in equity_curve]
    re_assets = [e["reinvest_asset"] for e in equity_curve]
    nr_assets = [e["no_reinvest_asset"] for e in equity_curve]
    po_assets = [e["price_only_asset"] for e in equity_curve]

    fig = plt.figure(figsize=(16, 9))

    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(dates, re_assets, label="红利再投", color="#cf1322", linewidth=1.6)
    ax1.plot(dates, nr_assets, label="分红不投", color="#1890ff", linewidth=1.2, alpha=0.85)
    ax1.plot(dates, po_assets, label="纯股价", color="#999999", linewidth=1.0, linestyle="--", alpha=0.8)

    # 买入日标记
    ax1.axvline(t["buy_date"], color="#d4b106", linestyle="--", linewidth=1.2, alpha=0.8)
    ax1.annotate(f"买入日 {t['buy_date']}\n@{t['buy_price']:.2f} 元",
                 xy=(t["buy_date"], re_assets[0]), xytext=(len(dates) * 0.45, re_assets[0] * 0.92),
                 fontsize=9, color="#ad6800",
                 arrowprops=dict(arrowstyle="->", color="#ad6800"))

    # 除息日标记（只标有行情的除息日）
    curve_map = {e["trade_date"]: e["reinvest_asset"] for e in equity_curve}
    ex_dates = [e["ex_dividend_date"] for e in events if e["ex_dividend_date"] in curve_map]
    if ex_dates:
        ax1.scatter(ex_dates, [curve_map[d] for d in ex_dates], marker="v",
                    color="#d4b106", s=36, zorder=5, label=f"除息日({len(ex_dates)})")

    ax1.set_title(f"{stock_name}({stock_code}) 大跌 {t['dip_pct']:.0f}% 买入 {t['buy_amount']/10000:.0f} 万 + 红利再投"
                  f" —— 权益曲线对比（不复权）")
    ax1.set_ylabel("总资产（元）")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    tick_step = max(1, len(dates) // 12)
    ax1.set_xticks(range(0, len(dates), tick_step))
    ax1.set_xticklabels([dates[i] for i in range(0, len(dates), tick_step)], rotation=30, fontsize=8)

    # 年度分红柱状图
    ax2 = plt.subplot(2, 1, 2)
    year_cash = {}
    for e in events:
        y = e["ex_dividend_date"][:4]
        year_cash[y] = year_cash.get(y, 0.0) + e["cash_received"]
    if year_cash:
        years = sorted(year_cash)
        values = [year_cash[y] for y in years]
        bars = ax2.bar(years, values, color="#fa8c16", alpha=0.85)
        ax2.set_title("年度分红到账金额（元）")
        ax2.set_ylabel("到账金额（元）")
        ax2.grid(True, alpha=0.3, axis="y")
        for bar, v in zip(bars, values):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     f"{v:,.0f}", ha="center", va="bottom", fontsize=8)
        ax2.tick_params(axis="x", rotation=45, labelsize=8)
    else:
        ax2.text(0.5, 0.5, "买入后无分红记录", ha="center", va="center",
                 transform=ax2.transAxes, fontsize=14, color="#999")
        ax2.set_axis_off()

    plt.tight_layout()
    if show:
        plt.show()
    chart_path = saver.save_chart(f"{stock_code}_红利再投增强版.jpg")
    plt.close(fig)
    return chart_path


def main():
    os.chdir(ROOT_DIR)
    args = parse_args()
    stock_code = args.code.strip()

    saver = reset_saver("红利再投增强版")
    saver.set_tag(stock_code)
    log = saver.log

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stock_name = get_stock_name(db, stock_code) or stock_code
        log(f"正在读取 {stock_name}({stock_code}) 的行情...")
        quotes = load_quotes(db, stock_code)
        if not quotes:
            log(f"数据库中没有 {stock_code} 的行情数据，请先同步行情（导入数据功能或 /api/stocks/{stock_code}/fetch）")
            return
        log(f"共 {len(quotes)} 个交易日（{quotes[0]['trade_date']} ~ {quotes[-1]['trade_date']}）")

        forward_quotes = load_forward_quotes(db, stock_code, len(quotes))
        if forward_quotes:
            log("回撤检测使用前复权价格（避免送转除权造成假跌破）")
        else:
            log("前复权数据缺失，回撤检测回退为不复权价格")

        dividends = ensure_dividends(db, stock_code, args.sync, log)
        log(f"分红明细: {len(dividends)} 笔（仅统计已实施分配）")

        result = simulate_dip_buy(
            quotes=quotes,
            dividends=dividends,
            dip_pct=args.dip,
            buy_amount=args.amount * 10000,  # 万元 → 元
            start_date=args.start,
            end_date=args.end,
            tax_rate=args.tax,
            reinvest=True,
            lot_size=100,
            trigger_quotes=forward_quotes,
        )

        if result["status"] != "ok":
            log(f"模拟失败: {result.get('message', '未知错误')}")
            return

        print_report(result, stock_name, stock_code, log)
        make_chart(result, stock_name, stock_code, saver, show=not args.no_chart)
    finally:
        db.close()

    saver.finalize()


if __name__ == "__main__":
    main()
