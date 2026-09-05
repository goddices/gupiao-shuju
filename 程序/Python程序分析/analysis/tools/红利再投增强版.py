# -*- coding: utf-8 -*-
"""
红利再投增强版 —— 大跌买入 + 红利再投，能赚多少？（迁移自旧版独立脚本）

策略: 观察期内股价从（滚动）历史最高点首次回撤 ≥ x% 时，按当日收盘价买入 y 万元，
之后每次分红到账"无脑买入"该股（红利再投），与「分红不投」「纯股价」对比收益率。

回撤检测使用前复权价格（避免送转除权造成假跌破），买入与模拟使用不复权价格。
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

ANALYSIS_NAME = "红利再投增强版"
DESCRIPTION = "大跌 x%% 买入 y 万 + 红利再投，对比收益率"


def print_report(result: dict, stock_name: str, stock_code: str, log):
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

    ri = s["reinvest"]
    nr = s["no_reinvest"]
    diff = ri["final_asset"] - nr["final_asset"]
    log("\n5. 红利再投的贡献:")
    log(f"   累计分红到账: {ri['total_dividends']:,.2f} 元，"
        f"其中再投 {ri['total_reinvested']:,.2f} 元（{ri['reinvest_count']} 次买入）")
    log(f"   红利再投比「分红不投」多赚: {diff:,.2f} 元（+{diff / nr['final_asset'] * 100:.2f}%）")
    log(f"   比「纯股价」多赚: {ri['final_asset'] - s['price_only']['final_asset']:,.2f} 元")

    # 前复权口径：每笔交易成本按当日前复权价折算
    has_fwd = any(x.get("forward_cost") is not None
                  for x in (s["reinvest"], s["no_reinvest"], s["price_only"]))
    if has_fwd:
        log("\n6. 前复权口径（成本价前复权）:")
        print_forward_block(log, lines, ri["trades"], "红利再投线")
    else:
        log("\n6. 前复权口径: 未计算（前复权数据缺失或覆盖不全，请先同步前复权行情）")

    events = result["dividend_events"]
    log("\n7. 分红事件明细:")
    print_dividend_table(log, events, "（买入后无分红记录）")

    if result["warnings"]:
        log("\n8. 提示:")
        print_warnings(log, result["warnings"])

    print_footer(log, 76)


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
    plot_equity_lines(ax1, dates, [
        ("红利再投", re_assets, {"color": EQUITY_COLORS["primary"], "linewidth": 1.6}),
        ("分红不投", nr_assets, {"color": EQUITY_COLORS["secondary"], "linewidth": 1.2, "alpha": 0.85}),
        ("纯股价", po_assets, {"color": EQUITY_COLORS["baseline"], "linewidth": 1.0, "linestyle": "--", "alpha": 0.8}),
    ])

    # 买入日标记
    ax1.axvline(t["buy_date"], color=EQUITY_COLORS["marker"], linestyle="--", linewidth=1.2, alpha=0.8)
    ax1.annotate(f"买入日 {t['buy_date']}\n@{t['buy_price']:.2f} 元",
                 xy=(t["buy_date"], re_assets[0]), xytext=(len(dates) * 0.45, re_assets[0] * 0.92),
                 fontsize=9, color="#ad6800",
                 arrowprops=dict(arrowstyle="->", color="#ad6800"))

    # 除息日标记（只标有行情的除息日）
    curve_map = {e["trade_date"]: e["reinvest_asset"] for e in equity_curve}
    mark_ex_dividend_dates(ax1, curve_map, events)

    ax1.set_title(f"{stock_name}({stock_code}) 大跌 {t['dip_pct']:.0f}% 买入 {t['buy_amount']/10000:.0f} 万 + 红利再投"
                  f" —— 权益曲线对比（不复权）")
    ax1.set_ylabel("总资产（元）")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    set_date_ticks(ax1, dates)

    # 年度分红柱状图
    ax2 = plt.subplot(2, 1, 2)
    draw_year_dividend_bar(ax2, events, empty_text="买入后无分红记录")

    plt.tight_layout()
    if show:
        plt.show()
    chart_path = saver.save_chart(f"{stock_code}_红利再投增强版.jpg")
    plt.close(fig)
    return chart_path


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
    stock_code = ask("请输入股票代码（默认：601857）: ", "601857")
    start_date = ask("请输入观察起点（默认：数据最早）: ", "")
    end_date = ask("请输入观察终点（默认：数据最晚）: ", "")
    dip = ask("请输入回撤买入幅度 %（默认：20）: ", 20.0, float)
    amount = ask("请输入买入金额，万元（默认：10 万）: ", 10.0, float)
    tax = ask("请输入分红税率 0~1（默认：0 = 长期持有免税）: ", 0.0, float)
    return argparse.Namespace(code=stock_code, start=start_date or None,
                              end=end_date or None, dip=dip, amount=amount,
                              tax=tax, sync=False, no_chart=False)


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
            db, stock_code, dip_pct=args.dip,
            buy_amount=args.amount * 10000,  # 万元 → 元
            start_date=args.start, end_date=args.end, tax_rate=args.tax,
            reinvest=True, lot_size=100, sync=args.sync, log=log,
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
