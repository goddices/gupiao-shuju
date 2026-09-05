# -*- coding: utf-8 -*-
"""
大跌分批买入 + 红利再投 —— 当天大跌 x% 就在最低价买一笔，能赚多少？（迁移自旧版独立脚本）

策略: 每个交易日若盘中最低价较前收盘跌幅 ≥ x%（当天大跌），按当日最低价买入
一笔，金额 = 总仓位 × y%（每次触发买一笔，直至现金用完），此后分红到账
"无脑买入"该股（红利再投）。

对比基准:
    staged_reinvest   分批买入 + 红利再投（本策略）
    lump_reinvest     首个触发日一次性全仓买入 + 红利再投
    lump_no_reinvest  首个触发日一次性全仓买入 + 分红不投

口径说明: 触发条件用盘中最低价（相当于挂"前收盘 -x%"的限价单，盘中跌破即成交），
成交价 = 当日最低价；买入与模拟均用不复权价格。
入口契约见 analysis.tools 包 docstring。
"""
import argparse

import matplotlib.pyplot as plt

from analysis.chart_utils import (
    setup_chinese_fonts, EQUITY_COLORS, plot_equity_lines, set_date_ticks,
    mark_ex_dividend_dates, draw_year_dividend_bar,
)
from analysis.cli import ask, code_parent, db_common_parent, range_parent
from analysis.report import (
    print_header, print_footer, print_compare_rows, print_forward_block,
    print_dividend_table, print_warnings,
)
from backend.database import SessionLocal, engine
from backend.models import Base
from backend.services import get_stock_name
from result_saver import reset_saver
from simulation.strategy_runners import run_dip_buy

setup_chinese_fonts()

ANALYSIS_NAME = "大跌分批买入"
DESCRIPTION = "当天大跌 x%% 按最低价买入总仓位 y%% 一笔 + 红利再投"


def print_report(result: dict, stock_name: str, stock_code: str, log):
    p = result["params"]
    s = result["summary"]
    triggers = result["triggers"]

    print_header(log, f"{stock_name}({stock_code}) 大跌分批买入 + 红利再投 报告", width=78)

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
    rows = [
        {
            "name": name,
            "line1": [
                f"期末总资产: {x['final_asset']:>14,.2f} 元",
                f"收益率: {x['total_return_pct']:>8.2f}%",
                f"年化: {(f'{x['annual_return_pct']*100:.2f}%' if x['annual_return_pct'] is not None else 'N/A')}",
            ],
            "line2": [
                f"期末持股: {x['final_shares']:>10,} 股",
                f"期末现金: {x['final_cash']:>12,.2f} 元",
                f"最大回撤: {x['max_drawdown_pct']:.2f}%",
                f"累计分红: {x['total_dividends']:>12,.2f} 元",
            ],
        }
        for name, x in lines
    ]
    print_compare_rows(log, rows)

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
        print_forward_block(log, lines, st["trades"], "分批买入线")
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
    print_dividend_table(log, events, "（买入后无分红记录）")

    if result["warnings"]:
        log("\n9. 提示:")
        print_warnings(log, result["warnings"])

    print_footer(log, 78)


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
    plot_equity_lines(ax1, dates, [
        ("分批买入+红利再投", st_assets, {"color": EQUITY_COLORS["primary"], "linewidth": 1.6}),
        ("首触全仓+红利再投", lr_assets, {"color": EQUITY_COLORS["secondary"], "linewidth": 1.2, "alpha": 0.85}),
        ("首触全仓+分红不投", ln_assets, {"color": EQUITY_COLORS["baseline"], "linewidth": 1.0, "linestyle": "--", "alpha": 0.8}),
    ])

    # 每次买入日标记（竖线 + 底部三角）
    curve_map = {e["trade_date"]: e["staged_asset"] for e in equity_curve}
    buy_in_curve = [d for d in buy_dates if d in curve_map]
    for d in buy_in_curve:
        ax1.axvline(d, color=EQUITY_COLORS["marker"], linestyle=":", linewidth=0.6, alpha=0.35)
    if buy_in_curve:
        ymin = min(st_assets) * 0.98
        ax1.scatter(buy_in_curve, [ymin] * len(buy_in_curve), marker="^",
                    color=EQUITY_COLORS["marker"], s=40, zorder=5, label=f"买入日({len(buy_in_curve)})")

    # 除息日标记
    mark_ex_dividend_dates(ax1, curve_map, events, color="#52c41a")

    ax1.set_title(f"{stock_name}({stock_code}) 当日大跌 ≥{p['dip_pct']:.0f}% 按最低价买入"
                  f"总仓位 {p['buy_ratio']:.0f}%/笔（总仓位 {p['total_position']/10000:.0f} 万）"
                  f" + 红利再投 —— 权益曲线对比")
    ax1.set_ylabel("总资产（元）")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    set_date_ticks(ax1, dates)

    # 年度分红柱状图
    ax2 = plt.subplot(2, 1, 2)
    draw_year_dividend_bar(ax2, events, title="年度分红到账金额（元，分批买入线）",
                           empty_text="买入后无分红记录")

    plt.tight_layout()
    if show:
        plt.show()
    chart_path = saver.save_chart(f"{stock_code}_大跌分批买入.jpg")
    plt.close(fig)
    return chart_path


