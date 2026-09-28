# -*- coding: utf-8 -*-
"""
高开低走分析 —— 上证指数、深证成指、沪深300 三大指数高开低走概率与高开后下跌幅度统计

口径：
    高开：当日开盘价较前一交易日收盘价上涨 >= threshold%（默认 1%）
    高开低走：高开且当日收盘价 < 当日开盘价
    高开后下跌幅度：(开盘价 - 收盘价) / 开盘价 * 100%

入口契约见 analysis.tools 包 docstring。
"""
import argparse
import asyncio
import warnings
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from analysis.chart_utils import setup_chinese_fonts
from analysis.cli import ask, range_parent, today_str
from analysis.kline import fetch_kline_df
from analysis.report import print_footer, print_header
from result_saver import reset_saver

setup_chinese_fonts()

ANALYSIS_NAME = "高开低走分析"
DESCRIPTION = "三大指数高开低走概率与高开后下跌幅度统计"

DEFAULT_START = "2008-01-01"
DEFAULT_THRESHOLD = 1.0

# 三大指数：代码、名称、图表配色
INDICES = [
    {"code": "000001", "name": "上证指数", "color": "#cf1322"},
    {"code": "399001", "name": "深证成指", "color": "#1890ff"},
    {"code": "000300", "name": "沪深300", "color": "#d4b106"},
]


