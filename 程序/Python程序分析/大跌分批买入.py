"""
大跌分批买入 + 红利再投 —— 当天大跌 x% 就在最低价买一笔，能赚多少？

策略: 每个交易日若盘中最低价较前收盘跌幅 ≥ x%（当天大跌），按当日最低价买入
一笔，金额 = 总仓位 × y%（每次触发买一笔，直至现金用完），此后分红到账
"无脑买入"该股（红利再投）。

对比基准:
    staged_reinvest   分批买入 + 红利再投（本策略）
    lump_reinvest     首个触发日一次性全仓买入 + 红利再投
    lump_no_reinvest  首个触发日一次性全仓买入 + 分红不投

口径说明: 触发条件用盘中最低价（相当于挂"前收盘 -x%"的限价单，盘中跌破即成交），
成交价 = 当日最低价；买入与模拟均用不复权价格；分红数据缺失时自动从东方财富拉取入库。

用法:
    python3 大跌分批买入.py --code 601857 --position 100 --ratio 5 --dip 3
    python3 大跌分批买入.py --code 600519 --position 50 --ratio 10 --dip 5 --start 2018-01-01 --tax 0.1
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
from dividend_reinvest_engine import simulate_staged_dip_buy
from result_saver import reset_saver

plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 只统计"实施分配"的分红
IMPL_PROGRESS = "实施分配"


def parse_args():
    parser = argparse.ArgumentParser(
        description="大跌分批买入：当天大跌 x% 在最低价买入总仓位 y% 的一笔 + 红利再投"
    )
    parser.add_argument("--code", default="601857", help="股票代码（默认 601857 中国石油）")
    parser.add_argument("--start", default=None, help="观察起点 YYYY-MM-DD（默认：数据最早）")
    parser.add_argument("--end", default=None, help="观察终点 YYYY-MM-DD（默认：数据最晚）")
    parser.add_argument("--position", type=float, default=100.0,
                        help="总仓位，万元（默认 100 万）")
    parser.add_argument("--ratio", type=float, default=5.0,
                        help="每笔买入占总仓位比例 %%（默认 5 = 每次买总仓位的 5%%）")
    parser.add_argument("--dip", type=float, default=3.0,
                        help="当日大跌阈值 %%（默认 3 = 盘中最低价较前收盘跌 3%% 触发）")
    parser.add_argument("--tax", type=float, default=0.0, help="分红税率 0~1（默认 0 = 长期持有免税）")
    parser.add_argument("--sync", action="store_true", help="强制重新从东方财富拉取分红明细")
    parser.add_argument("--no-chart", action="store_true", help="不弹出图形窗口（图片仍会保存到 results 目录）")
    return parser.parse_args()


def load_quotes(db, stock_code: str) -> list:
    """读不复权日线（升序），含最低价与收盘价"""
    rows = (
        db.query(StockDailyQuote.trade_date, StockDailyQuote.low_price, StockDailyQuote.close_price)
        .filter(StockDailyQuote.stock_code == stock_code)
        .order_by(StockDailyQuote.trade_date.asc())
        .all()
    )
    return [
        {"trade_date": r.trade_date, "low_price": float(r.low_price), "close_price": float(r.close_price)}
        for r in rows
    ]


def load_forward_quotes(db, stock_code: str, n_expected: int) -> list:
    """读前复权收盘价（成本前复权口径用；不完整则返回 None，回退不复权口径）"""
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
    p = result["params"]
    s = result["summary"]
    triggers = result["triggers"]

    log("=" * 78)
    log(f"        {stock_name}({stock_code}) 大跌分批买入 + 红利再投 报告")
    log("=" * 78)

    log(f"\n1. 策略参数:")
    log(f"   总仓位: {p['total_position']:,.0f} 元（{p['total_position']/10000:.1f} 万）  "
        f"每笔买入: 总仓位的 {p['buy_ratio']:.1f}%（{s['tranche']:,.0f} 元/笔）  "
        f"触发条件: 盘中最低价较前收盘跌 ≥{p['dip_pct']:.1f}%")
    log(f"   口径: 触发用盘中最低价（限价单模型），成交价 = 当日最低价（不复权）")
    log(f"   模拟区间（首触日起）: {s['start_date']} 至 {s['end_date']}（{s['trading_days']} 个交易日）")

    log(f"\n2. 触发统计: 共 {len(triggers)} 次买入，累计投入 {s['total_invested']:,.0f} 元"
        f"（占总仓位 {s['total_invested']/p['total_position']*100:.1f}%），"
        f"剩余现金 {s['leftover_cash']:,.0f} 元")

    log(f"\n3. 每笔买入明细:")
    log(f"   {'买入日期':<12}{'前收盘':>9}{'最低价':>9}{'跌幅':>8}{'买入价':>9}"
        f"{'买入金额':>13}{'股数':>8}")
    for t in triggers:
        log(f"   {t['buy_date']:<12}{t['prev_close']:>9.2f}{t['buy_price']:>9.2f}"
            f"{t['drop_pct']:>7.2f}%{t['buy_price']:>9.2f}{t['buy_amount']:>13,.0f}{t['buy_shares']:>8,}")

    log(f"\n4. 策略对比（首触日 至 {s['end_date']}，总仓位 {p['total_position']:,.0f} 元口径）:")
    lines = [
        ("分批买入+红利再投", s["staged_reinvest"]),
        ("首触全仓+红利再投", s["lump_reinvest"]),
        ("首触全仓+分红不投", s["lump_no_reinvest"]),
    ]
    for name, x in lines:
        ann = (f"{x['annual_return_pct']*100:.2f}%" if x["annual_return_pct"] is not None else "N/A")
        log(f"   【{name}】期末总资产: {x['final_asset']:>14,.2f} 元  "
            f"收益率: {x['total_return_pct']:>8.2f}%  年化: {ann}")
        log(f"            期末持股: {x['final_shares']:>10,} 股  "
            f"期末现金: {x['final_cash']:>12,.2f} 元  "
            f"最大回撤: {x['max_drawdown_pct']:.2f}%  累计分红: {x['total_dividends']:>12,.2f} 元")

    st = s["staged_reinvest"]
    lr = s["lump_reinvest"]
    diff = st["final_asset"] - lr["final_asset"]
    log("\n5. 分批 vs 一把梭:")
    log(f"   分批买入比「首触全仓」{'多赚' if diff >= 0 else '少赚'} {abs(diff):,.2f} 元"
        f"（{diff / lr['final_asset'] * 100:+.2f}%）；期间股价涨跌 {s['period_return_pct']:.2f}%")

    # 前复权口径：每笔交易成本按当日前复权价折算
    has_fwd = any(x.get("forward_cost") is not None
                  for x in (s["staged_reinvest"], s["lump_reinvest"], s["lump_no_reinvest"]))
    if has_fwd:
        log("\n6. 前复权口径（成本价前复权）:")
        log("   每笔交易成本按当日前复权价折算（参考前复权K线对应日期），"
            "分红送转已隐含在复权价格中，现金资产另行列示")
        for name, x in lines:
            log(f"   【{name}】前复权成本: {x['forward_cost']:>14,.2f} 元  "
                f"成本均价: {x['forward_cost_avg']:>8.4f} 元/股  "
                f"前复权收益率: {x['forward_return_pct']:>8.2f}%")
        log("\n   每笔交易明细（日期/价格/数量，分批买入线）:")
        trades = st["trades"]
        log(f"   {'交易日期':<12}{'类型':>10}{'成交价':>10}{'数量':>10}{'金额':>14}{'当日前复权价':>14}")
        for t in trades:
            fp = f"{t['fwd_price']:>14.4f}" if t.get("fwd_price") is not None else f"{'—':>14}"
            log(f"   {t['trade_date']:<12}{t['kind']:>10}{t['price']:>10.4f}{t['shares']:>10,}"
                f"{t['amount']:>14,.2f}{fp}")
    else:
        log("\n6. 前复权口径: 未计算（前复权数据缺失或覆盖不全，请先同步前复权行情）")

    if "total_reinvested" in st:
        log("\n7. 红利再投的贡献（分批买入线）:")
        log(f"   累计分红到账: {st['total_dividends']:,.2f} 元，"
            f"其中再投 {st['total_reinvested']:,.2f} 元（{st['reinvest_count']} 次买入）")
        log(f"   比「首触全仓+分红不投」多赚: "
            f"{st['final_asset'] - s['lump_no_reinvest']['final_asset']:,.2f} 元")

    events = result["dividend_events"]
    log("\n8. 分红事件明细（分批买入线口径）:")
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
        log("\n9. 提示:")
        for w in result["warnings"]:
            log(f"   - {w}")

    log("=" * 78)


def make_chart(result: dict, stock_name: str, stock_code: str, saver, show: bool = True):
    """对比图：权益曲线（三线 + 每次买入日/除息日标记）+ 年度分红柱状图"""
    p = result["params"]
    equity_curve = result["equity_curve"]
    events = result["dividend_events"]
    buy_dates = [t["buy_date"] for t in result["triggers"]]

    dates = [e["trade_date"] for e in equity_curve]
    st_assets = [e["staged_asset"] for e in equity_curve]
    lr_assets = [e["lump_re_asset"] for e in equity_curve]
    ln_assets = [e["lump_nr_asset"] for e in equity_curve]

    fig = plt.figure(figsize=(16, 9))

    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(dates, st_assets, label="分批买入+红利再投", color="#cf1322", linewidth=1.6)
    ax1.plot(dates, lr_assets, label="首触全仓+红利再投", color="#1890ff", linewidth=1.2, alpha=0.85)
    ax1.plot(dates, ln_assets, label="首触全仓+分红不投", color="#999999",
             linewidth=1.0, linestyle="--", alpha=0.8)

    # 每次买入日标记（竖线 + 底部三角）
    curve_map = {e["trade_date"]: e["staged_asset"] for e in equity_curve}
    buy_in_curve = [d for d in buy_dates if d in curve_map]
    for i, d in enumerate(buy_in_curve):
        ax1.axvline(d, color="#d4b106", linestyle=":", linewidth=0.6, alpha=0.35)
    if buy_in_curve:
        ymin = min(st_assets) * 0.98
        ax1.scatter(buy_in_curve, [ymin] * len(buy_in_curve), marker="^",
                    color="#d4b106", s=40, zorder=5, label=f"买入日({len(buy_in_curve)})")

    # 除息日标记
    ex_dates = [e["ex_dividend_date"] for e in events if e["ex_dividend_date"] in curve_map]
    if ex_dates:
        ax1.scatter(ex_dates, [curve_map[d] for d in ex_dates], marker="v",
                    color="#52c41a", s=36, zorder=5, label=f"除息日({len(ex_dates)})")

    ax1.set_title(f"{stock_name}({stock_code}) 当日大跌 ≥{p['dip_pct']:.0f}% 按最低价买入"
                  f"总仓位 {p['buy_ratio']:.0f}%/笔（总仓位 {p['total_position']/10000:.0f} 万）"
                  f" + 红利再投 —— 权益曲线对比")
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
        ax2.set_title("年度分红到账金额（元，分批买入线）")
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
    chart_path = saver.save_chart(f"{stock_code}_大跌分批买入.jpg")
    plt.close(fig)
    return chart_path


def main():
    os.chdir(ROOT_DIR)
    args = parse_args()
    stock_code = args.code.strip()

    saver = reset_saver("大跌分批买入")
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
            log("已加载前复权行情（成本前复权口径可用）")
        else:
            log("前复权数据缺失，成本前复权口径不可用（请先同步前复权行情）")

        dividends = ensure_dividends(db, stock_code, args.sync, log)
        log(f"分红明细: {len(dividends)} 笔（仅统计已实施分配）")

        result = simulate_staged_dip_buy(
            quotes=quotes,
            dividends=dividends,
            total_position=args.position * 10000,  # 万元 → 元
            buy_ratio=args.ratio,
            dip_pct=args.dip,
            start_date=args.start,
            end_date=args.end,
            tax_rate=args.tax,
            reinvest=True,
            lot_size=100,
            forward_quotes=forward_quotes,
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
