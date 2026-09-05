# -*- coding: utf-8 -*-
"""
模拟持仓 —— 买入持有/理想买卖/均线策略三策略模拟对比（迁移自旧版独立脚本）

行情为前复权口径（分红送转已还原）。
入口契约见 analysis.tools 包 docstring。
"""
import argparse
import asyncio
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from emdata import AdjustPriceType

from analysis.chart_utils import setup_chinese_fonts
from analysis.cli import ask, code_parent, range_parent, today_str
from analysis.kline import fetch_kline_df
from analysis.metrics import calc_max_drawdown, total_return_pct
from analysis.report import print_footer, print_header, print_strategy_block
from result_saver import reset_saver

setup_chinese_fonts()

ANALYSIS_NAME = "模拟持仓"
DESCRIPTION = "买入持有/理想买卖/均线策略三策略模拟对比"


@dataclass
class Trade:
    action: str
    date: datetime
    price: float
    shares: int
    amount: float
    reason: str


@dataclass
class StrategyResult:
    name: str
    trades: List[Trade]
    final_value: float
    return_pct: float
    max_drawdown_pct: float
    cost_avg: float  # 前复权成本均价（行情为前复权口径，成本价即前复权口径）


def calc_cost_avg(trades: List[Trade]) -> float:
    """前复权成本均价 = 各笔买入金额合计 / 买入股数合计（行情为前复权口径）"""
    buys = [t for t in trades if t.action == "买入"]
    total_amount = sum(t.amount for t in buys)
    total_shares = sum(t.shares for t in buys)
    return total_amount / total_shares if total_shares else 0.0


def simulate_buy_and_hold(df: pd.DataFrame, initial_capital: float) -> StrategyResult:
    buy_price = df.iloc[0]["close"]
    shares = int(initial_capital / buy_price / 100) * 100
    if shares == 0:
        shares = int(initial_capital / buy_price)

    buy_amount = shares * buy_price
    sell_price = df.iloc[-1]["close"]
    final_value = shares * sell_price
    equity = [
        initial_capital - buy_amount + shares * row["close"] for _, row in df.iterrows()
    ]

    trades = [
        Trade(
            "买入", df.iloc[0]["date"], buy_price, shares, buy_amount, "期初全仓买入"
        ),
        Trade(
            "卖出", df.iloc[-1]["date"], sell_price, shares, final_value, "期末全部卖出"
        ),
    ]
    return StrategyResult(
        name="买入持有",
        trades=trades,
        final_value=final_value,
        return_pct=total_return_pct(initial_capital, final_value),
        max_drawdown_pct=calc_max_drawdown(equity),
        cost_avg=calc_cost_avg(trades),
    )


def simulate_optimal_trade(df: pd.DataFrame, initial_capital: float) -> StrategyResult:
    best_return = -float("inf")
    best_buy_idx = 0
    best_sell_idx = len(df) - 1

    for buy_idx in range(len(df)):
        for sell_idx in range(buy_idx + 1, len(df)):
            buy_price = df.iloc[buy_idx]["low"]
            sell_price = df.iloc[sell_idx]["high"]
            ret = (sell_price - buy_price) / buy_price
            if ret > best_return:
                best_return = ret
                best_buy_idx = buy_idx
                best_sell_idx = sell_idx

    buy_price = df.iloc[best_buy_idx]["low"]
    sell_price = df.iloc[best_sell_idx]["high"]
    shares = int(initial_capital / buy_price / 100) * 100 or int(
        initial_capital / buy_price
    )
    buy_amount = shares * buy_price
    final_value = shares * sell_price

    equity = [initial_capital] * len(df)
    for i in range(best_buy_idx, best_sell_idx + 1):
        equity[i] = initial_capital - buy_amount + shares * df.iloc[i]["close"]
    for i in range(best_sell_idx + 1, len(df)):
        equity[i] = final_value

    trades = [
        Trade(
            "买入",
            df.iloc[best_buy_idx]["date"],
            buy_price,
            shares,
            buy_amount,
            f"区间最低点附近买入（{df.iloc[best_buy_idx]['date'].strftime('%Y-%m-%d')}）",
        ),
        Trade(
            "卖出",
            df.iloc[best_sell_idx]["date"],
            sell_price,
            shares,
            final_value,
            f"买入后最高点附近卖出（{df.iloc[best_sell_idx]['date'].strftime('%Y-%m-%d')}）",
        ),
    ]
    return StrategyResult(
        name="理想买卖（事后最优）",
        trades=trades,
        final_value=final_value,
        return_pct=total_return_pct(initial_capital, final_value),
        max_drawdown_pct=calc_max_drawdown(equity),
        cost_avg=calc_cost_avg(trades),
    )


