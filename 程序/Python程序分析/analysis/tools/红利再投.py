# -*- coding: utf-8 -*-
"""
红利再投模拟 —— 个股长期红利再投可以赚多少？（迁移自旧版独立脚本）

用不复权价格模拟: 期初全仓买入 → 每次分红到账后按除息日收盘价"无脑买入"该股，
并与"分红不投(现金留存)"、"纯股价"两个基准对比。

数据来源: MySQL stock_daily_quote(不复权收盘价) + stock_dividend_detail(东财分红明细)。
入口契约见 analysis.tools 包 docstring；与 红利再投增强版/大跌分批买入 共用的
报告节、图表骨架与 run 骨架见 analysis.tools._reinvest_common。
"""
import argparse
import warnings as py_warnings

py_warnings.filterwarnings("ignore")

from analysis.chart_utils import setup_chinese_fonts
from analysis.cli import ask, code_parent, db_common_parent, range_parent
from analysis.report import print_header, print_footer
from analysis.tools._reinvest_common import (
    print_strategy_compare, print_reinvest_total, print_forward_section,
    print_events_and_warnings, make_compare_chart,
    ask_base_inputs, ask_tax, run_tool,
)
from simulation.strategy_runners import run_dividend_reinvest

setup_chinese_fonts()

ANALYSIS_NAME = "红利再投"
DESCRIPTION = "个股长期红利再投收益模拟（不复权 + 分红无脑再投）"


def print_report(result: dict, stock_name: str, stock_code: str, args, log):
    summary = result["summary"]
    print_header(log, f"{stock_name}({stock_code}) 红利再投模拟报告", width=76, extra=[
        f"        期间: {summary['start_date']} 至 {summary['end_date']} "
        f"（{summary['trading_days']} 个交易日）",
    ])

    log("\n1. 区间行情概览（不复权）:")
    log(f"   期初收盘: {summary['first_close']:.2f}   期末收盘: {summary['last_close']:.2f}   "
        f"区间涨跌幅: {summary['period_return_pct']:.2f}%")

    log(f"\n2. 三策略对比（初始资金 {args.capital:,.0f} 元，分红税率 {args.tax*100:.0f}%）:")
    lines = [
        ("红利再投", summary["reinvest"]),
        ("分红不投", summary["no_reinvest"]),
        ("纯股价  ", summary["price_only"]),
    ]
    print_strategy_compare(log, lines)

    ri = summary["reinvest"]
    nr = summary["no_reinvest"]
    diff = ri["final_asset"] - nr["final_asset"]
    log("\n3. 红利再投的贡献:")
    print_reinvest_total(log, ri)
    log(f"   红利再投比「分红不投」多赚: {diff:,.2f} 元 "
        f"（+{diff / nr['final_asset'] * 100:.2f}%）")
    log(f"   比「纯股价」多赚: {ri['final_asset'] - summary['price_only']['final_asset']:,.2f} 元")

    # 前复权口径：每笔交易成本按当日前复权价折算
    print_forward_section(log, 4, lines, ri["trades"], "红利再投线")

    print_events_and_warnings(log, 5, "分红事件明细",
                              result["dividend_events"], "（区间内无分红记录）",
                              result["warnings"])

    print_footer(log, 76)


def make_chart(result: dict, stock_name: str, stock_code: str, saver, show: bool = True):
    """生成对比图：权益曲线（三线 + 除息日标记）+ 年度分红柱状图（骨架见 _reinvest_common）"""
    return make_compare_chart(
        saver, stock_name, stock_code, result["equity_curve"],
        series=[
            ("红利再投", "reinvest_asset"),
            ("分红不投", "no_reinvest_asset"),
            ("纯股价", "price_only_asset"),
        ],
        events=result["dividend_events"],
        title=f"{stock_name}({stock_code}) 红利再投模拟 —— 权益曲线对比（不复权）",
        chart_filename=f"{stock_code}_红利再投.jpg",
        show=show,
    )


def add_parser(sub):
    """注册子命令（--code/--start/--end/--capital/--tax/--sync/--no-chart）"""
    p = sub.add_parser(ANALYSIS_NAME, help=DESCRIPTION,
                       parents=[code_parent(), range_parent(), db_common_parent()])
    p.add_argument("--capital", type=float, default=100000, help="初始资金（默认 100000）")
    p.set_defaults(_run=run)
    return p


def interactive_input(saver):
    """菜单路径的交互输入"""
    stock_code, start_date, end_date = ask_base_inputs(
        "起始日期（默认：最早有数据）", "结束日期（默认：最新有数据）")
    capital = ask("请输入初始资金（默认：100000）: ", 100000.0, float)
    tax = ask_tax()
    return argparse.Namespace(code=stock_code, start=start_date or None,
                              end=end_date or None, capital=capital,
                              tax=tax, sync=False, no_chart=False)


def _invoke(db, stock_code, args, log):
    return run_dividend_reinvest(
        db, stock_code, start_date=args.start, end_date=args.end,
        initial_cash=args.capital, tax_rate=args.tax,
        reinvest=True, lot_size=100, sync=args.sync, log=log,
    )


def run(args, saver=None):
    """执行分析（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)，骨架见 _reinvest_common）"""
    return run_tool(args, ANALYSIS_NAME, "不复权行情", _invoke,
                    print_report, make_chart, saver=saver)
