# -*- coding: utf-8 -*-
"""
红利再投模拟 —— 个股长期红利再投可以赚多少？（迁移自旧版独立脚本）

用不复权价格模拟: 期初全仓买入 → 每次分红到账后按除息日收盘价"无脑买入"该股，
并与"分红不投(现金留存)"、"纯股价"两个基准对比。

数据来源: MySQL stock_daily_quote(不复权收盘价) + stock_dividend_detail(东财分红明细)。
入口契约见 analysis.tools 包 docstring。
"""
import argparse
import warnings as py_warnings

py_warnings.filterwarnings("ignore")

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
from simulation.strategy_runners import run_dividend_reinvest

setup_chinese_fonts()

ANALYSIS_NAME = "红利再投"
DESCRIPTION = "个股长期红利再投收益模拟（不复权 + 分红无脑再投）"


def print_report(summary: dict, events: list, warnings_list: list, stock_name: str,
                 stock_code: str, initial_cash: float, tax_rate: float, log):
    print_header(log, f"{stock_name}({stock_code}) 红利再投模拟报告", width=76, extra=[
        f"        期间: {summary['start_date']} 至 {summary['end_date']} "
        f"（{summary['trading_days']} 个交易日）",
    ])

    log("\n1. 区间行情概览（不复权）:")
    log(f"   期初收盘: {summary['first_close']:.2f}   期末收盘: {summary['last_close']:.2f}   "
        f"区间涨跌幅: {summary['period_return_pct']:.2f}%")

    log(f"\n2. 三策略对比（初始资金 {initial_cash:,.0f} 元，分红税率 {tax_rate*100:.0f}%）:")
    lines = [
        ("红利再投", summary["reinvest"]),
        ("分红不投", summary["no_reinvest"]),
        ("纯股价  ", summary["price_only"]),
    ]
    rows = [
        {
            "name": name,
            "line1": [
                f"期末总资产: {s['final_asset']:>14,.2f} 元",
                f"收益率: {s['total_return_pct']:>8.2f}%",
                f"年化: {(str(round(s['annual_return_pct']*100, 2)) + '%') if s['annual_return_pct'] is not None else 'N/A'}",
            ],
            "line2": [
                f"期末持股: {s['final_shares']:>10,} 股",
                f"期末现金: {s['final_cash']:>12,.2f} 元",
                f"最大回撤: {s['max_drawdown_pct']:.2f}%",
                f"累计分红: {s['total_dividends']:>12,.2f} 元",
            ],
        }
        for name, s in lines
    ]
    print_compare_rows(log, rows)

    ri = summary["reinvest"]
    nr = summary["no_reinvest"]
    diff = ri["final_asset"] - nr["final_asset"]
    log("\n3. 红利再投的贡献:")
    log(f"   累计分红到账: {ri['total_dividends']:,.2f} 元，"
        f"其中再投 {ri['total_reinvested']:,.2f} 元（{ri['reinvest_count']} 次买入）")
    log(f"   红利再投比「分红不投」多赚: {diff:,.2f} 元 "
        f"（+{diff / nr['final_asset'] * 100:.2f}%）")
    log(f"   比「纯股价」多赚: {ri['final_asset'] - summary['price_only']['final_asset']:,.2f} 元")

    # 前复权口径：每笔交易成本按当日前复权价折算
    has_fwd = any(x.get("forward_cost") is not None
                  for x in (summary["reinvest"], summary["no_reinvest"], summary["price_only"]))
    if has_fwd:
        log("\n4. 前复权口径（成本价前复权）:")
        print_forward_block(log, lines, ri["trades"], "红利再投线")
    else:
        log("\n4. 前复权口径: 未计算（前复权数据缺失或覆盖不全，请先同步前复权行情）")

    log("\n5. 分红事件明细:")
    print_dividend_table(log, events, "（区间内无分红记录）")

    if warnings_list:
        log("\n6. 提示:")
        print_warnings(log, warnings_list)

    print_footer(log, 76)