class HighOpenLowCloseAnalyzer:
    """三大指数高开低走分析器"""

    def __init__(self):
        self.results = []
        self.start_date = None
        self.end_date = None
        self.threshold = DEFAULT_THRESHOLD

    async def fetch_all(self, start_date=DEFAULT_START, end_date=""):
        """抓取三大指数日K线"""
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        self.dfs = []

        for index_info in INDICES:
            df, quote_name = await fetch_kline_df(
                index_info["code"], self.start_date, self.end_date,
                stock_name=index_info["name"], period="daily",
            )
            self.dfs.append({
                "code": index_info["code"],
                "name": index_info["name"],
                "color": index_info["color"],
                "df": df,
            })
        return self.dfs

    def analyze(self, threshold: float = DEFAULT_THRESHOLD):
        """对每个指数计算高开低走概率与高开后下跌幅度"""
        self.threshold = threshold
        self.results = []

        for item in self.dfs:
            df = item["df"]
            if df is None or df.empty:
                continue

            data = df[["date", "open", "close"]].copy()
            data["prev_close"] = data["close"].shift(1)
            data["open_gap_pct"] = (
                (data["open"] - data["prev_close"]) / data["prev_close"] * 100
            )
            data["decline_pct"] = (
                (data["open"] - data["close"]) / data["open"] * 100
            )
            data["is_high_open"] = data["open_gap_pct"] >= threshold
            data["is_low_close"] = data["decline_pct"] > 0

            high_open = data[data["is_high_open"]]
            high_open_low_close = high_open[high_open["is_low_close"]]

            ho_count = len(high_open)
            low_count = len(high_open_low_close)

            annual_rows = []
            data["year"] = data["date"].dt.year
            for year, year_data in data.groupby("year"):
                y_ho = year_data[year_data["is_high_open"]]
                y_low = y_ho[y_ho["is_low_close"]]
                annual_rows.append({
                    "year": int(year),
                    "ho_count": len(y_ho),
                    "low_count": len(y_low),
                    "probability": (len(y_low) / len(y_ho) * 100)
                    if len(y_ho) else 0.0,
                    "avg_decline_low": (y_low["decline_pct"].mean()
                                        if len(y_low) else 0.0),
                    "avg_decline_all": (y_ho["decline_pct"].mean()
                                        if len(y_ho) else 0.0),
                })

            result = {
                "code": item["code"],
                "name": item["name"],
                "color": item["color"],
                "total_count": len(data),
                "ho_count": ho_count,
                "low_count": low_count,
                "probability": (low_count / ho_count * 100) if ho_count else 0.0,
                "avg_open_gap": (high_open["open_gap_pct"].mean() if ho_count else 0.0),
                "avg_decline_all": (high_open["decline_pct"].mean() if ho_count else 0.0),
                "avg_decline_low": (high_open_low_close["decline_pct"].mean()
                                    if low_count else 0.0),
                "median_decline_low": (high_open_low_close["decline_pct"].median()
                                       if low_count else 0.0),
                "max_decline": (high_open_low_close["decline_pct"].max()
                                if low_count else 0.0),
                "max_decline_date": None,
                "annual": annual_rows,
            }

            if low_count:
                worst = high_open_low_close.loc[
                    high_open_low_close["decline_pct"].idxmax()
                ]
                result["max_decline_date"] = worst["date"].strftime("%Y-%m-%d")
                result["max_decline_open"] = float(worst["open"])
                result["max_decline_close"] = float(worst["close"])

            self.results.append(result)

        return self.results

    def generate_report(self, saver=None):
        """生成文字报告"""
        if not self.results:
            message = "没有可分析的数据，请检查指数行情是否获取成功"
            if saver:
                saver.log(message)
            else:
                print(message)
            return

        log_func = saver.log if saver else print

        print_header(
            log_func,
            "三大指数高开低走分析报告",
            width=90,
            indent=8,
            extra=[
                f"        分析区间: {self.start_date} 至 {self.end_date}",
                f"        高开定义: 开盘价较前一交易日收盘价上涨 >= {self.threshold:.2f}%",
                f"        高开低走: 高开且收盘价 < 开盘价",
                f"        高开后下跌幅度: (开盘价 - 收盘价) / 开盘价 × 100%",
                f"        概率口径: 高开低走次数 / 高开次数 × 100%",
            ],
        )

        log_func("\n一、三大指数汇总")
        log_func(
            f"{'指数':<10}{'高开次数':<10}{'高开低走':<10}{'概率':<10}"
            f"{'高开后平均幅度%':<18}{'低走平均跌幅%':<16}{'低走最大跌幅%':<16}"
        )
        log_func("-" * 90)
        for r in self.results:
            log_func(
                f"{r['name']:<10}{r['ho_count']:<10}{r['low_count']:<10}"
                f"{r['probability']:>9.2f}% "
                f"{r['avg_decline_all']:<17.4f} "
                f"{r['avg_decline_low']:<15.4f} "
                f"{r['max_decline']:<15.4f}"
            )

        log_func("\n二、关键数据")
        for r in self.results:
            log_func(f"\n【{r['name']}】({r['code']})")
            log_func(f"   交易日总数: {r['total_count']}")
            log_func(f"   高开次数: {r['ho_count']}，平均高开幅度: {r['avg_open_gap']:.4f}%")
            log_func(f"   高开低走次数: {r['low_count']}，概率: {r['probability']:.2f}%")
            log_func(f"   高开后平均幅度(开盘-收盘)/开盘: {r['avg_decline_all']:.4f}%")
            log_func(f"   高开低走样本平均跌幅: {r['avg_decline_low']:.4f}%")
            log_func(f"   高开低走样本中位跌幅: {r['median_decline_low']:.4f}%")
            if r["max_decline_date"]:
                log_func(
                    f"   高开低走最大跌幅: {r['max_decline']:.4f}% "
                    f"（{r['max_decline_date']}，开盘 {r['max_decline_open']:.2f}，"
                    f"收盘 {r['max_decline_close']:.2f}）"
                )

        log_func("\n三、年度明细")
        for r in self.results:
            log_func(f"\n【{r['name']}】")
            log_func(
                f"{'年份':<8}{'高开次数':<10}{'高开低走':<10}{'概率':<10}"
                f"{'低走平均跌幅%':<16}{'高开后平均幅度%':<18}"
            )
            log_func("-" * 72)
            for y in r["annual"]:
                if y["ho_count"] == 0:
                    continue
                log_func(
                    f"{y['year']:<8}{y['ho_count']:<10}{y['low_count']:<10}"
                    f"{y['probability']:>9.2f}% "
                    f"{y['avg_decline_low']:<15.4f} "
                    f"{y['avg_decline_all']:<17.4f}"
                )

        print_footer(log_func, 90)

    def plot_analysis(self, show=True):
        """绘制三大指数高开低走对比图"""
        if not self.results:
            print("没有可绘制的分析数据")
            return

        names = [r["name"] for r in self.results]
        colors = [r["color"] for r in self.results]
        probs = [r["probability"] for r in self.results]
        avg_all = [r["avg_decline_all"] for r in self.results]
        avg_low = [r["avg_decline_low"] for r in self.results]

        fig = plt.figure(figsize=(18, 13))

        # 子图1：高开低走概率
        ax1 = plt.subplot(2, 2, 1)
        bars1 = ax1.bar(names, probs, color=colors, alpha=0.85)
        ax1.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax1.set_title("三大指数高开低走概率（2008年以来）")
        ax1.set_ylabel("概率(%)")
        ax1.set_ylim(0, max(probs) * 1.25 if probs and max(probs) > 0 else 100)
        ax1.grid(True, alpha=0.3, axis="y")
        for bar, v in zip(bars1, probs):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     f"{v:.2f}%", ha="center", va="bottom", fontsize=10)

        # 子图2：高开后下跌幅度（全部高开 vs 高开低走样本）
        ax2 = plt.subplot(2, 2, 2)
        x = np.arange(len(names))
        width = 0.35
        bars_a = ax2.bar(x - width / 2, avg_all, width,
                         label="高开后平均幅度", color="#8c8c8c", alpha=0.85)
        bars_b = ax2.bar(x + width / 2, avg_low, width,
                         label="高开低走平均跌幅", color="#fa8c16", alpha=0.85)
        ax2.axhline(y=0, color="black", linewidth=0.8)
        ax2.set_xticks(x)
        ax2.set_xticklabels(names)
        ax2.set_title("高开后下跌幅度对比：(开盘-收盘)/开盘")
        ax2.set_ylabel("幅度(%)")
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis="y")
        for bar, v in zip(list(bars_a) + list(bars_b), avg_all + avg_low):
            offset = 0.03 if v >= 0 else -0.12
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + offset,
                     f"{v:.3f}", ha="center", va="bottom" if v >= 0 else "top",
                     fontsize=8)

        # 子图3：年度高开低走概率
        ax3 = plt.subplot(2, 2, 3)
        all_years = sorted(set(
            y["year"] for r in self.results for y in r["annual"]
        ))
        for r in self.results:
            year_map = {y["year"]: y["probability"] for y in r["annual"]}
            values = [year_map.get(y, np.nan) for y in all_years]
            ax3.plot(all_years, values, marker="o", color=r["color"],
                     label=r["name"], linewidth=1.8)
        ax3.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax3.set_title("年度高开低走概率")
        ax3.set_xlabel("年份")
        ax3.set_ylabel("概率(%)")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 子图4：年度高开低走平均跌幅
        ax4 = plt.subplot(2, 2, 4)
        for r in self.results:
            year_map = {y["year"]: y["avg_decline_low"] for y in r["annual"]}
            values = [year_map.get(y, np.nan) for y in all_years]
            ax4.plot(all_years, values, marker="s", color=r["color"],
                     label=r["name"], linewidth=1.8)
        ax4.axhline(y=0, color="black", linewidth=0.8)
        ax4.set_title("年度高开低走样本平均跌幅")
        ax4.set_xlabel("年份")
        ax4.set_ylabel("跌幅(%)")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        if show:
            plt.show()


