"""
红利再投模拟 —— 个股长期红利再投可以赚多少？

用不复权价格模拟: 期初全仓买入 → 每次分红到账后按除息日收盘价"无脑买入"该股，
并与"分红不投(现金留存)"、"纯股价"两个基准对比。

数据来源: MySQL stock_daily_quote(不复权收盘价) + stock_dividend_detail(东财分红明细)。
分红数据缺失时自动从东方财富拉取并入库。

用法:
    python3 红利再投.py --code 601857 --start 2008-01-01
    python3 红利再投.py --code 600519 --start 2015-01-01 --capital 500000 --tax 0.1 --sync
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
from dividend_reinvest_engine import simulate_dividend_reinvest
from result_saver import reset_saver

plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 只统计"实施分配"的分红
IMPL_PROGRESS = "实施分配"


def parse_args():
    parser = argparse.ArgumentParser(
        description="红利再投模拟：用不复权价格模拟长期持股+分红无脑再投的收益"
    )
    parser.add_argument("--code", default="601857", help="股票代码（默认 601857 中国石油）")
    parser.add_argument("--start", default=None, help="起始日期 YYYY-MM-DD（默认：最早有数据）")
    parser.add_argument("--end", default=None, help="结束日期 YYYY-MM-DD（默认：最新有数据）")
    parser.add_argument("--capital", type=float, default=100000, help="初始资金（默认 100000）")
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


def print_report(summary: dict, events: list, warnings_list: list, stock_name: str,
                 stock_code: str, initial_cash: float, tax_rate: float, log):
    log("=" * 76)
    log(f"        {stock_name}({stock_code}) 红利再投模拟报告")
    log(f"        期间: {summary['start_date']} 至 {summary['end_date']} "
        f"（{summary['trading_days']} 个交易日）")
    log("=" * 76)

    log("\n1. 区间行情概览（不复权）:")
    log(f"   期初收盘: {summary['first_close']:.2f}   期末收盘: {summary['last_close']:.2f}   "
        f"区间涨跌幅: {summary['period_return_pct']:.2f}%")

    log(f"\n2. 三策略对比（初始资金 {initial_cash:,.0f} 元，分红税率 {tax_rate*100:.0f}%）:")
    lines = [
        ("红利再投", summary["reinvest"]),
        ("分红不投", summary["no_reinvest"]),
        ("纯股价  ", summary["price_only"]),
    ]
    for name, s in lines:
        log(f"   【{name}】期末总资产: {s['final_asset']:>14,.2f} 元  "
            f"收益率: {s['total_return_pct']:>8.2f}%  "
            f"年化: {(str(round(s['annual_return_pct']*100, 2)) + '%') if s['annual_return_pct'] is not None else 'N/A'}")
        log(f"            期末持股: {s['final_shares']:>10,} 股  "
            f"期末现金: {s['final_cash']:>12,.2f} 元  "
            f"最大回撤: {s['max_drawdown_pct']:.2f}%  "
            f"累计分红: {s['total_dividends']:>12,.2f} 元")

    ri = summary["reinvest"]
    nr = summary["no_reinvest"]
    diff = ri["final_asset"] - nr["final_asset"]
    log("\n3. 红利再投的贡献:")
    log(f"   累计分红到账: {ri['total_dividends']:,.2f} 元，"
        f"其中再投 {ri['total_reinvested']:,.2f} 元（{ri['reinvest_count']} 次买入）")
    log(f"   红利再投比「分红不投」多赚: {diff:,.2f} 元 "
        f"（+{diff / nr['final_asset'] * 100:.2f}%）")
    log(f"   比「纯股价」多赚: {ri['final_asset'] - summary['price_only']['final_asset']:,.2f} 元")

    log("\n4. 分红事件明细:")
    if events:
        log(f"   {'除息日':<12}{'每10股派息':>10}{'送转(股)':>9}{'到账金额':>13}"
            f"{'再投股数':>10}{'再投金额':>13}{'当日收盘':>10}")
        for e in events:
            bonus = (e["bonus_per_10"] or 0) + (e["conversion_per_10"] or 0)
            log(f"   {e['ex_dividend_date']:<12}{e['cash_per_10']:>10.4f}{bonus:>9.1f}"
                f"{e['cash_received']:>13,.2f}{e['reinvest_shares']:>10,}"
                f"{e['reinvest_amount']:>13,.2f}{e['close_price']:>10.2f}")
    else:
        log("   （区间内无分红记录）")

    if warnings_list:
        log("\n5. 提示:")
        for w in warnings_list:
            log(f"   - {w}")

    log("=" * 76)


def make_chart(equity_curve: list, events: list, summary: dict,
               stock_name: str, stock_code: str, saver, show: bool = True):
    """生成对比图：权益曲线（三线 + 除息日标记）+ 年度分红柱状图（pyplot 绘制，show=True 时弹窗显示）"""
    dates = [e["trade_date"] for e in equity_curve]
    re_assets = [e["reinvest_asset"] for e in equity_curve]
    nr_assets = [e["no_reinvest_asset"] for e in equity_curve]
    po_assets = [e["price_only_asset"] for e in equity_curve]

    fig = plt.figure(figsize=(16, 9))

    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(dates, re_assets, label="红利再投", color="#cf1322", linewidth=1.6)
    ax1.plot(dates, nr_assets, label="分红不投", color="#1890ff", linewidth=1.2, alpha=0.85)
    ax1.plot(dates, po_assets, label="纯股价", color="#999999", linewidth=1.0, linestyle="--", alpha=0.8)

    # 除息日标记（只标有行情的除息日）
    curve_map = {e["trade_date"]: e["reinvest_asset"] for e in equity_curve}
    ex_dates = [e["ex_dividend_date"] for e in events if e["ex_dividend_date"] in curve_map]
    if ex_dates:
        ax1.scatter(ex_dates, [curve_map[d] for d in ex_dates], marker="v",
                    color="#d4b106", s=36, zorder=5, label=f"除息日({len(ex_dates)})")

    ax1.set_title(f"{stock_name}({stock_code}) 红利再投模拟 —— 权益曲线对比（不复权）")
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
        ax2.text(0.5, 0.5, "区间内无分红记录", ha="center", va="center",
                 transform=ax2.transAxes, fontsize=14, color="#999")
        ax2.set_axis_off()

    plt.tight_layout()
    if show:
        plt.show()  # 弹窗显示（关闭窗口后继续）
    chart_path = saver.save_chart(f"{stock_code}_红利再投.jpg")
    plt.close(fig)
    return chart_path


def main():
    os.chdir(ROOT_DIR)  # results/ 目录固定在脚本所在目录
    args = parse_args()
    stock_code = args.code.strip()

    saver = reset_saver("红利再投")
    saver.set_tag(stock_code)
    log = saver.log

    # 建表（幂等）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stock_name = get_stock_name(db, stock_code) or stock_code
        log(f"正在读取 {stock_name}({stock_code}) 的不复权行情...")
        quotes = load_quotes(db, stock_code)
        if not quotes:
            log(f"数据库中没有 {stock_code} 的行情数据，请先同步行情（导入数据功能或 /api/stocks/{stock_code}/fetch）")
            return

        log(f"共 {len(quotes)} 个交易日"
            f"（{quotes[0]['trade_date']} ~ {quotes[-1]['trade_date']}）")

        dividends = ensure_dividends(db, stock_code, args.sync, log)
        log(f"分红明细: {len(dividends)} 笔（仅统计已实施分配）")

        result = simulate_dividend_reinvest(
            quotes=quotes,
            dividends=dividends,
            initial_cash=args.capital,
            start_date=args.start,
            end_date=args.end,
            tax_rate=args.tax,
            reinvest=True,
            lot_size=100,
        )

        if result["status"] != "ok":
            log(f"模拟失败: {result.get('message', '未知错误')}")
            return

        print_report(
            result["summary"], result["dividend_events"], result["warnings"],
            stock_name, stock_code, args.capital, args.tax, log,
        )

        # 图表始终绘制并保存（--no-chart 仅关闭弹窗）
        make_chart(
            result["equity_curve"], result["dividend_events"], result["summary"],
            stock_name, stock_code, saver, show=not args.no_chart,
        )
    finally:
        db.close()

    saver.finalize()  # finalize 内已输出保存路径


if __name__ == "__main__":
    main()