def make_chart(equity_curve: list, events: list, summary: dict,
               stock_name: str, stock_code: str, saver, show: bool = True):
    """生成对比图：权益曲线（三线 + 除息日标记）+ 年度分红柱状图（pyplot 绘制，show=True 时弹窗显示）"""
    dates = [e["trade_date"] for e in equity_curve]
    re_assets = [e["reinvest_asset"] for e in equity_curve]
    nr_assets = [e["no_reinvest_asset"] for e in equity_curve]
    po_assets = [e["price_only_asset"] for e in equity_curve]

    fig = plt.figure(figsize=(16, 9))

    ax1 = plt.subplot(2, 1, 1)
    plot_equity_lines(ax1, dates, [
        ("红利再投", re_assets, {"color": EQUITY_COLORS["primary"], "linewidth": 1.6}),
        ("分红不投", nr_assets, {"color": EQUITY_COLORS["secondary"], "linewidth": 1.2, "alpha": 0.85}),
        ("纯股价", po_assets, {"color": EQUITY_COLORS["baseline"], "linewidth": 1.0, "linestyle": "--", "alpha": 0.8}),
    ])

    # 除息日标记（只标有行情的除息日）
    curve_map = {e["trade_date"]: e["reinvest_asset"] for e in equity_curve}
    mark_ex_dividend_dates(ax1, curve_map, events)

    ax1.set_title(f"{stock_name}({stock_code}) 红利再投模拟 —— 权益曲线对比（不复权）")
    ax1.set_ylabel("总资产（元）")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    set_date_ticks(ax1, dates)

    # 年度分红柱状图
    ax2 = plt.subplot(2, 1, 2)
    draw_year_dividend_bar(ax2, events)

    plt.tight_layout()
    if show:
        plt.show()  # 弹窗显示（关闭窗口后继续）
    chart_path = saver.save_chart(f"{stock_code}_红利再投.jpg")
    plt.close(fig)
    return chart_path


def add_parser(sub):
    """注册子命令（--code/--start/--end/--capital/--tax/--sync/--no-chart）"""
    p = sub.add_parser(ANALYSIS_NAME, help=DESCRIPTION,
                       parents=[code_parent(), range_parent(), db_common_parent()])
    p.add_argument("--capital", type=float, default=100000, help="初始资金（默认 100000）")
    p.set_defaults(_run=run)
    return p


def interactive_input(saver):
    """菜单路径的交互输入"""
    stock_code = ask("请输入股票代码（默认：601857）: ", "601857")
    start_date = ask("请输入起始日期（默认：最早有数据）: ", "")
    end_date = ask("请输入结束日期（默认：最新有数据）: ", "")
    capital = ask("请输入初始资金（默认：100000）: ", 100000.0, float)
    tax = ask("请输入分红税率 0~1（默认：0 = 长期持有免税）: ", 0.0, float)
    return argparse.Namespace(code=stock_code, start=start_date or None,
                              end=end_date or None, capital=capital,
                              tax=tax, sync=False, no_chart=False)


def run(args, saver=None):
    """执行分析（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)）"""
    if saver is None:
        saver = reset_saver(ANALYSIS_NAME)
    stock_code = args.code.strip()

    saver.set_tag(stock_code)
    log = saver.log

    # 建表（幂等）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stock_name = get_stock_name(db, stock_code) or stock_code
        log(f"正在读取 {stock_name}({stock_code}) 的不复权行情...")
        result = run_dividend_reinvest(
            db, stock_code, start_date=args.start, end_date=args.end,
            initial_cash=args.capital, tax_rate=args.tax,
            reinvest=True, lot_size=100, sync=args.sync, log=log,
        )

        if result["status"] != "ok":
            if result["status"] != "no_data":
                log(f"模拟失败: {result.get('message', '未知错误')}")
            saver.finalize()
            return 0

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
    return 0