def add_parser(sub):
    """注册子命令（--start/--end/--threshold/--no-chart）"""
    p = sub.add_parser(
        ANALYSIS_NAME,
        help=DESCRIPTION,
        parents=[
            range_parent(
                start_default=DEFAULT_START,
                start_help=f"起始日期 YYYY-MM-DD（默认：{DEFAULT_START}）",
                end_help="结束日期 YYYY-MM-DD（默认：今天）",
            ),
        ],
    )
    p.add_argument("--no-chart", action="store_true",
                   help="不弹出图形窗口（图片仍会保存到 results 目录）")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                   help="高开阈值（%%，默认 1.0）")
    p.set_defaults(_run=run)
    return p


def interactive_input(saver):
    """菜单路径的交互输入"""
    log_func = saver.log if saver else print
    log_func("=== 高开低走分析工具 ===")
    log_func("默认分析上证指数、深证成指、沪深300 三大指数")
    log_func("高开定义：开盘价较前一交易日收盘价上涨 >= 1%\n")

    start_date = ask(f"请输入起始日期（默认：{DEFAULT_START}）: ", DEFAULT_START)
    end_date = ask(f"请输入结束日期（默认：{today_str()}）: ", today_str())
    threshold = ask("请输入高开阈值（%，默认：1.0）: ", DEFAULT_THRESHOLD, float)

    return argparse.Namespace(start=start_date, end=end_date,
                              threshold=threshold, no_chart=False)


def run(args, saver=None):
    """执行分析（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)）"""
    if saver is None:
        saver = reset_saver(ANALYSIS_NAME)

    saver.set_tag("三大指数")
    start_date = args.start or DEFAULT_START
    end_date = args.end or today_str()
    threshold = getattr(args, "threshold", DEFAULT_THRESHOLD)

    analyzer = HighOpenLowCloseAnalyzer()
    asyncio.run(analyzer.fetch_all(start_date, end_date))

    if not analyzer.dfs or all(item["df"] is None or item["df"].empty
                               for item in analyzer.dfs):
        saver.log("无法获取三大指数K线数据，程序退出")
        saver.finalize()
        return 2

    for item in analyzer.dfs:
        df = item["df"]
        if df is not None and not df.empty:
            saver.log(f"{item['name']}({item['code']}) 数据预览 (共{len(df)}条):")
            saver.log(df.head().to_string())
            saver.log(df.tail().to_string())

    analyzer.analyze(threshold=threshold)
    analyzer.generate_report(saver)
    analyzer.plot_analysis(show=not getattr(args, "no_chart", False))
    saver.save_chart("三大指数_高开低走分析.jpg")
    saver.finalize()
    return 0