def simulate_ma_crossover(
    df: pd.DataFrame,
    initial_capital: float,
    short_window: int = 5,
    long_window: int = 20,
) -> StrategyResult:
    data = df.copy()
    data["ma_short"] = data["close"].rolling(short_window).mean()
    data["ma_long"] = data["close"].rolling(long_window).mean()
    data["signal"] = 0
    data.loc[data["ma_short"] > data["ma_long"], "signal"] = 1
    data["cross"] = data["signal"].diff()

    cash = initial_capital
    shares = 0
    trades: List[Trade] = []
    equity: List[float] = []

    for _, row in data.iterrows():
        price = row["close"]
        if row["cross"] == 1 and shares == 0 and cash > 0:
            shares = int(cash / price / 100) * 100 or int(cash / price)
            if shares > 0:
                amount = shares * price
                cash -= amount
                trades.append(
                    Trade(
                        "买入",
                        row["date"],
                        price,
                        shares,
                        amount,
                        f"MA{short_window}上穿MA{long_window}（金叉）",
                    )
                )
        elif row["cross"] == -1 and shares > 0:
            amount = shares * price
            cash += amount
            trades.append(
                Trade(
                    "卖出",
                    row["date"],
                    price,
                    shares,
                    amount,
                    f"MA{short_window}下穿MA{long_window}（死叉）",
                )
            )
            shares = 0

        equity.append(cash + shares * price)

    if shares > 0:
        last = data.iloc[-1]
        amount = shares * last["close"]
        cash += amount
        trades.append(
            Trade(
                "卖出",
                last["date"],
                last["close"],
                shares,
                amount,
                "期末强制平仓",
            )
        )
        shares = 0
        equity[-1] = cash

    final_value = cash
    return StrategyResult(
        name=f"均线策略（MA{short_window}/MA{long_window}）",
        trades=trades,
        final_value=final_value,
        return_pct=total_return_pct(initial_capital, final_value),
        max_drawdown_pct=calc_max_drawdown(equity),
        cost_avg=calc_cost_avg(trades),
    )


def find_swing_points(df: pd.DataFrame, window: int = 5) -> Tuple[List[int], List[int]]:
    buy_points: List[int] = []
    sell_points: List[int] = []

    for i in range(window, len(df) - window):
        local_low = df.iloc[i - window : i + window + 1]["low"].min()
        local_high = df.iloc[i - window : i + window + 1]["high"].max()
        if df.iloc[i]["low"] == local_low:
            buy_points.append(i)
        if df.iloc[i]["high"] == local_high:
            sell_points.append(i)

    return buy_points, sell_points


def analyze_period(
    df: pd.DataFrame, stock_code: str, stock_name: str, initial_capital: float
):
    start_close = df.iloc[0]["close"]
    end_close = df.iloc[-1]["close"]
    high_idx = df["high"].idxmax()
    low_idx = df["low"].idxmin()

    buy_points, sell_points = find_swing_points(df)

    strategies = [
        simulate_buy_and_hold(df, initial_capital),
        simulate_optimal_trade(df, initial_capital),
        simulate_ma_crossover(df, initial_capital),
    ]

    summary = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "start_date": df.iloc[0]["date"].strftime("%Y-%m-%d"),
        "end_date": df.iloc[-1]["date"].strftime("%Y-%m-%d"),
        "trading_days": len(df),
        "start_close": start_close,
        "end_close": end_close,
        "period_return_pct": total_return_pct(start_close, end_close),
        "high_price": df.iloc[high_idx]["high"],
        "high_date": df.iloc[high_idx]["date"].strftime("%Y-%m-%d"),
        "low_price": df.iloc[low_idx]["low"],
        "low_date": df.iloc[low_idx]["date"].strftime("%Y-%m-%d"),
        "swing_buy_dates": [
            df.iloc[i]["date"].strftime("%Y-%m-%d") for i in buy_points
        ],
        "swing_sell_dates": [
            df.iloc[i]["date"].strftime("%Y-%m-%d") for i in sell_points
        ],
        "strategies": strategies,
    }
    return summary, buy_points, sell_points


