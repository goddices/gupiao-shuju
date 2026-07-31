"""
节日涨跌分析 - 分析中国A股在主要节假日前后7个交易日的涨跌幅度和概率
支持春节、国庆节、劳动节、端午节、中秋节、清明节、元旦等主要节日
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import json
import asyncio
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime, timedelta, date
from collections import defaultdict

from emdata import get_quote_reader, Market, AdjustPriceType, PeriodType
from result_saver import get_saver, reset_saver

# 主要节日列表（按重要性排序）
MAJOR_HOLIDAYS = ["春节", "国庆节", "劳动节", "端午节", "中秋节", "清明节", "元旦"]

# 节日颜色配置
HOLIDAY_COLORS = {
    "春节": "#FF0000",
    "国庆节": "#FF6600",
    "劳动节": "#0099FF",
    "端午节": "#33CC66",
    "中秋节": "#FFCC00",
    "清明节": "#99CC99",
    "元旦": "#0066CC",
}


class HolidayAnalyzer:
    """节日前后涨跌分析器"""

    def __init__(self):
        self.df = None
        self.stock_name = "上证指数"
        self.stock_code = "000001"
        self.start_date = None
        self.end_date = None
        self.trading_dates = set()
        self.non_trading_dates = set()
        self.holiday_events = []  # 所有节日事件 [{name, year, start, end, holidays}]
        self.analysis_results = {}  # {holiday_name: {position: stats}}

    # ==================== 假日数据加载 ====================

    def load_holiday_data(self):
        """加载2008-2026年所有假日数据，构建非交易日集合"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        all_public_holidays = set()
        all_transfer_workdays = set()
        holiday_events_by_name = defaultdict(list)

        for year in range(2008, 2027):
            filename = os.path.join(script_dir, "public_data", "cn_holidays", f"china_holidays_{year}.json")
            if not os.path.exists(filename):
                continue

            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            for entry in data.get("dates", []):
                d = entry["date"]
                if entry["type"] == "public_holiday":
                    all_public_holidays.add(d)
                    holiday_events_by_name[(entry["name"], year)].append(d)
                elif entry["type"] == "transfer_workday":
                    all_transfer_workdays.add(d)

        # 构建假日事件列表
        for (name, year), dates in holiday_events_by_name.items():
            if name not in MAJOR_HOLIDAYS:
                continue
            dates_sorted = sorted(dates)
            self.holiday_events.append({
                "name": name,
                "year": year,
                "start": dates_sorted[0],
                "end": dates_sorted[-1],
                "dates": dates_sorted,
            })

        # 按年份和节日名排序
        self.holiday_events.sort(key=lambda x: (x["year"], MAJOR_HOLIDAYS.index(x["name"])))

        # 构建非交易日集合（2008-2026年间所有日期）
        self._build_non_trading_set(all_public_holidays, all_transfer_workdays)

        print(f"已加载 {len(self.holiday_events)} 个节日事件（{len(MAJOR_HOLIDAYS)}种节日）")
        return self.holiday_events

    def _build_non_trading_set(self, public_holidays, transfer_workdays):
        """构建非交易日集合：周末 + 节假日 - 补班日"""
        self.non_trading_dates = set()
        start = date(2008, 1, 1)
        end = date(2026, 12, 31)
        current = start
        while current <= end:
            d_str = current.strftime("%Y-%m-%d")
            is_weekend = current.weekday() >= 5
            is_holiday = d_str in public_holidays
            is_workday_transfer = d_str in transfer_workdays

            # 非交易日 = (周末或节假日) 且不是补班日
            if (is_weekend or is_holiday) and not is_workday_transfer:
                self.non_trading_dates.add(d_str)

            current += timedelta(days=1)

    def is_trading_day(self, d):
        """判断是否为交易日"""
        if isinstance(d, str):
            d_str = d
        elif isinstance(d, (date, datetime)):
            d_str = d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d)[:10]
        else:
            d_str = str(d)[:10]
        return d_str not in self.non_trading_dates

    def get_trading_dates_from_data(self):
        """从已加载的K线数据中提取实际交易日集合"""
        if self.df is not None and len(self.df) > 0:
            self.trading_dates = set(
                d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d)[:10]
                for d in self.df['date']
            )
        return self.trading_dates

    # ==================== K线数据获取 ====================

    async def fetch_kline_data(self, stock_code="000001", stock_name="上证指数",
                                start_date="2008-01-01", end_date=""):
        """获取股票日K线数据"""
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')

        print(f"正在获取{stock_name}({stock_code}) {start_date}至{self.end_date}的日K线数据...")

        if stock_code == "000001" and stock_name == "上证指数":
            market_code = Market.SHANGHAI
        else:
            market_code = Market.SHANGHAI if stock_code.startswith('6') else Market.SHENGZHEN

        reader = get_quote_reader()

        try:
            # 计算需要获取的数据量（大约天数 * 1.5 确保足够）
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
            days_diff = (end_dt - start_dt).days + 100
            limit = min(max(days_diff, 1000), 5000)

            start_date_formatted = start_date.replace('-', '')
            end_date_formatted = self.end_date.replace('-', '')

            quote = await reader.read_quote_async(
                market=market_code,
                stock_code=stock_code,
                adjust_type=AdjustPriceType.NONE,
                period_type=PeriodType.DAILY,
                end_date=end_date_formatted,
                limit=limit
            )

            if quote is None:
                print(f"无法获取{stock_name}({stock_code})的数据")
                self.df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                return self.df

            kline_data = []
            for line in quote.quote_lines:
                kline_data.append({
                    'date': line.trade_date,
                    'open': line.open,
                    'high': line.high,
                    'low': line.low,
                    'close': line.close,
                    'volume': line.volume
                })

            self.df = pd.DataFrame(kline_data)
            self.df = self.df.sort_values('date').reset_index(drop=True)

            if start_date or end_date:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                self.df = self.df[(self.df['date'] >= start_dt) & (self.df['date'] <= end_dt)]

            # 提取实际交易日
            self.get_trading_dates_from_data()

            print(f"成功获取 {len(self.df)} 条日K线数据，包含 {len(self.trading_dates)} 个交易日")
            return self.df

        except Exception as e:
            print(f"获取数据时出错: {e}")
            self.df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
            return self.df

    # ==================== 核心分析逻辑 ====================

    def find_trading_days_around(self, target_date_str, direction="before", count=7):
        """从目标日期开始，向前或向后找count个交易日"""
        result = []
        target = datetime.strptime(target_date_str, "%Y-%m-%d")

        if direction == "before":
            current = target - timedelta(days=1)
        else:
            current = target + timedelta(days=1)

        max_iterations = 60  # 防止无限循环
        iterations = 0

        while len(result) < count and iterations < max_iterations:
            d_str = current.strftime("%Y-%m-%d")
            # 优先使用实际数据中的交易日，没有则用规则判断
            if self.trading_dates:
                is_trading = d_str in self.trading_dates
            else:
                is_trading = self.is_trading_day(d_str)

            if is_trading:
                result.append(d_str)

            if direction == "before":
                current -= timedelta(days=1)
            else:
                current += timedelta(days=1)
            iterations += 1

        return result if direction == "before" else result

    def find_last_trading_before(self, date_str):
        """找到date_str之前最后一个交易日"""
        trading_days = self.find_trading_days_around(date_str, "before", 1)
        return trading_days[0] if trading_days else None

    def find_first_trading_after(self, date_str):
        """找到date_str之后第一个交易日"""
        trading_days = self.find_trading_days_around(date_str, "after", 1)
        return trading_days[0] if trading_days else None

    def get_price_on_date(self, date_str):
        """获取某日期的收盘价（如非交易日则找前一个交易日的收盘价）"""
        if self.df is None or len(self.df) == 0:
            return None

        d = pd.to_datetime(date_str)
        # 找日期 <= date_str 的最近一条数据
        mask = self.df['date'] <= d
        if mask.any():
            return self.df.loc[mask, 'close'].iloc[-1]
        return None

    def compute_daily_returns(self, date_list):
        """计算一组连续日期的每日涨跌幅（相对于前一交易日）"""
        if not date_list or self.df is None or len(self.df) == 0:
            return []

        returns = []
        for d_str in date_list:
            d = pd.to_datetime(d_str)
            row = self.df[self.df['date'] == d]
            if len(row) > 0:
                close = row['close'].iloc[0]
                # 找前一个交易日
                prev_mask = self.df['date'] < d
                if prev_mask.any():
                    prev_close = self.df.loc[prev_mask, 'close'].iloc[-1]
                    change_pct = (close - prev_close) / prev_close * 100
                    returns.append({
                        'date': d_str,
                        'close': close,
                        'change_pct': round(change_pct, 4)
                    })
                else:
                    returns.append({'date': d_str, 'close': close, 'change_pct': None})
            else:
                returns.append({'date': d_str, 'close': None, 'change_pct': None})

        return returns

    def analyze_holiday(self, lookback=7, lookforward=7):
        """对所有节日事件进行分析"""
        if self.df is None or len(self.df) == 0:
            print("请先获取K线数据")
            return None

        print(f"\n正在分析 {len(self.holiday_events)} 个节日事件的前后{lookback}个交易日涨跌...")

        # 按节日名收集数据
        # {holiday_name: {position_key: [returns]}}
        raw_data = defaultdict(lambda: defaultdict(list))

        valid_events = 0
        for event in self.holiday_events:
            name = event["name"]
            holiday_start = event["start"]
            holiday_end = event["end"]

            # 找到假期前最后一个交易日
            last_trading_before = self.find_last_trading_before(holiday_start)
            if last_trading_before is None:
                continue

            # 找到假期后第一个交易日
            first_trading_after = self.find_first_trading_after(holiday_end)
            if first_trading_after is None:
                continue

            # 节前N个交易日
            pre_dates = self.find_trading_days_around(holiday_start, "before", lookback)
            pre_dates = list(reversed(pre_dates))  # 从远到近排序

            # 节后N个交易日
            post_dates = self.find_trading_days_around(holiday_end, "after", lookforward)

            # 计算每日涨跌幅
            pre_returns = self.compute_daily_returns(pre_dates)
            post_returns = self.compute_daily_returns(post_dates)

            # 记录节前每日涨跌
            for i, r in enumerate(pre_returns):
                pos = -(lookback - i)  # -7, -6, ..., -1
                if r['change_pct'] is not None:
                    raw_data[name][f"day_{pos}"].append({
                        'year': event['year'],
                        'date': r['date'],
                        'change_pct': r['change_pct']
                    })

            # 记录节后每日涨跌
            for i, r in enumerate(post_returns):
                pos = i + 1  # +1, +2, ..., +7
                if r['change_pct'] is not None:
                    raw_data[name][f"day_{pos}"].append({
                        'year': event['year'],
                        'date': r['date'],
                        'change_pct': r['change_pct']
                    })

            # 计算累计涨跌幅
            # 节前累计
            pre_changes = [r['change_pct'] for r in pre_returns if r['change_pct'] is not None]
            if pre_changes:
                cum_pre = np.prod([1 + c / 100 for c in pre_changes]) - 1
                raw_data[name]["cumulative_before"].append({
                    'year': event['year'],
                    'change_pct': round(cum_pre * 100, 4)
                })

            # 节后累计
            post_changes = [r['change_pct'] for r in post_returns if r['change_pct'] is not None]
            if post_changes:
                cum_post = np.prod([1 + c / 100 for c in post_changes]) - 1
                raw_data[name]["cumulative_after"].append({
                    'year': event['year'],
                    'change_pct': round(cum_post * 100, 4)
                })

            # 节后首日
            if post_changes:
                raw_data[name]["first_day_after"].append({
                    'year': event['year'],
                    'change_pct': post_changes[0]
                })

            valid_events += 1

        print(f"成功分析 {valid_events} 个节日事件")

        # 汇总统计
        self.analysis_results = {}
        for name in MAJOR_HOLIDAYS:
            if name not in raw_data:
                continue
            self.analysis_results[name] = {}
            for key, records in raw_data[name].items():
                changes = [r['change_pct'] for r in records]
                up_count = sum(1 for c in changes if c > 0)
                down_count = sum(1 for c in changes if c < 0)
                flat_count = sum(1 for c in changes if c == 0)
                total = len(changes)

                self.analysis_results[name][key] = {
                    'count': total,
                    'up_count': up_count,
                    'down_count': down_count,
                    'flat_count': flat_count,
                    'up_probability': round(up_count / total * 100, 2) if total > 0 else 0,
                    'down_probability': round(down_count / total * 100, 2) if total > 0 else 0,
                    'mean_change': round(np.mean(changes), 4) if total > 0 else 0,
                    'median_change': round(np.median(changes), 4) if total > 0 else 0,
                    'std_change': round(np.std(changes), 4) if total > 0 else 0,
                    'max_gain': round(max(changes), 4) if total > 0 else 0,
                    'max_loss': round(min(changes), 4) if total > 0 else 0,
                    'total_return': round(sum(changes), 4) if total > 0 else 0,
                    'records': records  # 保留原始记录
                }

        return self.analysis_results

    # ==================== 报告生成 ====================

    def generate_report(self, saver=None):
        """生成分析报告"""
        if not self.analysis_results:
            message = "请先执行 analyze_holiday()"
            if saver:
                saver.log(message)
            else:
                print(message)
            return

        log_func = saver.log if saver else print

        log_func("=" * 80)
        log_func(f"     {self.stock_name}({self.stock_code}) 节日前后涨跌分析报告")
        log_func(f"     分析期间: {self.start_date} 至 {self.end_date}")
        log_func(f"     涵盖节日: 2008-2026年共 {len(MAJOR_HOLIDAYS)} 种节日")
        log_func("=" * 80)

        for name in MAJOR_HOLIDAYS:
            if name not in self.analysis_results:
                continue
            stats = self.analysis_results[name]
            color = HOLIDAY_COLORS.get(name, "#000000")

            log_func(f"\n{'=' * 80}")
            log_func(f"  【{name}】节日前后7日涨跌分析")
            log_func(f"{'=' * 80}")

            # 节前分析
            log_func(f"\n  📉 节前 {7} 个交易日:")
            log_func(f"  {'位置':<8} {'样本数':<8} {'上涨次数':<10} {'下跌次数':<10} "
                     f"{'上涨概率':<10} {'平均涨跌%':<12} {'最大涨幅%':<10} {'最大跌幅%':<10}")
            log_func(f"  {'-' * 78}")
            for day in range(-7, 0):
                key = f"day_{day}"
                if key in stats:
                    s = stats[key]
                    log_func(f"  第{abs(day)}天前 {'':<2} "
                             f"{s['count']:<8} {s['up_count']:<10} {s['down_count']:<10} "
                             f"{s['up_probability']:<9.1f}% {s['mean_change']:<12.4f} "
                             f"{s['max_gain']:<10.4f} {s['max_loss']:<10.4f}")

            # 节前累计
            if "cumulative_before" in stats:
                s = stats["cumulative_before"]
                log_func(f"  {'累计(7日)':<8} "
                         f"{s['count']:<8} {s['up_count']:<10} {s['down_count']:<10} "
                         f"{s['up_probability']:<9.1f}% {s['mean_change']:<12.4f} "
                         f"{s['max_gain']:<10.4f} {s['max_loss']:<10.4f}")

            # 节后分析
            log_func(f"\n  📈 节后 {7} 个交易日:")
            log_func(f"  {'位置':<8} {'样本数':<8} {'上涨次数':<10} {'下跌次数':<10} "
                     f"{'上涨概率':<10} {'平均涨跌%':<12} {'最大涨幅%':<10} {'最大跌幅%':<10}")
            log_func(f"  {'-' * 78}")
            for day in range(1, 8):
                key = f"day_{day}"
                if key in stats:
                    s = stats[key]
                    log_func(f"  第{day}天后 {'':<2} "
                             f"{s['count']:<8} {s['up_count']:<10} {s['down_count']:<10} "
                             f"{s['up_probability']:<9.1f}% {s['mean_change']:<12.4f} "
                             f"{s['max_gain']:<10.4f} {s['max_loss']:<10.4f}")

            # 节后累计
            if "cumulative_after" in stats:
                s = stats["cumulative_after"]
                log_func(f"  {'累计(7日)':<8} "
                         f"{s['count']:<8} {s['up_count']:<10} {s['down_count']:<10} "
                         f"{s['up_probability']:<9.1f}% {s['mean_change']:<12.4f} "
                         f"{s['max_gain']:<10.4f} {s['max_loss']:<10.4f}")

            # 节后首日单独
            if "first_day_after" in stats:
                s = stats["first_day_after"]
                log_func(f"\n  🎯 节后首日特别关注:")
                log_func(f"     样本数: {s['count']}, 上涨概率: {s['up_probability']:.1f}%, "
                         f"平均涨跌: {s['mean_change']:.4f}%, "
                         f"最大涨幅: {s['max_gain']:.4f}%, 最大跌幅: {s['max_loss']:.4f}%")

        # 综合对比
        log_func(f"\n{'=' * 80}")
        log_func(f"  📊 各节日综合对比（节后首日）")
        log_func(f"{'=' * 80}")
        log_func(f"  {'节日':<10} {'样本':<6} {'上涨概率':<10} {'平均涨跌%':<12} {'节前累计%':<12} {'节后累计%':<12}")
        log_func(f"  {'-' * 70}")
        for name in MAJOR_HOLIDAYS:
            if name not in self.analysis_results:
                continue
            s = self.analysis_results[name]
            fd = s.get("first_day_after", {})
            cb = s.get("cumulative_before", {})
            ca = s.get("cumulative_after", {})
            log_func(f"  {name:<10} {fd.get('count', 0):<6} "
                     f"{fd.get('up_probability', 0):<9.1f}% "
                     f"{fd.get('mean_change', 0):<12.4f} "
                     f"{cb.get('mean_change', 0):<12.4f} "
                     f"{ca.get('mean_change', 0):<12.4f}")

        # 关键发现
        log_func(f"\n{'=' * 80}")
        log_func(f"  💡 关键发现")
        log_func(f"{'=' * 80}")

        # 找出节后首日上涨概率最高的节日
        best_first_day = None
        best_first_prob = 0
        for name in MAJOR_HOLIDAYS:
            if name in self.analysis_results:
                fd = self.analysis_results[name].get("first_day_after", {})
                prob = fd.get("up_probability", 0)
                if prob > best_first_prob:
                    best_first_prob = prob
                    best_first_day = name

        if best_first_day:
            log_func(f"  ✅ 节后首日上涨概率最高的节日: {best_first_day} ({best_first_prob:.1f}%)")

        # 找出节后累计表现最好的节日
        best_cum_after = max(
            (name for name in MAJOR_HOLIDAYS if name in self.analysis_results),
            key=lambda n: self.analysis_results[n].get("cumulative_after", {}).get("mean_change", -999)
        )
        ca = self.analysis_results[best_cum_after].get("cumulative_after", {})
        log_func(f"  ✅ 节后7日累计涨幅最大的节日: {best_cum_after} ({ca.get('mean_change', 0):.4f}%)")

        log_func("=" * 80)

    # ==================== 图表绘制 ====================

    def plot_holiday_analysis(self, lookback=7, lookforward=7):
        """绘制节日分析图表"""
        if not self.analysis_results:
            print("请先执行 analyze_holiday()")
            return

        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        active_holidays = [h for h in MAJOR_HOLIDAYS if h in self.analysis_results]
        n_holidays = len(active_holidays)

        if n_holidays == 0:
            print("没有可用的分析数据")
            return

        fig = plt.figure(figsize=(20, 4 * n_holidays + 10))

        # ---- 子图1: 各节日每日平均涨跌幅对比 ----
        ax1 = plt.subplot(n_holidays + 2, 2, 1)
        x_positions = list(range(-lookback, 0)) + list(range(1, lookforward + 1))
        x_labels = [f"前{abs(i)}天" for i in range(-lookback, 0)] + [f"后{i}天" for i in range(1, lookforward + 1)]

        for name in active_holidays:
            means = []
            for day in range(-lookback, 0):
                key = f"day_{day}"
                means.append(self.analysis_results[name].get(key, {}).get("mean_change", 0))
            for day in range(1, lookforward + 1):
                key = f"day_{day}"
                means.append(self.analysis_results[name].get(key, {}).get("mean_change", 0))

            color = HOLIDAY_COLORS.get(name, "#000000")
            ax1.plot(range(len(x_positions)), means, 'o-', color=color, linewidth=2,
                     markersize=4, label=name, alpha=0.8)

        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax1.axvline(x=lookback - 0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.set_xticks(range(len(x_positions)))
        ax1.set_xticklabels(x_labels, fontsize=7, rotation=45)
        ax1.set_title(f'{self.stock_name} 各节日前后每日平均涨跌幅对比', fontsize=13, fontweight='bold')
        ax1.set_ylabel('平均涨跌幅(%)')
        ax1.legend(fontsize=7, loc='best')
        ax1.grid(True, alpha=0.3)

        # ---- 子图2: 各节日每日上涨概率对比 ----
        ax2 = plt.subplot(n_holidays + 2, 2, 2)
        for name in active_holidays:
            probs = []
            for day in range(-lookback, 0):
                key = f"day_{day}"
                probs.append(self.analysis_results[name].get(key, {}).get("up_probability", 0))
            for day in range(1, lookforward + 1):
                key = f"day_{day}"
                probs.append(self.analysis_results[name].get(key, {}).get("up_probability", 0))

            color = HOLIDAY_COLORS.get(name, "#000000")
            ax2.plot(range(len(x_positions)), probs, 's-', color=color, linewidth=2,
                     markersize=4, label=name, alpha=0.8)

        ax2.axhline(y=50, color='black', linestyle='--', linewidth=0.5, alpha=0.5)
        ax2.axvline(x=lookback - 0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax2.set_xticks(range(len(x_positions)))
        ax2.set_xticklabels(x_labels, fontsize=7, rotation=45)
        ax2.set_title(f'{self.stock_name} 各节日前后每日上涨概率对比', fontsize=13, fontweight='bold')
        ax2.set_ylabel('上涨概率(%)')
        ax2.legend(fontsize=7, loc='best')
        ax2.grid(True, alpha=0.3)

        # ---- 子图3: 每个节日单独子图（节前累计 vs 节后累计柱状图）----
        for idx, name in enumerate(active_holidays):
            ax = plt.subplot(n_holidays + 2, 2, 3 + idx)
            s = self.analysis_results[name]

            # 节前每日
            pre_means = []
            pre_probs = []
            for day in range(-lookback, 0):
                key = f"day_{day}"
                pre_means.append(s.get(key, {}).get("mean_change", 0))
                pre_probs.append(s.get(key, {}).get("up_probability", 0))

            # 节后每日
            post_means = []
            post_probs = []
            for day in range(1, lookforward + 1):
                key = f"day_{day}"
                post_means.append(s.get(key, {}).get("mean_change", 0))
                post_probs.append(s.get(key, {}).get("up_probability", 0))

            # 双Y轴: 柱状图表示涨跌幅，折线表示概率
            x_pre = range(-lookback, 0)
            x_post = range(1, lookforward + 1)
            all_x = list(x_pre) + list(x_post)

            colors_bar = ['red' if m >= 0 else 'green' for m in pre_means + post_means]
            bars = ax.bar(all_x, pre_means + post_means, color=colors_bar, alpha=0.6, width=0.6)

            ax2_twin = ax.twinx()
            ax2_twin.plot(all_x, pre_probs + post_probs, 'b-o', linewidth=1.5, markersize=4, alpha=0.8)
            ax2_twin.set_ylabel('上涨概率(%)', color='blue')
            ax2_twin.set_ylim(0, 100)
            ax2_twin.axhline(y=50, color='blue', linestyle='--', linewidth=0.5, alpha=0.3)

            ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax.axvline(x=-0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            ax.set_title(f'{name} ({s.get("first_day_after", {}).get("count", 0)}年数据)', fontsize=11)
            ax.set_ylabel('平均涨跌幅(%)')
            ax.set_xticks(all_x)
            ax.set_xticklabels([f"前{abs(i)}天" for i in range(-lookback, 0)] +
                               [f"后{i}天" for i in range(1, lookforward + 1)],
                               fontsize=6, rotation=45)
            ax.grid(True, alpha=0.3)

            # 在柱状图上标注数值
            for bar in bars:
                h = bar.get_height()
                if abs(h) > 0.05:
                    ax.text(bar.get_x() + bar.get_width() / 2., h,
                            f'{h:.2f}', ha='center', va='bottom' if h >= 0 else 'top',
                            fontsize=5)

        # ---- 子图: 汇总对比 ----
        ax_summary = plt.subplot(n_holidays + 2, 1, n_holidays + 2)
        names = active_holidays
        x_idx = np.arange(len(names))
        width = 0.25

        pre_cum_means = [self.analysis_results[n].get("cumulative_before", {}).get("mean_change", 0) for n in names]
        post_cum_means = [self.analysis_results[n].get("cumulative_after", {}).get("mean_change", 0) for n in names]
        first_day_means = [self.analysis_results[n].get("first_day_after", {}).get("mean_change", 0) for n in names]

        bars1 = ax_summary.bar(x_idx - width, pre_cum_means, width,
                               label='节前7日累计', color='orange', alpha=0.8)
        bars2 = ax_summary.bar(x_idx, post_cum_means, width,
                               label='节后7日累计', color='steelblue', alpha=0.8)
        bars3 = ax_summary.bar(x_idx + width, first_day_means, width,
                               label='节后首日', color='coral', alpha=0.8)

        ax_summary.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax_summary.set_xticks(x_idx)
        ax_summary.set_xticklabels(names, fontsize=10)
        ax_summary.set_title(f'{self.stock_name} 各节日涨跌汇总对比', fontsize=13, fontweight='bold')
        ax_summary.set_ylabel('平均涨跌幅(%)')
        ax_summary.legend(fontsize=9)
        ax_summary.grid(True, alpha=0.3)

        # 标注数值
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                h = bar.get_height()
                if abs(h) > 0.01:
                    ax_summary.text(bar.get_x() + bar.get_width() / 2., h,
                                    f'{h:.2f}', ha='center', va='bottom' if h >= 0 else 'top',
                                    fontsize=7)

        plt.tight_layout()
        plt.show()

    def plot_heatmap(self):
        """绘制节日逐年热力图（节后首日涨跌）"""
        if not self.analysis_results:
            print("请先执行 analyze_holiday()")
            return

        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        active_holidays = [h for h in MAJOR_HOLIDAYS if h in self.analysis_results]
        if not active_holidays:
            return

        # 收集所有年份
        all_years = set()
        holiday_year_changes = defaultdict(dict)  # {holiday: {year: change_pct}}
        for name in active_holidays:
            fd_records = self.analysis_results[name].get("first_day_after", {}).get("records", [])
            for r in fd_records:
                all_years.add(r['year'])
                holiday_year_changes[name][r['year']] = r['change_pct']

        years = sorted(all_years)
        if not years:
            return

        # 构建热力图数据
        data = np.zeros((len(active_holidays), len(years)))
        data[:] = np.nan
        for i, name in enumerate(active_holidays):
            for j, year in enumerate(years):
                if year in holiday_year_changes[name]:
                    data[i, j] = holiday_year_changes[name][year]

        fig, ax = plt.subplots(figsize=(max(14, len(years) * 0.6), max(4, len(active_holidays) * 0.8)))

        # 自定义colormap: 绿-白-红
        from matplotlib.colors import LinearSegmentedColormap
        cmap = LinearSegmentedColormap.from_list('rg', ['#008000', '#ffffff', '#FF0000'])

        vmax = max(abs(np.nanmax(data)), abs(np.nanmin(data)), 0.5)
        im = ax.imshow(data, cmap=cmap, aspect='auto', vmin=-vmax, vmax=vmax)

        ax.set_xticks(range(len(years)))
        ax.set_xticklabels(years, fontsize=8, rotation=45)
        ax.set_yticks(range(len(active_holidays)))
        ax.set_yticklabels(active_holidays, fontsize=10)
        ax.set_title(f'{self.stock_name} 各节日节后首日涨跌热力图', fontsize=14, fontweight='bold')

        # 在格子中标注数值
        for i in range(len(active_holidays)):
            for j in range(len(years)):
                val = data[i, j]
                if not np.isnan(val):
                    color = 'white' if abs(val) > vmax * 0.6 else 'black'
                    ax.text(j, i, f'{val:.2f}%', ha='center', va='center', fontsize=7,
                            color=color, fontweight='bold')

        plt.colorbar(im, ax=ax, label='涨跌幅(%)')
        plt.tight_layout()

        plt.tight_layout()
        plt.show()


# ==================== 主程序 ====================

def get_user_input(saver=None):
    """获取用户输入"""
    log_func = saver.log if saver else print
    today = datetime.now().strftime('%Y-%m-%d')

    log_func("=== 节日涨跌分析工具 ===")
    log_func("分析主要节日（春节、国庆节等）前后7个交易日的涨跌幅度和概率")
    log_func(f"数据范围: 2008-2026年假期数据\n")
    try:
        stock_code = input("请输入股票代码（默认：000001 上证指数）: ").strip() or "000001"
    except EOFError:
        stock_code = "000001"

    try:
        stock_name = input("请输入股票名称（默认：上证指数）: ").strip() or "上证指数"
    except EOFError:
        stock_name = "上证指数"

    try:
        start_date = input("请输入起始日期（默认：2008-01-01）: ").strip() or "2008-01-01"
    except EOFError:
        start_date = "2008-01-01"

    try:
        end_date = input(f"请输入结束日期（默认：{today}）: ").strip() or today
    except EOFError:
        end_date = today

    return stock_code, stock_name, start_date, end_date


def main():
    saver = reset_saver("节日涨跌分析")
    analyzer = HolidayAnalyzer()

    # 1. 加载假日数据
    saver.log("正在加载假日数据...")
    analyzer.load_holiday_data()
    saver.log(f"已加载 {len(analyzer.holiday_events)} 个节日事件")

    # 2. 获取用户输入
    stock_code, stock_name, start_date, end_date = get_user_input(saver)
    saver.set_tag(stock_code)

    # 3. 获取K线数据
    asyncio.run(analyzer.fetch_kline_data(stock_code, stock_name, start_date, end_date))

    if analyzer.df is None or len(analyzer.df) == 0:
        saver.log("无法获取K线数据，程序退出")
        return

    saver.log(f"\n数据预览 (共{len(analyzer.df)}条):")
    saver.log(analyzer.df.head().to_string())
    saver.log(analyzer.df.tail().to_string())

    # 4. 执行分析
    analyzer.analyze_holiday(lookback=7, lookforward=7)

    # 5. 生成报告
    analyzer.generate_report(saver)

    # 6. 绘图
    analyzer.plot_holiday_analysis(lookback=7, lookforward=7)
    saver.save_chart(f"{stock_code}_节日涨跌分析.jpg")

    analyzer.plot_heatmap()
    saver.save_chart(f"{stock_code}_节日热力图.jpg")

    saver.finalize()


if __name__ == "__main__":
    main()
