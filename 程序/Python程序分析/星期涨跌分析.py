import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import asyncio
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime, timedelta
from emdata import get_quote_reader, Market, AdjustPriceType, PeriodType
from result_saver import get_saver, reset_saver

WEEK_MAP = {
    "Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三",
    "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日"
}

WEEKDAY_ORDER = ["星期一", "星期二", "星期三", "星期四", "星期五"]


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

        print(f"正在获取{stock_name}({stock_code}) {start_date}至{self.end_date}的日K线数据...")

        if stock_code == "000001" and stock_name == "上证指数":
            market_code = Market.SHANGHAI
        else:
            market_code = Market.SHANGHAI if stock_code.startswith('6') else Market.SHENGZHEN

        start_date_formatted = start_date.replace('-', '')
        end_date_formatted = end_date.replace('-', '')

        reader = get_quote_reader()

        try:
            quote = await reader.read_quote_async(
                market=market_code,
                stock_code=stock_code,
                adjust_type=AdjustPriceType.NONE,
                period_type=PeriodType.DAILY,
                end_date=end_date_formatted,
                limit=2000
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

            print(f"成功获取 {len(self.df)} 条日K线数据")
            return self.df

        except Exception as e:
            print(f"获取数据时出错: {e}")
            self.df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
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
            if len(wd_data) == 0:
                stats[wd] = {
                    'count': 0, 'up_count': 0, 'down_count': 0, 'flat_count': 0,
                    'up_pct': 0, 'down_pct': 0,
                    'mean': 0, 'median': 0, 'std': 0,
                    'max_gain': 0, 'max_loss': 0
                }
                continue

            up_count = len(wd_data[wd_data > 0])
            down_count = len(wd_data[wd_data < 0])
            flat_count = len(wd_data[wd_data == 0])
            total = len(wd_data)

            stats[wd] = {
                'count': total,
                'up_count': up_count,
                'down_count': down_count,
                'flat_count': flat_count,
                'up_pct': round(up_count / total * 100, 2) if total > 0 else 0,
                'down_pct': round(down_count / total * 100, 2) if total > 0 else 0,
                'mean': round(wd_data.mean(), 4),
                'median': round(wd_data.median(), 4),
                'std': round(wd_data.std(), 4),
                'max_gain': round(wd_data.max(), 4),
                'max_loss': round(wd_data.min(), 4)
            }

        self.weekday_stats = stats
        self._df_with_weekday = df
        return stats

    def predict_next_day(self):
        """根据下一个交易日的星期几预测涨跌概率"""
        if self.weekday_stats is None:
            print("请先执行 analyze_weekday()")
            return None

        next_date = self.df['date'].max() + timedelta(days=1)
        # 跳过周末找到下一个交易日
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)

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
            current = current + timedelta(days=1)
            while current.weekday() >= 5:
                current += timedelta(days=1)

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

    def plot_weekday_analysis(self):
        """绘制星期几涨跌分析图表"""
        if self.weekday_stats is None:
            print("请先执行 analyze_weekday()")
            return

        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

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

        log_func("=" * 70)
        log_func(f"     {self.stock_name}({self.stock_code}) 星期涨跌分析报告")
        log_func(f"     分析期间: {self.start_date} 至 {self.end_date}")
        log_func("=" * 70)

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

        log_func("=" * 70)


def get_user_input(saver=None):
    log_func = saver.log if saver else print
    today = datetime.now().strftime('%Y-%m-%d')

    log_func("=== 星期涨跌分析工具 ===")
    try:
        stock_code = input("请输入股票代码（默认：000001 上证指数）: ") or "000001"
    except EOFError:
        stock_code = "000001"

    try:
        stock_name = input("请输入股票名称（默认：上证指数）: ") or "上证指数"
    except EOFError:
        stock_name = "上证指数"

    try:
        start_date = input("请输入起始日期（默认：2008-01-01）: ") or "2008-01-01"
    except EOFError:
        start_date = "2008-01-01"

    try:
        end_date = input(f"请输入结束日期（默认：{today}）: ") or today
    except EOFError:
        end_date = today

    return stock_code, stock_name, start_date, end_date


def main():
    saver = reset_saver("星期涨跌分析")
    analyzer = WeekdayChangeAnalyzer()

    stock_code, stock_name, start_date, end_date = get_user_input(saver)
    saver.set_tag(stock_code)

    asyncio.run(analyzer.fetch_kline_data(stock_code, stock_name, start_date, end_date))

    saver.log(f"\n数据预览 (共{len(analyzer.df)}条):")
    saver.log(analyzer.df.head().to_string())

    analyzer.analyze_weekday()
    analyzer.generate_report(saver)
    analyzer.plot_weekday_analysis()

    saver.save_chart(f"{stock_code}_星期涨跌分析.jpg")
    saver.finalize()


if __name__ == "__main__":
    main()
