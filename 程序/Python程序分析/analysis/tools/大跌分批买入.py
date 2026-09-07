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
入口契约见 analysis.tools 包 docstring；与 红利再投/红利再投增强版 共用的
报告节、图表骨架与 run 骨架见 analysis.tools._reinvest_common。
"""
import argparse

from analysis.chart_utils import setup_chinese_fonts, EQUITY_COLORS
from analysis.cli import ask, code_parent, db_common_parent, range_parent
from analysis.report import print_header, print_footer
from analysis.tools._reinvest_common import (
    print_strategy_compare, print_reinvest_total, print_forward_section,
    print_events_and_warnings, make_compare_chart,
    ask_base_inputs, ask_tax, run_tool,
)
from simulation.strategy_runners import run_dip_buy

setup_chinese_fonts()

ANALYSIS_NAME = "大跌分批买入"
DESCRIPTION = "当天大跌 x%% 按最低价买入总仓位 y%% 一笔 + 红利再投"


def print_report(result: dict, stock_name: str, stock_code: str, args, log):
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
    print_strategy_compare(log, lines)

    st = s["staged_reinvest"]
    lr = s["lump_reinvest"]
    diff = st["final_asset"] - lr["final_asset"]
    log("\n5. 分批 vs 一把梭:")
    log(f"   分批买入比「首触全仓」{'多赚' if diff >= 0 else '少赚'} {abs(diff):,.2f} 元"
        f"（{diff / lr['final_asset'] * 100:+.2f}%）；期间股价涨跌 {s['period_return_pct']:.2f}%")

    # 前复权口径：每笔交易成本按当日前复权价折算
    print_forward_section(log, 6, lines, st["trades"], "分批买入线")

    if "total_reinvested" in st:
        log("\n7. 红利再投的贡献（分批买入线）:")
        print_reinvest_total(log, st)
        log(f"   比「首触全仓+分红不投」多赚: "
            f"{st['final_asset'] - s['lump_no_reinvest']['final_asset']:,.2f} 元")

    print_events_and_warnings(log, 8, "分红事件明细（分批买入线口径）",
                              result["dividend_events"], "（买入后无分红记录）",
                              result["warnings"])

    print_footer(log, 78)


def make_chart(result: dict, stock_name: str, stock_code: str, saver, show: bool = True):
    """对比图：权益曲线（三线 + 每次买入日/除息日标记）+ 年度分红柱状图（骨架见 _reinvest_common）"""
    p = result["params"]
    buy_dates = [t["buy_date"] for t in result["triggers"]]

    def mark_buy_dates(ax1, dates, curve_map):
        """每次买入日标记（竖线 + 底部三角）"""
        buy_in_curve = [d for d in buy_dates if d in curve_map]
        for d in buy_in_curve:
            ax1.axvline(d, color=EQUITY_COLORS["marker"], linestyle=":", linewidth=0.6, alpha=0.35)
        if buy_in_curve:
            ymin = min(curve_map.values()) * 0.98
            ax1.scatter(buy_in_curve, [ymin] * len(buy_in_curve), marker="^",
                        color=EQUITY_COLORS["marker"], s=40, zorder=5, label=f"买入日({len(buy_in_curve)})")

    return make_compare_chart(
        saver, stock_name, stock_code, result["equity_curve"],
        series=[
            ("分批买入+红利再投", "staged_asset"),
            ("首触全仓+红利再投", "lump_re_asset"),
            ("首触全仓+分红不投", "lump_nr_asset"),
        ],
        events=result["dividend_events"],
        title=f"{stock_name}({stock_code}) 当日大跌 ≥{p['dip_pct']:.0f}% 按最低价买入"
              f"总仓位 {p['buy_ratio']:.0f}%/笔（总仓位 {p['total_position']/10000:.0f} 万）"
              f" + 红利再投 —— 权益曲线对比",
        chart_filename=f"{stock_code}_大跌分批买入.jpg",
        ex_color="#52c41a",
        decorate=mark_buy_dates,
        bar_title="年度分红到账金额（元，分批买入线）",
        bar_empty="买入后无分红记录",
        show=show,
    )


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
    stock_code, start_date, end_date = ask_base_inputs(
        "观察起点（默认：数据最早）", "观察终点（默认：数据最晚）")
    position = ask("请输入总仓位，万元（默认：100 万）: ", 100.0, float)
    ratio = ask("请输入每笔买入占总仓位比例 %（默认：5）: ", 5.0, float)
    dip = ask("请输入当日大跌阈值 %（默认：3）: ", 3.0, float)
    tax = ask_tax()
    return argparse.Namespace(code=stock_code, start=start_date or None,
                              end=end_date or None, position=position, ratio=ratio,
                              dip=dip, tax=tax, sync=False, no_chart=False)


def _invoke(db, stock_code, args, log):
    return run_dip_buy(
        db, stock_code, dip_pct=args.dip, buy_amount=None,
        start_date=args.start, end_date=args.end, tax_rate=args.tax,
        reinvest=True, lot_size=100, strategy="daily_drop",
        total_position=args.position * 10000,  # 万元 → 元
        buy_ratio=args.ratio, sync=args.sync, log=log,
    )


def run(args, saver=None):
    """执行分析（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)，骨架见 _reinvest_common）"""
    return run_tool(args, ANALYSIS_NAME, "行情", _invoke,
                    print_report, make_chart, saver=saver)
