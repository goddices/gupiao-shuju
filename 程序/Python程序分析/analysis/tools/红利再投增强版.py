# -*- coding: utf-8 -*-
"""
红利再投增强版 —— 大跌买入 + 红利再投，能赚多少？（迁移自旧版独立脚本）

策略: 观察期内股价从（滚动）历史最高点首次回撤 ≥ x% 时，按当日收盘价买入 y 万元，
之后每次分红到账"无脑买入"该股（红利再投），与「分红不投」「纯股价」对比收益率。

回撤检测使用前复权价格（避免送转除权造成假跌破），买入与模拟使用不复权价格。
入口契约见 analysis.tools 包 docstring；与 红利再投/大跌分批买入 共用的
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

ANALYSIS_NAME = "红利再投增强版"
DESCRIPTION = "大跌 x%% 买入 y 万 + 红利再投，对比收益率"


def print_report(result: dict, stock_name: str, stock_code: str, args, log):
    t = result["trigger"]
    s = result["summary"]

    print_header(log, f"{stock_name}({stock_code}) 红利再投增强版报告（大跌买入）", width=76)

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
    print_strategy_compare(log, lines)

    ri = s["reinvest"]
    nr = s["no_reinvest"]
    diff = ri["final_asset"] - nr["final_asset"]
    log("\n5. 红利再投的贡献:")
    print_reinvest_total(log, ri)
    log(f"   红利再投比「分红不投」多赚: {diff:,.2f} 元（+{diff / nr['final_asset'] * 100:.2f}%）")
    log(f"   比「纯股价」多赚: {ri['final_asset'] - s['price_only']['final_asset']:,.2f} 元")

    # 前复权口径：每笔交易成本按当日前复权价折算
    print_forward_section(log, 6, lines, ri["trades"], "红利再投线")

    print_events_and_warnings(log, 7, "分红事件明细",
                              result["dividend_events"], "（买入后无分红记录）",
                              result["warnings"])

    print_footer(log, 76)


def make_chart(result: dict, stock_name: str, stock_code: str, saver, show: bool = True):
    """对比图：权益曲线（三线 + 买入日/除息日标记）+ 年度分红柱状图（骨架见 _reinvest_common）"""
    t = result["trigger"]

    def mark_buy_date(ax1, dates, curve_map):
        """买入日标记（竖虚线 + 注释）"""
        ax1.axvline(t["buy_date"], color=EQUITY_COLORS["marker"], linestyle="--", linewidth=1.2, alpha=0.8)
        ax1.annotate(f"买入日 {t['buy_date']}\n@{t['buy_price']:.2f} 元",
                     xy=(t["buy_date"], curve_map[dates[0]]),
                     xytext=(len(dates) * 0.45, curve_map[dates[0]] * 0.92),
                     fontsize=9, color="#ad6800",
                     arrowprops=dict(arrowstyle="->", color="#ad6800"))

    return make_compare_chart(
        saver, stock_name, stock_code, result["equity_curve"],
        series=[
            ("红利再投", "reinvest_asset"),
            ("分红不投", "no_reinvest_asset"),
            ("纯股价", "price_only_asset"),
        ],
        events=result["dividend_events"],
        title=f"{stock_name}({stock_code}) 大跌 {t['dip_pct']:.0f}% 买入 {t['buy_amount']/10000:.0f} 万 + 红利再投"
              f" —— 权益曲线对比（不复权）",
        chart_filename=f"{stock_code}_红利再投增强版.jpg",
        decorate=mark_buy_date,
        bar_empty="买入后无分红记录",
        show=show,
    )


def add_parser(sub):
    """注册子命令（--code/--start/--end/--dip/--amount/--tax/--sync/--no-chart）"""
    p = sub.add_parser(ANALYSIS_NAME, help=DESCRIPTION,
                       parents=[
                           code_parent(),
                           range_parent(start_help="观察起点 YYYY-MM-DD（默认：数据最早）",
                                        end_help="观察终点 YYYY-MM-DD（默认：数据最晚）"),
                           db_common_parent(),
                       ])
    p.add_argument("--dip", type=float, default=20.0,
                   help="回撤买入幅度 %%（默认 20 = 从高点跌 20%% 买入）")
    p.add_argument("--amount", type=float, default=10.0,
                   help="买入金额，万元（默认 10 万）")
    p.set_defaults(_run=run)
    return p


def interactive_input(saver):
    """菜单路径的交互输入"""
    stock_code, start_date, end_date = ask_base_inputs(
        "观察起点（默认：数据最早）", "观察终点（默认：数据最晚）")
    dip = ask("请输入回撤买入幅度 %（默认：20）: ", 20.0, float)
    amount = ask("请输入买入金额，万元（默认：10 万）: ", 10.0, float)
    tax = ask_tax()
    return argparse.Namespace(code=stock_code, start=start_date or None,
                              end=end_date or None, dip=dip, amount=amount,
                              tax=tax, sync=False, no_chart=False)


def _invoke(db, stock_code, args, log):
    return run_dip_buy(
        db, stock_code, dip_pct=args.dip,
        buy_amount=args.amount * 10000,  # 万元 → 元
        start_date=args.start, end_date=args.end, tax_rate=args.tax,
        reinvest=True, lot_size=100, sync=args.sync, log=log,
    )


def run(args, saver=None):
    """执行分析（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)，骨架见 _reinvest_common）"""
    return run_tool(args, ANALYSIS_NAME, "行情", _invoke,
                    print_report, make_chart, saver=saver)
