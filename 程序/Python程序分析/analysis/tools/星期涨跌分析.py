# -*- coding: utf-8 -*-
"""
星期涨跌分析 —— 按星期几分组统计涨跌分布并预测未来交易日（迁移自旧版独立脚本）

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
from analysis.cli import ask, code_parent, market_parent, range_parent, today_str
from analysis.kline import fetch_kline_df
from analysis.metrics import change_stats
from analysis.report import print_footer, print_header
from analysis.trading_calendar import TradingCalendar
from result_saver import reset_saver

setup_chinese_fonts()

ANALYSIS_NAME = "星期涨跌分析"
DESCRIPTION = "按星期几分组统计涨跌分布并预测未来交易日"

WEEK_MAP = {
    "Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三",
    "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日"
}

WEEKDAY_ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五"]

# 交易日历（惰性加载假日 JSON）
_calendar_cache = None


def _get_calendar() -> TradingCalendar:
    global _calendar_cache
    if _calendar_cache is None:
        _calendar_cache = TradingCalendar()
    return _calendar_cache


class WeekdayChangeAnalyzer:
    def __init__(self):
        self.df = None
        self.stock_name = "上证指数"
        self.stock_code = "000001"
        self.start_date = None
        self.end_date = None
        self.weekday_stats = None

    async def fetch_kline_data(self, stock_code="000001", stock_name="上证指数",
                                start_date="2008-01-01", end_date=""):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')

        # 抓取委托 analysis.kline（limit 按区间自动估算）
        self.df, _ = await fetch_kline_df(
            stock_code, start_date, self.end_date,
            stock_name=stock_name, period="daily",
        )
        return self.df

    def analyze_weekday(self):
        """按星期几分组分析涨跌分布"""
        if self.df is None or len(self.df) == 0:
            print("请先获取K线数据")
            return None

        df = self.df.copy()
        df['change_pct'] = df['close'].pct_change() * 100
        df['weekday_en'] = df['date'].apply(lambda d: d.strftime("%A"))
        df['weekday_cn'] = df['weekday_en'].map(WEEK_MAP)

        # 去掉第一个NaN行
        df = df.dropna(subset=['change_pct'])

        stats = {}
        for wd in WEEKDAY_ORDER:
            wd_data = df[df['weekday_cn'] == wd]['change_pct']
            # 涨跌统计（统一口径 analysis.metrics.change_stats，舍入口径与旧脚本逐位一致）
            cs = change_stats(wd_data)
            stats[wd] = {
                'count': cs['count'],
                'up_count': cs['up_count'],
                'down_count': cs['down_count'],
                'flat_count': cs['flat_count'],
                'up_pct': round(cs['up_pct'], 2),
                'down_pct': round(cs['down_pct'], 2),
                'mean': round(cs['mean'], 4),
                'median': round(cs['median'], 4),
                'std': round(cs['std'], 4),
                'max_gain': round(cs['max_gain'], 4),
                'max_loss': round(cs['max_loss'], 4),
            }

        self.weekday_stats = stats
        self._df_with_weekday = df
        return stats

    def predict_next_day(self):
        """根据下一个交易日的星期几预测涨跌概率"""
        if self.weekday_stats is None:
            print("请先执行 analyze_weekday()")
            return None

        # 下一个交易日（节假日感知；超出日历范围时退化为只跳过周末）
        next_date = _get_calendar().next_trading_day(self.df['date'].max())

        en_name = next_date.strftime("%A")
        cn_name = WEEK_MAP[en_name]
        wd_stats = self.weekday_stats.get(cn_name, {})

        prediction = {
            'next_trade_date': next_date.strftime('%Y-%m-%d'),
            'weekday': cn_name,
            'up_probability': wd_stats.get('up_pct', 0),
            'down_probability': wd_stats.get('down_pct', 0),
            'mean_change': wd_stats.get('mean', 0),
            'sample_count': wd_stats.get('count', 0)
        }
        return prediction

    def predict_future_week(self):
        """预测未来5个交易日的涨跌概率"""
        if self.weekday_stats is None:
            print("请先执行 analyze_weekday()")
            return None

        predictions = []
        current = self.df['date'].max()

        for _ in range(5):
            current = _get_calendar().next_trading_day(current)

            en_name = current.strftime("%A")
            cn_name = WEEK_MAP[en_name]
            wd_stats = self.weekday_stats.get(cn_name, {})

            predictions.append({
                'date': current.strftime('%Y-%m-%d'),
                'weekday': cn_name,
                'up_probability': wd_stats.get('up_pct', 0),
                'down_probability': wd_stats.get('down_pct', 0),
                'mean_change': wd_stats.get('mean', 0),
                'sample_count': wd_stats.get('count', 0)
            })

        return predictions

    def plot_weekday_analysis(self, show=True):
        """绘制星期几涨跌分析图表"""
        if self.weekday_stats is None:
            print("请先执行 analyze_weekday()")
            return

        fig = plt.figure(figsize=(18, 14))

        # 子图1: 各星期涨跌天数对比
        ax1 = plt.subplot(2, 3, 1)
        x = np.arange(len(WEEKDAY_ORDER))
        width = 0.35
        up_counts = [self.weekday_stats[wd]['up_count'] for wd in WEEKDAY_ORDER]
        down_counts = [self.weekday_stats[wd]['down_count'] for wd in WEEKDAY_ORDER]
        bars1 = ax1.bar(x - width / 2, up_counts, width, label='上涨天数', color='red', alpha=0.7)
        bars2 = ax1.bar(x + width / 2, down_counts, width, label='下跌天数', color='green', alpha=0.7)
        ax1.set_xticks(x)
        ax1.set_xticklabels(WEEKDAY_ORDER)
        ax1.set_title(f'{self.stock_name} 各星期涨跌天数对比')
        ax1.set_ylabel('天数')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        for bar in bars1:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2., h + 1, str(int(h)),
                         ha='center', va='bottom', fontsize=8)
        for bar in bars2:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2., h + 1, str(int(h)),
                         ha='center', va='bottom', fontsize=8)

        # 子图2: 各星期涨跌概率
        ax2 = plt.subplot(2, 3, 2)
        up_pcts = [self.weekday_stats[wd]['up_pct'] for wd in WEEKDAY_ORDER]
        down_pcts = [self.weekday_stats[wd]['down_pct'] for wd in WEEKDAY_ORDER]
        bars3 = ax2.bar(x - width / 2, up_pcts, width, label='上涨概率(%)', color='red', alpha=0.7)
        bars4 = ax2.bar(x + width / 2, down_pcts, width, label='下跌概率(%)', color='green', alpha=0.7)
        ax2.set_xticks(x)
        ax2.set_xticklabels(WEEKDAY_ORDER)
        ax2.set_title(f'{self.stock_name} 各星期涨跌概率(%)')
        ax2.set_ylabel('概率(%)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        for bar in bars3:
            h = bar.get_height()
            if h > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2., h + 0.5, f'{h:.1f}',
                         ha='center', va='bottom', fontsize=8)
        for bar in bars4:
            h = bar.get_height()
            if h > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2., h + 0.5, f'{h:.1f}',
                         ha='center', va='bottom', fontsize=8)

        # 子图3: 各星期平均涨跌幅
        ax3 = plt.subplot(2, 3, 3)
        means = [self.weekday_stats[wd]['mean'] for wd in WEEKDAY_ORDER]
        colors = ['red' if m >= 0 else 'green' for m in means]
        bars5 = ax3.bar(WEEKDAY_ORDER, means, color=colors, alpha=0.7)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax3.set_title(f'{self.stock_name} 各星期平均涨跌幅(%)')
        ax3.set_ylabel('平均涨跌幅(%)')
        ax3.grid(True, alpha=0.3)
        for bar in bars5:
            h = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width() / 2., h + 0.002 if h >= 0 else h - 0.015,
                     f'{h:.3f}', ha='center', va='bottom', fontsize=8)

        # 子图4: 各星期涨跌幅箱线图
        ax4 = plt.subplot(2, 3, 4)
        box_data = [self._df_with_weekday[self._df_with_weekday['weekday_cn'] == wd]['change_pct'].dropna().values
                    for wd in WEEKDAY_ORDER]
        bp = ax4.boxplot(box_data, labels=WEEKDAY_ORDER, patch_artist=True)
        for patch, color in zip(bp['boxes'], ['lightcoral', 'lightblue', 'lightgreen', 'lightyellow', 'plum']):
            patch.set_facecolor(color)
        ax4.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        ax4.set_title(f'{self.stock_name} 各星期涨跌幅分布')
        ax4.set_ylabel('涨跌幅(%)')
        ax4.grid(True, alpha=0.3)

        # 子图5: 样本数量分布
        ax5 = plt.subplot(2, 3, 5)
        counts = [self.weekday_stats[wd]['count'] for wd in WEEKDAY_ORDER]
        bars6 = ax5.bar(WEEKDAY_ORDER, counts, color='steelblue', alpha=0.7)
        ax5.set_title(f'{self.stock_name} 各星期样本数量')
        ax5.set_ylabel('交易日数')
        ax5.grid(True, alpha=0.3)
        for bar in bars6:
            h = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width() / 2., h + 0.5, str(int(h)),
                     ha='center', va='bottom', fontsize=9)

        # 子图6: 未来5个交易日预测
        ax6 = plt.subplot(2, 3, 6)
        predictions = self.predict_future_week()
        if predictions:
            dates = [p['date'][-5:] for p in predictions]
            wds = [p['weekday'] for p in predictions]
            labels = [f"{d}\n({w})" for d, w in zip(dates, wds)]
            up_probs = [p['up_probability'] for p in predictions]
            down_probs = [p['down_probability'] for p in predictions]

            x2 = np.arange(len(labels))
            ax6.bar(x2 - 0.15, up_probs, 0.3, label='上涨概率(%)', color='red', alpha=0.7)
            ax6.bar(x2 + 0.15, down_probs, 0.3, label='下跌概率(%)', color='green', alpha=0.7)
            ax6.set_xticks(x2)
            ax6.set_xticklabels(labels, fontsize=8)
            ax6.set_title(f'{self.stock_name} 未来交易日预测')
            ax6.set_ylabel('概率(%)')
            ax6.legend()
            ax6.grid(True, alpha=0.3)

        plt.tight_layout()
        if show:
            plt.show()

    def generate_report(self, saver=None):
        """生成分析报告"""
        if self.weekday_stats is None:
            message = "请先执行 analyze_weekday()"
            if saver:
                saver.log(message)
            else:
                print(message)
            return

        log_func = saver.log if saver else print

        print_header(log_func,
                     f"{self.stock_name}({self.stock_code}) 星期涨跌分析报告",
                     width=70, indent=5,
                     extra=[f"     分析期间: {self.start_date} 至 {self.end_date}"])

        log_func(f"\n一、各星期涨跌统计:")
        log_func(f"{'星期':<8} {'交易日数':<10} {'上涨':<8} {'下跌':<8} {'上涨率':<10} {'下跌率':<10} {'平均涨跌%':<12}")
        log_func("-" * 70)
        for wd in WEEKDAY_ORDER:
            s = self.weekday_stats[wd]
            log_func(f"{wd:<8} {s['count']:<10} {s['up_count']:<8} {s['down_count']:<8} "
                     f"{s['up_pct']:<10.1f} {s['down_pct']:<10.1f} {s['mean']:<12.4f}")

        # 找出表现最好和最差的星期
        best_wd = max(WEEKDAY_ORDER, key=lambda w: self.weekday_stats[w]['mean'])
        worst_wd = min(WEEKDAY_ORDER, key=lambda w: self.weekday_stats[w]['mean'])
        best_up = max(WEEKDAY_ORDER, key=lambda w: self.weekday_stats[w]['up_pct'])

        log_func(f"\n二、关键发现:")
        log_func(f"   平均涨幅最高的交易日: {best_wd} ({self.weekday_stats[best_wd]['mean']:.4f}%)")
        log_func(f"   平均涨幅最低的交易日: {worst_wd} ({self.weekday_stats[worst_wd]['mean']:.4f}%)")
        log_func(f"   上涨概率最高的交易日: {best_up} ({self.weekday_stats[best_up]['up_pct']:.1f}%)")

        # 预测
        log_func(f"\n三、下一交易日预测:")
        next_pred = self.predict_next_day()
        if next_pred:
            log_func(f"   预计交易日: {next_pred['next_trade_date']} ({next_pred['weekday']})")
            log_func(f"   历史上涨概率: {next_pred['up_probability']:.1f}%")
            log_func(f"   历史下跌概率: {next_pred['down_probability']:.1f}%")
            log_func(f"   历史平均涨跌幅: {next_pred['mean_change']:.4f}%")
            log_func(f"   历史样本数量: {next_pred['sample_count']} 个交易日")

        log_func(f"\n四、未来5个交易日预测:")
        week_preds = self.predict_future_week()
        if week_preds:
            log_func(f"{'日期':<14} {'星期':<8} {'上涨概率%':<12} {'下跌概率%':<12} {'平均涨跌%':<12}")
            log_func("-" * 60)
            for p in week_preds:
                log_func(f"{p['date']:<14} {p['weekday']:<8} {p['up_probability']:<12.1f} "
                         f"{p['down_probability']:<12.1f} {p['mean_change']:<12.4f}")

        print_footer(log_func, 70)


def add_parser(sub):
    """注册子命令（--code/--name/--start/--end/--no-chart）"""
    p = sub.add_parser(ANALYSIS_NAME, help=DESCRIPTION,
                       parents=[
                           code_parent(default="000001",
                                       help_text="股票代码（默认 000001 上证指数）"),
                           range_parent(start_help="起始日期 YYYY-MM-DD（默认：2008-01-01）",
                                        end_help="结束日期 YYYY-MM-DD（默认：今天）"),
                           market_parent(),
                       ])
    p.set_defaults(_run=run)
    return p


def interactive_input(saver):
    """菜单路径的交互输入（欢迎语与旧脚本逐字一致）"""
    log_func = saver.log if saver else print
    log_func("=== 星期涨跌分析工具 ===")

    stock_code = ask("请输入股票代码（默认：000001 上证指数）: ", "000001")
    stock_name = ask("请输入股票名称（默认：上证指数）: ", "上证指数")
    start_date = ask("请输入起始日期（默认：2008-01-01）: ", "2008-01-01")
    end_date = ask(f"请输入结束日期（默认：{today_str()}）: ", today_str())

    return argparse.Namespace(code=stock_code, name=stock_name,
                              start=start_date, end=end_date, no_chart=False)


def run(args, saver=None):
    """执行分析（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)）"""
    if saver is None:
        saver = reset_saver(ANALYSIS_NAME)

    analyzer = WeekdayChangeAnalyzer()
    saver.set_tag(args.code)

    asyncio.run(analyzer.fetch_kline_data(
        args.code, args.name, args.start, args.end or today_str()))

    saver.log(f"\n数据预览 (共{len(analyzer.df)}条):")
    saver.log(analyzer.df.head().to_string())

    analyzer.analyze_weekday()
    analyzer.generate_report(saver)
    analyzer.plot_weekday_analysis(show=not getattr(args, "no_chart", False))

    saver.save_chart(f"{args.code}_星期涨跌分析.jpg")
    saver.finalize()
    return 0