def print_report(summary: dict, saver=None):
    log = saver.log if saver else print

    print_header(log,
                 f"{summary['stock_name']}({summary['stock_code']}) 模拟持仓分析报告",
                 width=70, indent=11,
                 extra=[f"           分析期间: {summary['start_date']} 至 {summary['end_date']}"])

    log("\n1. 区间行情概览:")
    log(f"   行情口径: 前复权（分红送转已还原，成本价与收益率均为前复权口径）")
    log(f"   交易日数: {summary['trading_days']} 天")
    log(f"   期初收盘: {summary['start_close']:.2f}")
    log(f"   期末收盘: {summary['end_close']:.2f}")
    log(f"   区间涨跌幅: {summary['period_return_pct']:.2f}%")
    log(f"   最高价: {summary['high_price']:.2f}（{summary['high_date']}）")
    log(f"   最低价: {summary['low_price']:.2f}（{summary['low_date']}）")

    log("\n2. 波段高低点参考（局部极值）:")
    log(f"   潜在买入参考日: {', '.join(summary['swing_buy_dates'][:8]) or '无'}")
    if len(summary["swing_buy_dates"]) > 8:
        log(f"   ... 共 {len(summary['swing_buy_dates'])} 个低点")
    log(f"   潜在卖出参考日: {', '.join(summary['swing_sell_dates'][:8]) or '无'}")
    if len(summary["swing_sell_dates"]) > 8:
        log(f"   ... 共 {len(summary['swing_sell_dates'])} 个高点")

    log("\n3. 策略模拟对比:")
    for strategy in summary["strategies"]:
        print_strategy_block(
            log,
            strategy.name,
            [
                ("最终资产", f"{strategy.final_value:,.2f} 元"),
                ("收益率", f"{strategy.return_pct:.2f}%"),
                ("最大回撤", f"{strategy.max_drawdown_pct:.2f}%"),
                ("前复权成本均价", f"{strategy.cost_avg:.4f} 元/股"
                                  "（各笔买入金额合计 / 股数合计，行情为前复权口径）"),
            ],
            trades=[(t.date.strftime('%Y-%m-%d'), t.action, t.shares,
                     f"{t.price:.2f}", f"{t.amount:,.2f}", t.reason)
                    for t in strategy.trades] or None,
        )

    best = max(summary["strategies"], key=lambda s: s.return_pct)
    log("\n4. 操作建议:")
    if summary["period_return_pct"] > 10:
        trend = "上涨趋势"
        advice = "可考虑逢低分批买入，均线金叉时加仓"
    elif summary["period_return_pct"] > -5:
        trend = "震荡整理"
        advice = "适合高抛低吸，在局部低点买入、局部高点卖出"
    else:
        trend = "下跌趋势"
        advice = "建议谨慎观望，等待均线金叉或趋势反转信号"

    log(f"   整体趋势: {trend}")
    log(f"   策略建议: {advice}")
    log(f"   区间内表现最佳策略: {best.name}（收益率 {best.return_pct:.2f}%）")
    print_footer(log, 70)


