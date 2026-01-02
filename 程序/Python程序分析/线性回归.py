import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import asyncio
import warnings
warnings.filterwarnings('ignore')
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from datetime import datetime
from eastmoney_quote_reader import EastmoneyQuoteReader, Market, AdjustPriceType, PeriodType
from result_saver import get_saver, reset_saver

class RegressionKLineAnalyzer:
    def __init__(self):
        self.df = None
        self.model = LinearRegression()
        self.stock_name = "上证指数"  # 默认股票名称
        self.stock_code = "000001"  # 默认股票代码
        self.period = "daily"  # 默认周期：daily, weekly, monthly
        self.start_date = None
        self.end_date = None
        
    async def fetch_kline_data(self, stock_code="000001", stock_name="上证指数", start_date="2007-01-01", end_date="2025-12-31", period="daily"):
        """
        获取K线数据（使用东方财富API获取真实数据）
        
        参数:
        - stock_code: 股票代码
        - stock_name: 股票名称
        - start_date: 起始日期，格式：YYYY-MM-DD
        - end_date: 结束日期，格式：YYYY-MM-DD
        - period: 时间周期，可选：daily, weekly, monthly
        """
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.start_date = start_date
        self.end_date = end_date
        self.period = period
        
        print(f"正在获取{stock_name}({stock_code}) {start_date}至{end_date}的{period}K线数据...")
        
        # 转换周期类型和股票代码
        # 确定股票所属市场（上海或深圳）
        if stock_code == "000001" and stock_name == "上证指数":
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

    def prepare_features(self):
        """准备特征数据"""
        # 转换日期为年份
        self.df['year'] = pd.to_datetime(self.df['date']).dt.year
        X = self.df[['year']].values
        y = self.df[['close']].values
        return X, y
    
    def train_model(self):
        """训练线性回归模型"""
        X, y = self.prepare_features()
        self.model.fit(X, y)
        
        # 计算R²分数
        y_pred = self.model.predict(X)
        r2 = r2_score(y, y_pred)
        
        print(f"线性回归模型训练完成")
        print(f"回归方程: y = {self.model.coef_[0][0]:.2f}x + {self.model.intercept_[0]:.2f}")
        print(f"R²分数: {r2:.4f}")
        
        return self.model
    
    def predict_future(self, future_periods=5):
        """预测未来几期的指数"""
        # 获取当前最大日期
        current_date = pd.to_datetime(self.df['date'].max())
        
        # 根据周期类型确定日期增量
        if self.period == "daily":
            future_dates = [current_date + pd.Timedelta(days=i) for i in range(1, future_periods + 1)]
        elif self.period == "weekly":
            future_dates = [current_date + pd.Timedelta(weeks=i) for i in range(1, future_periods + 1)]
        elif self.period == "monthly":
            future_dates = [current_date + pd.DateOffset(months=i) for i in range(1, future_periods + 1)]
        else:
            # 默认按日计算
            future_dates = [current_date + pd.Timedelta(days=i) for i in range(1, future_periods + 1)]
        
        # 提取年份
        future_years = [date.year for date in future_dates]
        
        future_X = np.array(future_years).reshape(-1, 1)
        future_predictions = self.model.predict(future_X)
        
        predictions_df = pd.DataFrame({
            'date': future_dates,
            'year': future_years,
            'predicted_close': [round(pred[0], 2) for pred in future_predictions]
        })
        
        return predictions_df
    
    def calculate_annual_return(self):
        """计算年化收益率"""
        # 按日期排序
        self.df = self.df.sort_values('date')
        # 计算年度收益（假设数据是按年度聚合的）
        self.df['annual_return'] = self.df['close'].pct_change() * 100
        self.df['cumulative_return'] = (1 + self.df['close'].pct_change()).cumprod().fillna(1)
        
        total_periods = len(self.df) - 1
        total_return = (self.df['close'].iloc[-1] / self.df['close'].iloc[0] - 1) * 100
        
        # 根据周期计算年化收益率
        if self.period == "daily":
            # 假设每年有250个交易日
            periods_per_year = 250
            annualized_return = (self.df['close'].iloc[-1] / self.df['close'].iloc[0]) ** (periods_per_year/total_periods) - 1
        elif self.period == "weekly":
            # 假设每年有52周
            periods_per_year = 52
            annualized_return = (self.df['close'].iloc[-1] / self.df['close'].iloc[0]) ** (periods_per_year/total_periods) - 1
        elif self.period == "monthly":
            # 假设每年有12个月
            periods_per_year = 12
            annualized_return = (self.df['close'].iloc[-1] / self.df['close'].iloc[0]) ** (periods_per_year/total_periods) - 1
        else:
            # 默认处理
            annualized_return = (self.df['close'].iloc[-1] / self.df['close'].iloc[0]) ** (1/(total_periods/periods_per_year)) - 1
        
        print(f"\n收益率分析:")
        print(f"总收益率: {total_return:.2f}%")
        print(f"年化收益率: {annualized_return*100:.2f}%")
        print(f"分析周期: {self.df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {self.df['date'].iloc[-1].strftime('%Y-%m-%d')}")
        
        return annualized_return
    
    def plot_analysis(self, future_predictions=None):
        """绘制分析图表"""
        # 设置中文字体以避免乱码
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
        
        fig = plt.figure(figsize=(16, 12))
        
        # 子图1: K线趋势
        ax1 = plt.subplot(2, 2, 1)
        for i, row in self.df.iterrows():
            color = 'red' if row['close'] >= row['open'] else 'green'
            plt.plot([i, i], [row['low'], row['high']], color='black', linewidth=1)
            plt.plot([i, i], [row['open'], row['close']], color=color, linewidth=3)
        
        # 绘制回归线
        X = self.df[['year']].values
        y_pred = self.model.predict(X)
        plt.plot(range(len(self.df)), y_pred, 'b-', linewidth=2, label='线性回归趋势线')
        
        plt.title(f'{self.stock_name}({self.stock_code}){self.period}K线及线性回归趋势')
        plt.xlabel('时间')
        plt.ylabel('指数点位')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2: 收益率
        ax2 = plt.subplot(2, 2, 2)
        colors = ['red' if x >= 0 else 'green' for x in self.df['annual_return'].fillna(0)]
        plt.bar(range(len(self.df)), self.df['annual_return'].fillna(0), color=colors, alpha=0.7)
        plt.title('收益率(%)')
        plt.xlabel('时间')
        plt.ylabel('收益率(%)')
        plt.grid(True, alpha=0.3)
        
        # 子图3: 累积收益率
        ax3 = plt.subplot(2, 2, 3)
        plt.plot(range(len(self.df)), self.df['cumulative_return'], 'purple', linewidth=2)
        plt.title('累积收益率')
        plt.xlabel('时间')
        plt.ylabel('累积收益倍数')
        plt.grid(True, alpha=0.3)
        
        # 子图4: 未来预测
        ax4 = plt.subplot(2, 2, 4)
        plt.plot(range(len(self.df)), self.df['close'], 'ko-', label='历史数据', markersize=4)
        
        if future_predictions is not None:
            # 连接历史数据和预测数据
            last_index = len(self.df) - 1
            extended_indices = [last_index] + list(range(last_index + 1, last_index + len(future_predictions) + 1))
            
            # 创建扩展的日期序列
            extended_dates = list(range(len(self.df))) + list(range(len(self.df), len(self.df) + len(future_predictions)))
            
            # 合并历史数据和预测数据
            combined_values = list(self.df['close']) + list(future_predictions['predicted_close'])
            
            # 绘制合并后的数据
            plt.plot(extended_dates, combined_values, 'ko-', label='历史数据', markersize=4)
            plt.plot(extended_dates[len(self.df):], future_predictions['predicted_close'], 
                    'ro--', label='预测数据', markersize=4)
            
            # 标注预测值
            for i, row in future_predictions.iterrows():
                plt.annotate(f"{row['predicted_close']:.2f}", 
                           (extended_dates[len(self.df) + i], row['predicted_close']),
                           textcoords="offset points", xytext=(0,10), ha='center')
            
            # 延长回归线到预测期
            extended_years = list(self.df['year']) + list(future_predictions['year'])
            extended_X = np.array(extended_years).reshape(-1, 1)
            extended_pred = self.model.predict(extended_X)
            plt.plot(extended_dates, extended_pred, 'b--', alpha=0.7, label='回归趋势延长线')
        
        plt.title(f'{self.stock_name}({self.stock_code})历史数据与未来预测')
        plt.xlabel('时间')
        plt.ylabel('指数点位')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(script_dir, f"{self.stock_code}_线性回归分析.jpg")
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
        
        plt.show()
    
    def generate_report(self, saver=None):
        """生成分析报告"""
        log_func = saver.log if saver else print
        
        log_func("=" * 70)
        log_func(f"           {self.stock_name}({self.stock_code}){self.period}K线线性回归分析报告")
        log_func(f"           分析期间: {self.start_date} 至 {self.end_date}")
        log_func("=" * 70)
        
        # 基本统计信息
        log_func(f"\n1. 基本统计信息:")
        log_func(f"   股票名称: {self.stock_name}")
        log_func(f"   股票代码: {self.stock_code}")
        log_func(f"   分析周期: {self.period}")
        log_func(f"   数据条数: {len(self.df)} 条")
        log_func(f"   数据期间: {self.df['date'].min().strftime('%Y-%m-%d')} 至 {self.df['date'].max().strftime('%Y-%m-%d')}")
        log_func(f"   最新收盘: {self.df['close'].iloc[-1]:.2f} 点")
        log_func(f"   历史最高: {self.df['high'].max():.2f} 点")
        log_func(f"   历史最低: {self.df['low'].min():.2f} 点")
        
        # 回归分析结果
        log_func(f"\n2. 线性回归分析:")
        log_func(f"   回归方程: y = {self.model.coef_[0][0]:.2f}x + {self.model.intercept_[0]:.2f}")
        
        # 根据周期计算增长率
        if self.period == "daily":
            growth_per_period = self.model.coef_[0][0]
            periods_per_year = 250
            growth_per_year = growth_per_period * periods_per_year
            log_func(f"   平均增长: {growth_per_period:.2f} 点/日 ({growth_per_year:.2f} 点/年)")
        elif self.period == "weekly":
            growth_per_period = self.model.coef_[0][0]
            periods_per_year = 52
            growth_per_year = growth_per_period * periods_per_year
            log_func(f"   平均增长: {growth_per_period:.2f} 点/周 ({growth_per_year:.2f} 点/年)")
        elif self.period == "monthly":
            growth_per_period = self.model.coef_[0][0]
            periods_per_year = 12
            growth_per_year = growth_per_period * periods_per_year
            log_func(f"   平均增长: {growth_per_period:.2f} 点/月 ({growth_per_year:.2f} 点/年)")
        else:
            log_func(f"   平均增长: {self.model.coef_[0][0]:.2f} 点/期")
        
        # 预测未来
        future_predictions = self.predict_future(5)
        log_func(f"\n3. 未来5期预测:")
        for _, row in future_predictions.iterrows():
            log_func(f"   {row['date'].strftime('%Y-%m-%d')}预测: {row['predicted_close']:.2f} 点")
        
        # 投资建议
        log_func(f"\n4. 分析结论:")
        slope = self.model.coef_[0][0]
        
        # 根据周期调整判断标准
        if self.period == "daily":
            if slope > 1:
                trend = "强劲上升"
                suggestion = "长期看好"
            elif slope > 0.5:
                trend = "稳步上升" 
                suggestion = "适合长期投资"
            elif slope > 0:
                trend = "缓慢上升"
                suggestion = "谨慎乐观"
            else:
                trend = "下降趋势"
                suggestion = "注意风险"
        elif self.period == "weekly":
            if slope > 5:
                trend = "强劲上升"
                suggestion = "长期看好"
            elif slope > 2:
                trend = "稳步上升" 
                suggestion = "适合长期投资"
            elif slope > 0:
                trend = "缓慢上升"
                suggestion = "谨慎乐观"
            else:
                trend = "下降趋势"
                suggestion = "注意风险"
        elif self.period == "monthly":
            if slope > 20:
                trend = "强劲上升"
                suggestion = "长期看好"
            elif slope > 10:
                trend = "稳步上升" 
                suggestion = "适合长期投资"
            elif slope > 0:
                trend = "缓慢上升"
                suggestion = "谨慎乐观"
            else:
                trend = "下降趋势"
                suggestion = "注意风险"
        else:
            if slope > 50:
                trend = "强劲上升"
                suggestion = "长期看好"
            elif slope > 20:
                trend = "稳步上升" 
                suggestion = "适合长期投资"
            elif slope > 0:
                trend = "缓慢上升"
                suggestion = "谨慎乐观"
            else:
                trend = "下降趋势"
                suggestion = "注意风险"
            
        log_func(f"   长期趋势: {trend}")
        log_func(f"   投资建议: {suggestion}")

def get_user_input(saver=None):
    """
    获取用户输入的通用函数
    """
    log_func = saver.log if saver else print
    
    # 获取当前日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 获取用户输入
    log_func("欢迎使用股票K线线性回归分析工具！")
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
    saver = reset_saver("线性回归")
    
    analyzer = RegressionKLineAnalyzer()
    
    # 获取用户输入
    stock_code, stock_name, start_date, end_date, period = get_user_input(saver)
    
    # 获取数据（异步调用）
    df = asyncio.run(analyzer.fetch_kline_data(stock_code, stock_name, start_date, end_date, period))
    
    if df is None or df.empty:
        saver.log("未能获取到有效数据，分析终止。")
        return
    
    saver.log("数据预览:")
    saver.log(df.head().to_string())
    
    # 训练模型
    analyzer.train_model()
    
    # 计算收益率
    analyzer.calculate_annual_return()
    
    # 预测未来
    future_predictions = analyzer.predict_future(5)
    
    # 生成报告
    analyzer.generate_report(saver)
    
    # 绘制图表
    analyzer.plot_analysis(future_predictions)
    
    # 保存图表
    saver.save_chart("线性回归_图表.jpg")
    
    # 完成分析
    saver.finalize()

if __name__ == "__main__":
    main()