def add_parser(sub):
    """注册子命令（--code/--start/--end/--position/--ratio/--dip/--tax/--sync/--no-chart）"""
    p = sub.add_parser(ANALYSIS_NAME, help=DESCRIPTION,
                       parents=[
                           code_parent(),
                           range_parent(start_help="观察起点 YYYY-MM-DD（默认：数据最早）",
                                        end_help="观察终点 YYYY-MM-DD（默认：数据最晚）"),
                           db_common_parent(),
                       ])
    p.add_argument("--position", type=float, default=100.0,
                   help="总仓位，万元（默认 100 万）")
    p.add_argument("--ratio", type=float, default=5.0,
                   help="每笔买入占总仓位比例 %%（默认 5 = 每次买总仓位的 5%%）")
    p.add_argument("--dip", type=float, default=3.0,
                   help="当日大跌阈值 %%（默认 3 = 盘中最低价较前收盘跌 3%% 触发）")
    p.set_defaults(_run=run)
    return p


def interactive_input(saver):
    """菜单路径的交互输入"""
    stock_code = ask("请输入股票代码（默认：601857）: ", "601857")
    start_date = ask("请输入观察起点（默认：数据最早）: ", "")
    end_date = ask("请输入观察终点（默认：数据最晚）: ", "")
    position = ask("请输入总仓位，万元（默认：100 万）: ", 100.0, float)
    ratio = ask("请输入每笔买入占总仓位比例 %（默认：5）: ", 5.0, float)
    dip = ask("请输入当日大跌阈值 %（默认：3）: ", 3.0, float)
    tax = ask("请输入分红税率 0~1（默认：0 = 长期持有免税）: ", 0.0, float)
    return argparse.Namespace(code=stock_code, start=start_date or None,
                              end=end_date or None, position=position, ratio=ratio,
                              dip=dip, tax=tax, sync=False, no_chart=False)


def run(args, saver=None):
    """执行分析（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)）"""
    if saver is None:
        saver = reset_saver(ANALYSIS_NAME)
    stock_code = args.code.strip()

    saver.set_tag(stock_code)
    log = saver.log

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stock_name = get_stock_name(db, stock_code) or stock_code
        log(f"正在读取 {stock_name}({stock_code}) 的行情...")
        result = run_dip_buy(
            db, stock_code, dip_pct=args.dip, buy_amount=None,
            start_date=args.start, end_date=args.end, tax_rate=args.tax,
            reinvest=True, lot_size=100, strategy="daily_drop",
            total_position=args.position * 10000,  # 万元 → 元
            buy_ratio=args.ratio, sync=args.sync, log=log,
        )

        if result["status"] != "ok":
            if result["status"] != "no_data":
                log(f"模拟失败: {result.get('message', '未知错误')}")
            saver.finalize()
            return 0

        print_report(result, stock_name, stock_code, log)
        make_chart(result, stock_name, stock_code, saver, show=not args.no_chart)
    finally:
        db.close()

    saver.finalize()
    return 0
