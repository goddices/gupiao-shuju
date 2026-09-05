# -*- coding: utf-8 -*-
"""
分红目标测算 —— 目标每年分红到账 X 元，需要在买入日投入多少钱？（迁移自旧版独立脚本）

给定目标年分红(如 20 万/年)和买入日期，按分红基准(去年全年 / 最近12个月)推算
每股年分红，分别计算两种策略所需的最小买入资金：
  1) 红利再投: 买入后每次分红到账"无脑买入"该股，持股越滚越多，期初可以少买；
  2) 分红不投: 分红现金留存，持股不变，需要一次买足目标股数。

数据来源: MySQL stock_daily_quote(不复权收盘价) + stock_dividend_detail(东财分红明细)。
入口契约见 analysis.tools 包 docstring。
"""
import argparse

import matplotlib.pyplot as plt

from analysis.chart_utils import setup_chinese_fonts
from analysis.cli import ask, code_parent, db_common_parent
from analysis.report import print_footer, print_header, wan
from backend.database import SessionLocal, engine
from backend.models import Base
from backend.services import get_stock_name
from result_saver import reset_saver
from simulation.strategy_runners import plan_target

setup_chinese_fonts()

ANALYSIS_NAME = "分红目标测算"
DESCRIPTION = "目标每年分红到账金额反推需投入本金"


def print_report(summary: dict, stock_name: str, stock_code: str, log):
    ref = summary["reference"]
    nr = summary["no_reinvest"]
    ri = summary["reinvest"]

    print_header(log, f"{stock_name}({stock_code}) 分红目标测算报告", width=76)

    log(f"\n1. 买入计划:")
    log(f"   指定买入日期: {summary['buy_date']}（非交易日顺延）")
    log(f"   实际买入日期: {summary['actual_buy_date']}  买入价(不复权收盘): {summary['buy_price']:.2f} 元")

    log(f"\n2. 分红基准（{ref['label']}）:")
    log(f"   共 {ref['dividend_count']} 笔分红，合计 {ref['d_per_share']*10:.4f} 元/10股"
        f" = {ref['d_per_share']:.4f} 元/股（税前）")
    log(f"   税率 {summary['tax_rate']*100:.0f}% 后: {ref['d_net_per_share']:.4f} 元/股")

    log(f"\n3. 目标:")
    log(f"   每年分红到账 {summary['target_annual_dividend']:,.0f} 元"
        f" → 需要持有 {summary['target_shares']:,} 股")

    log("\n4. 两种策略对比:")
    log(f"   【分红不投】一次买足: {nr['required_shares']:,} 股 × {summary['buy_price']:.2f} 元"
        f" = 买入资金 {wan(nr['required_amount'])}（{nr['required_amount']:,.0f} 元）")
    log(f"              → 每年分红到账 {nr['actual_annual_dividend']:,.2f} 元")
    if ri is not None:
        log(f"   【红利再投】期初只需: {ri['required_shares']:,} 股 × {summary['buy_price']:.2f} 元"
            f" = 买入资金 {wan(ri['required_amount'])}（{ri['required_amount']:,.0f} 元）")
        log(f"              → 买入后每次分红无脑再买，共再投 {ri['reinvest_count']} 次"
            f" / {wan(ri['total_reinvested'])}（{ri['total_reinvested']:,.0f} 元）")
        log(f"              → 现在持股 {ri['final_shares']:,} 股，每年分红到账 {ri['actual_annual_dividend']:,.2f} 元")
        log(f"              → 期间累计分红到账 {wan(ri['total_dividends_received'])}")
        log(f"\n   红利再投比「分红不投」少花: {wan(summary['saving_amount'])}"
            f"（-{summary['saving_pct']:.1f}%）")

    log(f"\n5. 参考分红明细（{ref['label']}）:")
    for d in ref["dividends"]:
        rpt = f" 报告期 {str(d['report_date'])[:10]}" if d.get("report_date") else ""
        log(f"   除息日 {d['ex_dividend_date']}  每10股派 {d['cash_per_10']:.4f} 元{rpt}")
    print_footer(log, 76)


