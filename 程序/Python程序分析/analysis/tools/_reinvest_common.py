# -*- coding: utf-8 -*-
"""
红利再投系列工具公共脚手架（analysis.tools 包内私有模块，不入 TOOLS 注册表）

承接 红利再投 / 红利再投增强版 / 大跌分批买入 三工具逐字相同的中等粒度片段：
    fmt_annual                  年化收益率文本（统一 '{:.2f}%'，与旧独立脚本一致）
    print_strategy_compare      三策略对比两行版式（rows 构建 + print_compare_rows）
    print_reinvest_total        「累计分红到账…其中再投…（N 次买入）」单行
    print_forward_section       前复权口径整节（has_fwd 判断 + 块 / 「未计算」行）
    print_events_and_warnings   分红事件明细节 + 提示节（提示为空时整体跳过）
    make_compare_chart          权益曲线对比图骨架（三线 + 除息日标记 + 年度分红柱）
    ask_base_inputs / ask_tax   菜单路径公共问项（code/start/end/tax）
    run_tool                    run() 骨架（saver→建表→会话→取数→报告→图表→finalize）

字节级约定与 analysis.report 相同：数值按原脚本格式串输出，节号、标题、独有段落
留在各工具内（节号经 section_no 参数传入）。Python 3.10 语法兼容。
"""
import matplotlib.pyplot as plt

from analysis.chart_utils import (
    EQUITY_COLORS, plot_equity_lines, set_date_ticks,
    mark_ex_dividend_dates, draw_year_dividend_bar,
)
from analysis.cli import ask
from analysis.report import (
    print_compare_rows, print_forward_block, print_dividend_table, print_warnings,
)
from backend.database import SessionLocal, engine
from backend.models import Base
from backend.services import get_stock_name
from result_saver import reset_saver

# 三线对比固定样式（顺序 = primary 主线 / secondary 对比线 / baseline 基准线）
_LINE_STYLES = [
    {"color": EQUITY_COLORS["primary"], "linewidth": 1.6},
    {"color": EQUITY_COLORS["secondary"], "linewidth": 1.2, "alpha": 0.85},
    {"color": EQUITY_COLORS["baseline"], "linewidth": 1.0, "linestyle": "--", "alpha": 0.8},
]


def fmt_annual(value) -> str:
    """年化收益率文本：None → 'N/A'，否则两位小数百分数（'{:.2f}%'，与旧独立脚本一致）"""
    return "N/A" if value is None else "{:.2f}%".format(value * 100)


