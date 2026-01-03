import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import asyncio
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime
from eastmoney_quote_reader import EastmoneyQuoteReader, Market, AdjustPriceType, PeriodType
from result_saver import get_saver, reset_saver

class BasicKLineAnalyzer:
    def __init__(self):
        self.df = None
        self.stock_name = "上证指数"  # 默认股票名称
        self.stock_code = "000001"  # 默认股票代码
        self.period = "daily"  # 默认周期：daily, weekly, monthly
        self.start_date = None
        self.end_date = None
    
    async def fetch_kline_data(self, stock_code="000001", stock_name="上证指数", start_date="2008-01-01", end_date="", period="daily"):
        """
        获取K线数据（使用东方财富API获取真实数据）
        
        参数:
        - stock_code: 股票代码
        - stock_name: 股票名称
        - start_date: 起始日期，格式：YYYY-MM-DD
        - end_date: 结束日期，格式：YYYY-MM-DD，默认为当前日期
        - period: 时间周期，可选：daily, weekly, monthly
        """
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.period = period
        
        print(f"正在获取{stock_name}({stock_code}) {start_date}至{self.end_date}的{period}K线数据...")
   
        # 转换周期类型和股票代码
        # 确定股票所属市场（上海或深圳）
        if stock_code == "000001" and stock_name == "上证指数":
            market_code = Market.SHANGHAI
        else:
            if stock_code.startswith('6'):
                market_code = Market.SHANGHAI
            else:
                market_code = Market.SHENGZHEN
        
        # 转换周期类型
        period_mapping = {
            'daily': PeriodType.DAILY,
            'weekly': PeriodType.WEEKLY,
            'monthly': PeriodType.MONTHLY
        }
        period_type = period_mapping.get(period.lower(), PeriodType.DAILY)
        
        # 转换日期格式为YYYYMMDD
        start_date_formatted = start_date.replace('-', '')
        end_date_formatted = end_date.replace('-', '')
        
        # 创建行情读取器
        reader = EastmoneyQuoteReader()
        
        try:
            # 获取行情数据
            quote = await reader.read_quote_async(
                market=market_code,
                stock_code=stock_code,
                adjust_type=AdjustPriceType.NONE,
                period_type=period_type,
                end_date=end_date_formatted,
                limit=2000
            )
            
            if quote is None:
                print(f"无法获取{stock_name}({stock_code})的数据")
                # 创建一个空的DataFrame作为示例
                self.df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                return self.df
            
            # 转换行情数据为DataFrame格式
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
            # 按日期排序
            self.df = self.df.sort_values('date').reset_index(drop=True)
            
            # 过滤指定日期范围的数据
            if start_date or end_date:
                start_date_obj = pd.to_datetime(start_date)
                end_date_obj = pd.to_datetime(end_date)
                self.df = self.df[(self.df['date'] >= start_date_obj) & (self.df['date'] <= end_date_obj)]
            
            print(f"成功获取 {len(self.df)} 条{period}K线数据")
            return self.df
            
        except Exception as e:
            print(f"获取{stock_name}({stock_code})数据时出错: {e}")
            # 创建一个空的DataFrame作为示例
            self.df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
            return self.df
    
    def analyze_kline(self):
        """
        分析K线数据，计算最大值、最小值、幅度等
        """
        if self.df is None:
            print("请先获取K线数据")
            return None
        
        # 计算基本统计信息
        stats = {}
        
        # 最高价分析
        stats['high_price'] = self.df['high'].max()
        stats['high_date'] = self.df.loc[self.df['high'].idxmax(), 'date'].strftime('%Y-%m-%d')
        
        # 最低价分析
        stats['low_price'] = self.df['low'].min()
        stats['low_date'] = self.df.loc[self.df['low'].idxmin(), 'date'].strftime('%Y-%m-%d')
        
        # 价格波动幅度
        stats['price_range'] = stats['high_price'] - stats['low_price']
        stats['price_range_pct'] = (stats['price_range'] / self.df['close'].mean()) * 100
        
        # 收盘价分析
        stats['start_close'] = self.df['close'].iloc[0]
        stats['end_close'] = self.df['close'].iloc[-1]
        stats['total_change'] = stats['end_close'] - stats['start_close']
        stats['total_change_pct'] = (stats['total_change'] / stats['start_close']) * 100
        
        # 日均涨跌幅
        self.df['change_pct'] = self.df['close'].pct_change() * 100
        stats['avg_change_pct'] = self.df['change_pct'].mean()
        stats['max_daily_gain'] = self.df['change_pct'].max()
        stats['max_daily_loss'] = self.df['change_pct'].min()
        
        # 涨跌天数统计
        stats['up_days'] = len(self.df[self.df['change_pct'] > 0])
        stats['down_days'] = len(self.df[self.df['change_pct'] < 0])
        stats['flat_days'] = len(self.df[self.df['change_pct'] == 0])
        
        # 保存统计结果
        self.stats = stats
        return stats
    
    def plot_kline_analysis(self):
        """
        绘制K线分析图表
        """
        if self.df is None:
            print("请先获取K线数据")
            return
        
        # 设置中文字体以避免乱码
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
        
        fig = plt.figure(figsize=(16, 12))
        
        # 子图1: K线图（带最高价、最低价标记）
        ax1 = plt.subplot(3, 2, 1)
        
        # 绘制K线
        for i, row in self.df.iterrows():
            color = 'red' if row['close'] >= row['open'] else 'green'
            plt.plot([i, i], [row['low'], row['high']], color='black', linewidth=1)
            plt.plot([i, i], [row['open'], row['close']], color=color, linewidth=3)
        
        # 标记最高价和最低价
        high_idx = self.df['high'].idxmax()
        low_idx = self.df['low'].idxmin()
        
        plt.scatter(high_idx, self.df.loc[high_idx, 'high'], color='red', marker='^', s=100, label=f'最高价: {self.stats["high_price"]:.2f}')
        plt.scatter(low_idx, self.df.loc[low_idx, 'low'], color='green', marker='v', s=100, label=f'最低价: {self.stats["low_price"]:.2f}')
        
        # 绘制收盘价趋势线
        z = np.polyfit(range(len(self.df)), self.df['close'], 1)
        p = np.poly1d(z)
        plt.plot(range(len(self.df)), p(range(len(self.df))), 'b--', linewidth=2, label='收盘价趋势线')
        
        # 设置x轴标签
        ax1.set_xticks(range(0, len(self.df), max(1, len(self.df) // 10)))
        ax1.set_xticklabels([self.df.iloc[i]['date'].strftime('%Y-%m-%d') for i in range(0, len(self.df), max(1, len(self.df) // 10))], rotation=45)
        
        plt.title(f'{self.stock_name}({self.stock_code}){self.period}K线图')
        plt.xlabel('日期')
        plt.ylabel('价格')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2: 价格波动幅度
        ax2 = plt.subplot(3, 2, 2)
        price_ranges = self.df['high'] - self.df['low']
        plt.bar(range(len(self.df)), price_ranges, alpha=0.7, color='orange', label='当日波动幅度')
        plt.axhline(y=price_ranges.mean(), color='blue', linestyle='--', label=f'平均幅度: {price_ranges.mean():.2f}')
        
        ax2.set_xticks(range(0, len(self.df), max(1, len(self.df) // 10)))
        ax2.set_xticklabels([self.df.iloc[i]['date'].strftime('%Y-%m-%d') for i in range(0, len(self.df), max(1, len(self.df) // 10))], rotation=45)
        
        plt.title('价格波动幅度')
        plt.xlabel('日期')
        plt.ylabel('波动幅度')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图3: 涨跌幅分布直方图
        ax3 = plt.subplot(3, 2, 3)
        plt.hist(self.df['change_pct'].dropna(), bins=20, alpha=0.7, color='purple')
        plt.axvline(x=self.df['change_pct'].mean(), color='red', linestyle='--', label=f'平均涨跌幅: {self.stats["avg_change_pct"]:.2f}%')
        plt.title('涨跌幅分布')
        plt.xlabel('涨跌幅(%)')
        plt.ylabel('频数')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图4: 累计涨跌幅
        ax4 = plt.subplot(3, 2, 4)
        cumulative_returns = (1 + self.df['change_pct'] / 100).cumprod() * 100 - 100
        plt.plot(range(len(self.df)), cumulative_returns, color='green', linewidth=2)
        plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
        ax4.set_xticks(range(0, len(self.df), max(1, len(self.df) // 10)))
        ax4.set_xticklabels([self.df.iloc[i]['date'].strftime('%Y-%m-%d') for i in range(0, len(self.df), max(1, len(self.df) // 10))], rotation=45)
        
        plt.title('累计涨跌幅(%)')
        plt.xlabel('日期')
        plt.ylabel('累计涨跌幅(%)')
        plt.grid(True, alpha=0.3)
        
        # 子图5: OHLC统计
        ax5 = plt.subplot(3, 2, 5)
        ohlc_means = [self.df['open'].mean(), self.df['high'].mean(), self.df['low'].mean(), self.df['close'].mean()]
        ohlc_labels = ['开盘价', '最高价', '最低价', '收盘价']
        bars = plt.bar(ohlc_labels, ohlc_means, color=['blue', 'red', 'green', 'purple'], alpha=0.7)
        
        # 在柱状图上标注数值
        for bar in bars:
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height + 5, f'{height:.2f}', ha='center', va='bottom')
        
        plt.title('价格均值统计')
        plt.ylabel('价格')
        plt.grid(True, alpha=0.3)
        
        # 子图6: 涨跌天数统计
        ax6 = plt.subplot(3, 2, 6)
        up_down_data = [self.stats['up_days'], self.stats['down_days'], self.stats['flat_days']]
        up_down_labels = ['上涨天数', '下跌天数', '平盘天数']
        colors = ['red', 'green', 'gray']
        bars = plt.bar(up_down_labels, up_down_data, color=colors, alpha=0.7)
        
        # 在柱状图上标注数值
        for bar in bars:
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height + 0.5, f'{int(height)}', ha='center', va='bottom')
        
        plt.title('涨跌天数统计')
        plt.ylabel('天数')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(script_dir, f"{self.stock_code}_K线分析.jpg")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
        
        plt.show()
    
    def generate_kline_report(self, saver=None):
        """
        生成K线分析报告
        
        Args:
            saver: 结果保存器实例，如果为None则直接打印
        """
        if self.df is None or not hasattr(self, 'stats'):
            message = "请先获取K线数据并进行分析"
            if saver:
                saver.log(message)
            else:
                print(message)
            return
        
        log_func = saver.log if saver else print
        
        log_func("=" * 70)
        log_func(f"           {self.stock_name}({self.stock_code}){self.period}K线分析报告")
        log_func(f"           分析期间: {self.start_date} 至 {self.end_date}")
        log_func("=" * 70)
        
        # 基本信息
        log_func(f"\n1. 基本信息:")
        log_func(f"   股票名称: {self.stock_name}")
        log_func(f"   股票代码: {self.stock_code}")
        log_func(f"   分析周期: {self.period}")
        log_func(f"   数据条数: {len(self.df)} 条")
        
        # 价格统计
        log_func(f"\n2. 价格统计:")
        log_func(f"   最高价: {self.stats['high_price']:.2f} （{self.stats['high_date']}）")
        log_func(f"   最低价: {self.stats['low_price']:.2f} （{self.stats['low_date']}）")
        log_func(f"   价格区间: {self.stats['price_range']:.2f} 点")
        log_func(f"   价格区间占比: {self.stats['price_range_pct']:.2f}%")
        log_func(f"   期初收盘价: {self.stats['start_close']:.2f}")
        log_func(f"   期末收盘价: {self.stats['end_close']:.2f}")
        log_func(f"   总涨跌幅: {self.stats['total_change_pct']:.2f}%")
        
        # 涨跌幅统计
        log_func(f"\n3. 涨跌幅统计:")
        log_func(f"   日均涨跌幅: {self.stats['avg_change_pct']:.2f}%")
        log_func(f"   最大单日涨幅: {self.stats['max_daily_gain']:.2f}%")
        log_func(f"   最大单日跌幅: {self.stats['max_daily_loss']:.2f}%")
        log_func(f"   上涨天数: {self.stats['up_days']} 天")
        log_func(f"   下跌天数: {self.stats['down_days']} 天")
        log_func(f"   平盘天数: {self.stats['flat_days']} 天")
        
        # 涨跌比例
        total_days = self.stats['up_days'] + self.stats['down_days'] + self.stats['flat_days']
        if total_days > 0:
            up_ratio = (self.stats['up_days'] / total_days) * 100
            down_ratio = (self.stats['down_days'] / total_days) * 100
            log_func(f"   上涨概率: {up_ratio:.2f}%")
            log_func(f"   下跌概率: {down_ratio:.2f}%")
        
        # 趋势分析
        log_func(f"\n4. 趋势分析:")
        if self.stats['total_change_pct'] > 20:
            trend = "强劲上涨"
        elif self.stats['total_change_pct'] > 5:
            trend = "温和上涨"
        elif self.stats['total_change_pct'] > -5:
            trend = "震荡整理"
        elif self.stats['total_change_pct'] > -20:
            trend = "温和下跌"
        else:
            trend = "大幅下跌"
        
        log_func(f"   整体趋势: {trend}")
        
        # 投资建议
        log_func(f"\n5. 投资建议:")
        if trend in ["强劲上涨", "温和上涨"]:
            suggestion = "建议逢低买入，长期持有"
        elif trend == "震荡整理":
            suggestion = "建议高抛低吸，短线操作"
        else:
            suggestion = "建议谨慎观望，控制风险"
        
        log_func(f"   {suggestion}")
        log_func("=" * 70)

def get_user_input(saver=None):
    """
    获取用户输入的通用函数
    
    Args:
        saver: 结果保存器实例，用于记录用户输入
    """
    log_func = saver.log if saver else print
    
    # 获取当前日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 获取用户输入
    log_func("欢迎使用股票K线分析工具！")
    try:
        stock_code = input("请输入股票代码（默认：000001）: ") or "000001"
    except EOFError:
        stock_code = "000001"
    
    try:
        stock_name = input("请输入股票名称（默认：上证指数）: ") or "上证指数"
    except EOFError:
        stock_name = "上证指数"
    
    try:
        start_date = input("请输入起始日期（默认：2008-01-01，格式：YYYY-MM-DD）: ") or "2008-01-01"
    except EOFError:
        start_date = "2008-01-01"
    
    try:
        end_date = input(f"请输入结束日期（默认：{today}，格式：YYYY-MM-DD）: ") or today
    except EOFError:
        end_date = today
    
    # 选择周期
    log_func("\n请选择分析周期：")
    log_func("1. 日线")
    log_func("2. 周线")
    log_func("3. 月线")
    
    try:
        period_choice = input("请输入选项（默认：1）: ") or "1"
    except EOFError:
        period_choice = "1"
    
    period_map = {"1": "daily", "2": "weekly", "3": "monthly"}
    period = period_map.get(period_choice, "daily")
    
    return stock_code, stock_name, start_date, end_date, period

def main():
    """
    主函数，提供用户交互
    """
    # 初始化结果保存器
    saver = reset_saver("股票K线分析")
    
    analyzer = BasicKLineAnalyzer()
    
    # 获取用户输入
    stock_code, stock_name, start_date, end_date, period = get_user_input(saver)
    
    # 获取数据（异步调用）
    df = asyncio.run(analyzer.fetch_kline_data(stock_code, stock_name, start_date, end_date, period))
    
    saver.log("数据预览:")
    saver.log(df.head().to_string())
    
    # 分析数据
    stats = analyzer.analyze_kline()
    
    # 生成报告
    analyzer.generate_kline_report(saver)
    
    # 绘制图表
    analyzer.plot_kline_analysis()
    
    # 保存图表
    saver.save_chart("股票K线分析_图表.jpg")
    
    # 完成分析
    saver.finalize()

if __name__ == "__main__":
    main()