def plot_analysis(
    df: pd.DataFrame,
    summary: dict,
    buy_points: List[int],
    sell_points: List[int],
    stock_code: str,
    show: bool = True,
):
    data = df.copy()
    data["ma5"] = data["close"].rolling(5).mean()
    data["ma20"] = data["close"].rolling(20).mean()

    ma_strategy = next(
        s for s in summary["strategies"] if s.name.startswith("均线策略")
    )

    fig = plt.figure(figsize=(16, 10))
    ax1 = plt.subplot(2, 1, 1)

    for i, row in data.iterrows():
        color = "red" if row["close"] >= row["open"] else "green"
        ax1.plot([i, i], [row["low"], row["high"]], color="black", linewidth=0.8)
        ax1.plot([i, i], [row["open"], row["close"]], color=color, linewidth=2)

    ax1.plot(data.index, data["ma5"], label="MA5", color="orange", linewidth=1.2)
    ax1.plot(data.index, data["ma20"], label="MA20", color="blue", linewidth=1.2)

    for idx in buy_points:
        ax1.scatter(
            idx, data.iloc[idx]["low"], marker="^", color="green", s=80, zorder=5
        )
    for idx in sell_points:
        ax1.scatter(
            idx, data.iloc[idx]["high"], marker="v", color="red", s=80, zorder=5
        )

    for trade in ma_strategy.trades:
        idx = data.index[data["date"] == trade.date][0]
        marker = "^" if trade.action == "买入" else "v"
        color = "lime" if trade.action == "买入" else "magenta"
        ax1.scatter(
            idx,
            trade.price,
            marker=marker,
            color=color,
            s=120,
            edgecolors="black",
            zorder=6,
        )

    tick_step = max(1, len(data) // 10)
    ax1.set_xticks(range(0, len(data), tick_step))
    ax1.set_xticklabels(
        [
            data.iloc[i]["date"].strftime("%Y-%m-%d")
            for i in range(0, len(data), tick_step)
        ],
        rotation=45,
    )
    ax1.set_title(f"{summary['stock_name']}({stock_code}) 模拟持仓 - K线与买卖信号")
    ax1.set_ylabel("价格")
    ax1.legend(["MA5", "MA20", "局部低点", "局部高点", "均线买入", "均线卖出"])
    ax1.grid(True, alpha=0.3)

    ax2 = plt.subplot(2, 1, 2)
    strategy_names = [s.name for s in summary["strategies"]]
    returns = [s.return_pct for s in summary["strategies"]]
    colors = ["steelblue", "gold", "seagreen"]
    bars = ax2.bar(strategy_names, returns, color=colors, alpha=0.8)
    ax2.axhline(
        y=summary["period_return_pct"],
        color="red",
        linestyle="--",
        label="标的区间涨跌幅",
    )
    ax2.set_ylabel("收益率 (%)")
    ax2.set_title("策略收益率对比")
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis="y")

    for bar, value in zip(bars, returns):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (0.5 if value >= 0 else -1.5),
            f"{value:.2f}%",
            ha="center",
            va="bottom" if value >= 0 else "top",
        )

    plt.tight_layout()
    if show:
        plt.show()


def add_parser(sub):
    """注册子命令（--code/--start/--end/--capital/--no-chart，与原 argparse 参数一致）"""
    p = sub.add_parser(ANALYSIS_NAME, help=DESCRIPTION,
                       parents=[
                           code_parent(default="600519",
                                       help_text="股票代码（默认 600519 贵州茅台）"),
                           range_parent(start_help="起始日期 YYYY-MM-DD（默认：2024-01-01）",
                                        end_help="结束日期 YYYY-MM-DD（默认：今天）"),
                       ])
    p.add_argument("--capital", type=float, default=100000, help="初始资金（默认 100000 元）")
    p.add_argument("--no-chart", action="store_true",
                   help="不弹出图形窗口（图片仍会保存到 results 目录）")
    p.set_defaults(_run=run)
    return p


def interactive_input(saver):
    """菜单路径的交互输入（欢迎语用 print，与旧脚本一致）"""
    print("欢迎使用模拟持仓分析工具！")

    stock_code = ask("请输入股票代码（默认：600519）: ", "600519")
    start_date = ask("请输入起始日期（默认：2024-01-01，格式：YYYY-MM-DD）: ", "2024-01-01")
    end_date = ask(f"请输入结束日期（默认：{today_str()}，格式：YYYY-MM-DD）: ", today_str())
    initial_capital = ask("请输入初始资金（默认：100000）: ", 100000.0, float)

    return argparse.Namespace(code=stock_code, start=start_date, end=end_date,
                              capital=initial_capital, no_chart=False)


async def run_analysis(
    stock_code: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    show_chart: bool = True,
    saver=None,
):
    if saver is None:
        saver = reset_saver(ANALYSIS_NAME)
    saver.set_tag(stock_code)

    saver.log(f"正在获取 {stock_code} {start_date} 至 {end_date} 的日线数据...")
    df, stock_name = await fetch_kline_df(
        stock_code, start_date, end_date,
        adjust=AdjustPriceType.FORWARD, raise_on_empty=True,
    )
    saver.log(f"成功获取 {len(df)} 条K线数据（{stock_name}）")

    summary, buy_points, sell_points = analyze_period(
        df, stock_code, stock_name, initial_capital
    )
    print_report(summary, saver)

    plot_analysis(df, summary, buy_points, sell_points, stock_code, show=show_chart)
    saver.save_chart(f"{stock_code}_模拟持仓.jpg")

    saver.finalize()
    return summary


def run(args, saver=None):
    """执行分析（saver 为 None 时由 run_analysis 自行 reset_saver）"""
    asyncio.run(run_analysis(
        stock_code=args.code,
        start_date=args.start,
        end_date=args.end or today_str(),
        initial_capital=args.capital,
        show_chart=not getattr(args, "no_chart", False),
        saver=saver,
    ))
    return 0