def print_strategy_compare(log, lines) -> None:
    """三策略对比两行版式：lines=[(策略名, 策略dict), ...] → rows 构建 + print_compare_rows"""
    rows = [
        {
            "name": name,
            "line1": [
                f"期末总资产: {s['final_asset']:>14,.2f} 元",
                f"收益率: {s['total_return_pct']:>8.2f}%",
                f"年化: {fmt_annual(s['annual_return_pct'])}",
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


def print_reinvest_total(log, strategy: dict) -> None:
    """「累计分红到账…其中再投…（N 次买入）」单行（三工具同型，比较行留调用方）"""
    log(f"   累计分红到账: {strategy['total_dividends']:,.2f} 元，"
        f"其中再投 {strategy['total_reinvested']:,.2f} 元（{strategy['reinvest_count']} 次买入）")


def print_forward_section(log, section_no: int, lines, trades, trades_label: str) -> None:
    """前复权口径整节：任意一线有 forward_cost 时打印折算块，否则「未计算」行

    :param section_no: 节号（各工具不同，由调用方决定）
    :param lines: [(策略名, 策略dict), ...]（与 print_strategy_compare 同一份）
    :param trades: 主策略交易明细；:param trades_label: 明细表标签（如「红利再投线」）
    """
    has_fwd = any(s.get("forward_cost") is not None for _name, s in lines)
    if has_fwd:
        log(f"\n{section_no}. 前复权口径（成本价前复权）:")
        print_forward_block(log, lines, trades, trades_label)
    else:
        log(f"\n{section_no}. 前复权口径: 未计算（前复权数据缺失或覆盖不全，请先同步前复权行情）")


def print_events_and_warnings(log, section_no: int, events_title: str, events,
                              empty_text: str, warnings_list) -> None:
    """分红事件明细节 + 提示节（warnings 为空时提示节整体跳过，节号 = section_no+1）"""
    log(f"\n{section_no}. {events_title}:")
    print_dividend_table(log, events, empty_text)
    if warnings_list:
        log(f"\n{section_no + 1}. 提示:")
        print_warnings(log, warnings_list)


def make_compare_chart(saver, stock_name, stock_code, equity_curve, series, events,
                       title, chart_filename, ex_color=None, decorate=None,
                       bar_title="年度分红到账金额（元）", bar_empty="区间内无分红记录",
                       show: bool = True):
    """权益曲线对比图骨架：2×1 布局（上：三线权益曲线 + 除息日标记；下：年度分红柱状图）

    :param series: [(图例名, 曲线资产键), ...] 三条线，样式固定 primary/secondary/baseline；
                   第一条为策略主线（除息日散点高度、decorate 的 curve_map 均取它）
    :param ex_color: 除息日标记颜色（None = 默认 marker 色）
    :param decorate: 可选回调 decorate(ax1, dates, curve_map)，在除息日标记之前调用
                     （各工具画买入日竖线/注释/三角）
    :return: 图表保存路径
    """
    dates = [e["trade_date"] for e in equity_curve]

    fig = plt.figure(figsize=(16, 9))

    ax1 = plt.subplot(2, 1, 1)
    plot_equity_lines(ax1, dates, [
        (label, [e[key] for e in equity_curve], style)
        for (label, key), style in zip(series, _LINE_STYLES)
    ])

    curve_map = {e["trade_date"]: e[series[0][1]] for e in equity_curve}
    if decorate is not None:
        decorate(ax1, dates, curve_map)

    # 除息日标记（只标有行情的除息日）
    mark_ex_dividend_dates(ax1, curve_map, events, color=ex_color)

    ax1.set_title(title)
    ax1.set_ylabel("总资产（元）")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    set_date_ticks(ax1, dates)

    # 年度分红柱状图
    ax2 = plt.subplot(2, 1, 2)
    draw_year_dividend_bar(ax2, events, title=bar_title, empty_text=bar_empty)

    plt.tight_layout()
    if show:
        plt.show()  # 弹窗显示（关闭窗口后继续）
    chart_path = saver.save_chart(chart_filename)
    plt.close(fig)
    return chart_path


def ask_base_inputs(start_label: str, end_label: str):
    """菜单路径公共问项：股票代码 + 观察区间（问语文案参数化，逐字保持原样）"""
    stock_code = ask("请输入股票代码（默认：601857）: ", "601857")
    start_date = ask(f"请输入{start_label}: ", "")
    end_date = ask(f"请输入{end_label}: ", "")
    return stock_code, start_date, end_date


def ask_tax() -> float:
    """菜单路径公共问项：分红税率"""
    return ask("请输入分红税率 0~1（默认：0 = 长期持有免税）: ", 0.0, float)


def run_tool(args, analysis_name, load_msg, invoke, report_fn, chart_fn, saver=None) -> int:
    """三工具 run() 骨架：saver→set_tag→建表→会话→取名→取数模拟→报告→图表→finalize

    :param load_msg: 「正在读取 {name}({code}) 的{load_msg}...」尾部（"不复权行情" / "行情"）
    :param invoke: invoke(db, stock_code, args, log) -> 引擎结果 dict（strategy_runners 调用）
    :param report_fn: report_fn(result, stock_name, stock_code, args, log) -> None
    :param chart_fn: chart_fn(result, stock_name, stock_code, saver, show) -> None
    """
    if saver is None:
        saver = reset_saver(analysis_name)
    stock_code = args.code.strip()

    saver.set_tag(stock_code)
    log = saver.log

    # 建表（幂等）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stock_name = get_stock_name(db, stock_code) or stock_code
        log(f"正在读取 {stock_name}({stock_code}) 的{load_msg}...")
        result = invoke(db, stock_code, args, log)

        if result["status"] != "ok":
            if result["status"] != "no_data":
                log(f"模拟失败: {result.get('message', '未知错误')}")
            saver.finalize()
            return 0

        report_fn(result, stock_name, stock_code, args, log)

        # 图表始终绘制并保存（--no-chart 仅关闭弹窗）
        chart_fn(result, stock_name, stock_code, saver, show=not args.no_chart)
    finally:
        db.close()

    saver.finalize()  # finalize 内已输出保存路径
    return 0
