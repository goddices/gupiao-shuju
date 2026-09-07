# -*- coding: utf-8 -*-
"""
报告输出公共库 —— 对比/报告打印助手

纯函数、只依赖 log 可调用对象（通常是 result_saver 的 saver.log 或 print），
不 import result_saver / matplotlib / pandas。供 analysis.tools 各工具模块复用，
不进 analysis/__init__.py 重导出（web 后端不需要）。

字节级约定：各调用方把数值用与原脚本相同的 f-string 预格式化成字符串后传入，
本模块只负责行首缩进、片段连接与表头，保证迁移后日志与旧脚本逐字一致。
"""
from typing import Callable, List, Optional, Sequence, Tuple

LogFunc = Callable[[str], None]


def wan(value: float) -> str:
    """元 → 万元文本（源自 分红目标测算 的 wan() 封装，千分位 + 空格 + 万）"""
    return f"{value / 10000:,.2f} 万"


def print_header(log: LogFunc, title: str, width: int = 76,
                 extra: Optional[Sequence[str]] = None,
                 indent: int = 8) -> None:
    """报告横幅：「=」*width + indent 空格缩进标题 + 可选附加行 + 「=」*width"""
    log("=" * width)
    log(" " * indent + title)
    for line in (extra or []):
        log(line)
    log("=" * width)


def print_footer(log: LogFunc, width: int = 76) -> None:
    log("=" * width)


def print_compare_rows(log: LogFunc, rows: Sequence[dict]) -> None:
    """策略对比两行版式（红利再投/红利再投增强版/大跌分批买入共用）

    rows: [{"name": str, "line1": [片段, ...], "line2": [片段, ...],
            "line3": [片段, ...](可选，摊薄成本口径行)}, ...]
    片段为预格式化字符串（如 "期末总资产: 1,234.56 元"），片段间固定两空格连接；
    首行前导 "   【name】"、其余行 12 空格缩进由本函数统一输出。
    """
    for r in rows:
        log("   【" + r["name"] + "】" + "  ".join(r["line1"]))
        log("            " + "  ".join(r["line2"]))
        if r.get("line3"):
            log("            " + "  ".join(r["line3"]))


def print_strategy_block(log: LogFunc, name: str,
                         fields: Sequence[Tuple[str, str]],
                         trades: Optional[Sequence[Tuple]] = None,
                         no_trades_text: str = "无交易信号") -> None:
    """策略块版式（模拟持仓共用）：每行一个指标 + 可选交易明细

    fields: [(标签, 预格式化值串), ...]
    trades: [(日期, 动作, 股数, 价格串, 金额串, 原因), ...]；None 打印 no_trades_text
    """
    log(f"\n   【{name}】")
    for label, value in fields:
        log(f"   {label}: {value}")
    if trades:
        log("   交易明细:")
        for date, action, shares, price, amount, reason in trades:
            log(f"     {date} {action} {shares}股 @ {price} ({amount}元) - {reason}")
    else:
        log(f"   {no_trades_text}")


def print_forward_block(log: LogFunc, lines: Sequence[Tuple[str, dict]],
                        trades: Sequence[dict], trades_label: str) -> None:
    """前复权口径块（红利再投/增强版/大跌分批买入三处逐字相同，仅明细标签不同）

    调用方负责打印节标题与 has_fwd 判断的 else 分支。
    lines: [(策略名, 策略dict含 forward_cost/forward_cost_avg/forward_return_pct), ...]
    trades: 主策略交易明细（含 trade_date/kind/price/shares/amount/fwd_price）
    """
    log("   每笔交易成本按当日前复权价折算（参考前复权K线对应日期），"
        "分红送转已隐含在复权价格中，现金资产另行列示")
    for name, s in lines:
        log(f"   【{name}】前复权成本: {s['forward_cost']:>14,.2f} 元  "
            f"成本均价: {s['forward_cost_avg']:>8.4f} 元/股  "
            f"前复权收益率: {s['forward_return_pct']:>8.2f}%")
    log(f"\n   每笔交易明细（日期/价格/数量，{trades_label}）:")
    log(f"   {'交易日期':<12}{'类型':>10}{'成交价':>10}{'数量':>10}{'金额':>14}{'当日前复权价':>14}")
    for t in trades:
        fp = f"{t['fwd_price']:>14.4f}" if t.get("fwd_price") is not None else f"{'—':>14}"
        log(f"   {t['trade_date']:<12}{t['kind']:>10}{t['price']:>10.4f}{t['shares']:>10,}"
            f"{t['amount']:>14,.2f}{fp}")


def print_dividend_table(log: LogFunc, events: Sequence[dict], empty_text: str) -> None:
    """分红事件明细表（三处逐字相同，仅空文案不同）

    调用方负责打印节标题（如 "\\n5. 分红事件明细:"）。
    """
    if events:
        log(f"   {'除息日':<12}{'每10股派息':>10}{'送转(股)':>9}{'到账金额':>13}"
            f"{'再投股数':>10}{'再投金额':>13}{'当日收盘':>10}")
        for e in events:
            bonus = (e["bonus_per_10"] or 0) + (e["conversion_per_10"] or 0)
            log(f"   {e['ex_dividend_date']:<12}{e['cash_per_10']:>10.4f}{bonus:>9.1f}"
                f"{e['cash_received']:>13,.2f}{e['reinvest_shares']:>10,}"
                f"{e['reinvest_amount']:>13,.2f}{e['close_price']:>10.2f}")
    else:
        log(f"   {empty_text}")


def print_warnings(log: LogFunc, warnings_list: Sequence[str]) -> None:
    """提示段（红利再投 6./增强版 8./分批 9. 同型，节号由调用方决定）"""
    if not warnings_list:
        return
    for w in warnings_list:
        log(f"   - {w}")