def make_chart(summary: dict, stock_name: str, stock_code: str, saver, show: bool = True):
    """对比图：两种策略所需买入资金（万元）+ 参考期每股分红构成"""
    ref = summary["reference"]
    nr = summary["no_reinvest"]
    ri = summary["reinvest"]

    fig = plt.figure(figsize=(14, 8))

    # 左图：所需买入资金对比
    ax1 = plt.subplot(1, 2, 1)
    names = ["红利再投", "分红不投"]
    amounts = [ri["required_amount"] if ri else nr["required_amount"], nr["required_amount"]]
    colors = ["#cf1322", "#1890ff"]
    bars = ax1.bar(names, [a / 10000 for a in amounts], color=colors, width=0.45)
    ax1.set_title("所需买入资金对比（万元）")
    ax1.set_ylabel("万元")
    ax1.grid(True, alpha=0.3, axis="y")
    for bar, v in zip(bars, amounts):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                 f"{v/10000:,.1f} 万", ha="center", va="bottom", fontsize=11, fontweight="bold")
    if ri is not None:
        ax1.text(0.5, max(amounts) / 10000 * 0.92,
                 f"再投少花 {summary['saving_amount']/10000:,.1f} 万 (-{summary['saving_pct']:.1f}%)",
                 ha="center", fontsize=11, color="#3f8600", fontweight="bold")

    # 右图：参考期每股分红构成
    ax2 = plt.subplot(1, 2, 2)
    divs = ref["dividends"]
    x = [f"{d['ex_dividend_date'][:7]}" for d in divs]
    y = [d["cash_per_10"] / 10 for d in divs]  # 元/股
    bars2 = ax2.bar(x, y, color="#fa8c16", width=0.55)
    ax2.set_title(f"{ref['label']} 各笔分红（元/股）")
    ax2.set_ylabel("元/股")
    ax2.grid(True, alpha=0.3, axis="y")
    ax2.tick_params(axis="x", rotation=45, labelsize=8)
    for bar, v in zip(bars2, y):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                 f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    ax2.axhline(ref["d_per_share"], color="#cf1322", linestyle="--", linewidth=1.2,
                label=f"年合计 {ref['d_per_share']:.2f} 元/股")
    ax2.legend(fontsize=9)

    fig.suptitle(f"{stock_name}({stock_code}) 分红目标测算", fontsize=14, fontweight="bold")
    plt.tight_layout()
    if show:
        plt.show()
    chart_path = saver.save_chart(f"{stock_code}_分红目标测算.jpg")
    plt.close(fig)
    return chart_path


def add_parser(sub):
    """注册子命令（--code/--buy-date/--target/--tax/--reference/--sync/--no-chart；无 --start/--end）"""
    p = sub.add_parser(ANALYSIS_NAME, help=DESCRIPTION,
                       parents=[code_parent(), db_common_parent()])
    p.add_argument("--buy-date", default=None,
                   help="买入日期 YYYY-MM-DD（非交易日顺延到下一交易日）")
    p.add_argument("--target", type=float, default=200000,
                   help="目标每年分红到账金额，元（默认 200000）")
    p.add_argument("--reference", default="last_year", choices=["last_year", "trailing"],
                   help="每股年分红基准: last_year=去年全年, trailing=最近12个月（默认 last_year）")
    p.set_defaults(_run=run)
    return p


def interactive_input(saver):
    """菜单路径的交互输入"""
    stock_code = ask("请输入股票代码（默认：601857）: ", "601857")
    buy_date = ask("请输入买入日期 YYYY-MM-DD（非交易日顺延到下一交易日）: ", "")
    target = ask("请输入目标每年分红到账金额，元（默认：200000）: ", 200000.0, float)
    tax = ask("请输入分红税率 0~1（默认：0 = 长期持有免税）: ", 0.0, float)
    reference = ask("请输入每股年分红基准 last_year/trailing（默认：last_year）: ", "last_year")
    if reference not in ("last_year", "trailing"):
        reference = "last_year"
    return argparse.Namespace(code=stock_code, buy_date=buy_date or None,
                              target=target, tax=tax, reference=reference,
                              sync=False, no_chart=False)


def run(args, saver=None):
    """执行分析（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)）"""
    if saver is None:
        saver = reset_saver(ANALYSIS_NAME)
    stock_code = args.code.strip()

    saver.set_tag(stock_code)
    log = saver.log

    buy_date = args.buy_date
    if not buy_date:
        buy_date = ask("请输入买入日期（YYYY-MM-DD）: ", "").strip() or None

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stock_name = get_stock_name(db, stock_code) or stock_code
        log(f"正在读取 {stock_name}({stock_code}) 的不复权行情...")
        result = plan_target(
            db, stock_code, buy_date=buy_date,
            target_annual_dividend=args.target, tax_rate=args.tax,
            reinvest=True, reference=args.reference, lot_size=100,
            sync=args.sync, log=log,
        )

        if result["status"] != "ok":
            if result["status"] != "no_data":
                log(f"测算失败: {result.get('message', '未知错误')}")
            saver.finalize()
            return 0

        print_report(result["summary"], stock_name, stock_code, log)
        make_chart(result["summary"], stock_name, stock_code, saver, show=not args.no_chart)
    finally:
        db.close()

    saver.finalize()
    return 0
