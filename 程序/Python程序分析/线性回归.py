import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score 
import warnings
warnings.filterwarnings('ignore')

class StockAnalyzer:
    def __init__(self):
        self.df = None
        self.model = LinearRegression()
        self.stock_name = "上证指数"  # 默认股票名称
        
    def fetch_data(self, start_year=1990, stock_name="上证指数", stock_code="000001"):
        """
        获取股票历史数据
        由于tushare需要token，这里我们模拟一些数据
        
        参数:
        - start_year: 起始年份
        - stock_name: 股票名称
        - stock_code: 股票代码
        """
        self.stock_name = stock_name  # 更新股票名称
        self.stock_code = stock_code  # 保存股票代码
        print(f"正在获取{stock_name}({stock_code})数据...")
        
        years = list(range(1990, 2025))
        
        raw_data = [
            ["1990-12-31", 96.05, 127.61, 127.61, 95.79],
            ["1991-12-31", 127.61, 292.75, 292.75, 104.96],
            ["1992-12-31", 293.74, 780.39, 1429.01, 292.76],
            ["1993-12-31", 784.13, 833.80, 1558.95, 750.46],
            ["1994-12-30", 837.70, 647.87, 1052.94, 325.89],
            ["1995-12-29", 637.72, 555.29, 926.41, 524.43],
            ["1996-12-31", 550.26, 917.01, 1258.68, 512.83],
            ["1997-12-31", 914.06, 1194.10, 1510.17, 870.18],
            ["1998-12-31", 1200.94, 1146.70, 1422.97, 1043.02],
            ["1999-12-30", 1144.88, 1366.58, 1756.18, 1047.83],
            ["2000-12-29", 1368.69, 2073.47, 2125.72, 1361.21],
            ["2001-12-31", 2077.07, 1645.97, 2245.43, 1514.86],
            ["2002-12-31", 1643.48, 1357.65, 1748.89, 1339.20],
            ["2003-12-31", 1347.43, 1497.04, 1649.60, 1307.40],
            ["2004-12-31", 1492.72, 1266.50, 1783.01, 1259.43],
            ["2005-12-30", 1260.78, 1161.06, 1328.53, 998.23],
            ["2006-12-29", 1163.88, 2675.47, 2698.90, 1161.91],
            ["2007-12-28", 2728.19, 5261.56, 6124.04, 2541.52],
            ["2008-12-31", 5265.00, 1820.81, 5522.78, 1664.93],
            ["2009-12-31", 1849.02, 3277.14, 3478.01, 1844.09],
            ["2010-12-31", 3289.75, 2808.08, 3306.75, 2319.74],
            ["2011-12-30", 2825.33, 2199.42, 3067.46, 2134.02],
            ["2012-12-31", 2212.00, 2269.13, 2478.38, 1949.46],
            ["2013-12-31", 2289.51, 2115.98, 2444.80, 1849.65],
            ["2014-12-31", 2112.13, 3234.68, 3239.36, 1974.38],
            ["2015-12-31", 3258.63, 3539.18, 5178.19, 2850.71],
            ["2016-12-30", 3536.59, 3103.64, 3538.69, 2638.30],
            ["2017-12-29", 3105.31, 3307.17, 3450.49, 3016.53],
            ["2018-12-28", 3314.03, 2493.90, 3587.03, 2449.20],
            ["2019-12-31", 2497.88, 3050.12, 3288.45, 2440.91],
            ["2020-12-31", 3066.34, 3473.07, 3474.92, 2646.80],
            ["2021-12-31", 3474.68, 3639.78, 3731.69, 3312.72],
            ["2022-12-30", 3649.15, 3089.26, 3651.89, 2863.65],
            ["2023-12-29", 3087.51, 2974.93, 3418.95, 2882.02],
            ["2024-12-31", 2972.78, 3351.76, 3674.40, 2635.09],
            ["2025-11-28", 3347.94, 3888.60, 4034.08, 3040.69]
        ]
        
        # 使用已有的历史数据而不是随机生成
        quote_line = []
        # 将data中的数据转换为所需格式
        for i, data_row in enumerate(raw_data):
            date_str = data_row[0]  # 日期
            year = int(date_str.split('-')[0])  # 从日期中提取年份
            open_price = data_row[1]  # 开盘价
            close_price = data_row[2]  # 收盘价
            high_price = data_row[3]  # 最高价
            low_price = data_row[4]  # 最低价
            
            quote_line.append({
                'year': year,
                'open': open_price,
                'close': close_price,
                'high': high_price,
                'low': low_price
            })
        
        # 如果历史数据不足，使用现有数据的最后一条进行填充
        if len(quote_line) < len(years):
            last_data = quote_line[-1].copy()
            for i in range(len(quote_line), len(years)):
                new_entry = last_data.copy()
                new_entry['year'] = years[i]
                quote_line.append(new_entry)
        
        self.df = pd.DataFrame(quote_line)
        print(f"成功获取 {len(self.df)} 年的数据")
        return self.df
    
    def prepare_features(self):
        """准备特征数据"""
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
    
    def predict_future(self, future_years=5):
        """预测未来几年的指数"""
        current_year = self.df['year'].max()
        future_years_list = list(range(current_year + 1, current_year + future_years + 1))
        
        future_X = np.array(future_years_list).reshape(-1, 1)
        future_predictions = self.model.predict(future_X)
        
        predictions_df = pd.DataFrame({
            'year': future_years_list,
            'predicted_close': [round(pred[0], 2) for pred in future_predictions]
        })
        
        return predictions_df
    
    def calculate_annual_return(self):
        """计算年化收益率"""
        self.df = self.df.sort_values('year')
        self.df['annual_return'] = self.df['close'].pct_change() * 100
        self.df['cumulative_return'] = (1 + self.df['close'].pct_change()).cumprod().fillna(1)
        
        total_years = len(self.df) - 1
        total_return = (self.df['close'].iloc[-1] / self.df['close'].iloc[0] - 1) * 100
        annualized_return = (self.df['close'].iloc[-1] / self.df['close'].iloc[0]) ** (1/total_years) - 1
        
        print(f"\n收益率分析:")
        print(f"总收益率: {total_return:.2f}%")
        print(f"年化收益率: {annualized_return*100:.2f}%")
        print(f"分析周期: {self.df['year'].iloc[0]}年 - {self.df['year'].iloc[-1]}年")
        
        return annualized_return
    
    def plot_analysis(self, future_predictions=None):
        """绘制分析图表"""
        # 设置中文字体以避免乱码
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
        plt.figure(figsize=(15, 12))
        
        # 子图1: 年K线趋势
        plt.subplot(2, 2, 1)
        for i, row in self.df.iterrows():
            color = 'red' if row['close'] >= row['open'] else 'green'
            plt.plot([row['year'], row['year']], [row['low'], row['high']], color='black', linewidth=1)
            plt.plot([row['year'], row['year']], [row['open'], row['close']], color=color, linewidth=3)
        
        # 绘制回归线
        X = self.df[['year']].values
        y_pred = self.model.predict(X)
        plt.plot(self.df['year'], y_pred, 'b-', linewidth=2, label='线性回归趋势线')
        
        plt.title(f'{self.stock_name}年K线及线性回归趋势')
        plt.xlabel('年份')
        plt.ylabel('指数点位')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2: 年度收益率
        plt.subplot(2, 2, 2)
        colors = ['red' if x >= 0 else 'green' for x in self.df['annual_return'].fillna(0)]
        plt.bar(self.df['year'], self.df['annual_return'].fillna(0), color=colors, alpha=0.7)
        plt.title('年度收益率(%)')
        plt.xlabel('年份')
        plt.ylabel('收益率(%)')
        plt.grid(True, alpha=0.3)
        
        # 子图3: 累积收益率
        plt.subplot(2, 2, 3)
        plt.plot(self.df['year'], self.df['cumulative_return'], 'purple', linewidth=2)
        plt.title('累积收益率')
        plt.xlabel('年份')
        plt.ylabel('累积收益倍数')
        plt.grid(True, alpha=0.3)
        
        # 子图4: 未来预测
        plt.subplot(2, 2, 4)
        plt.plot(self.df['year'], self.df['close'], 'ko-', label='历史数据', markersize=4)
        
        if future_predictions is not None:
            plt.plot(future_predictions['year'], future_predictions['predicted_close'], 
                    'ro--', label='预测数据', markersize=4)
            
            # 标注预测值
            for i, row in future_predictions.iterrows():
                plt.annotate(f"{row['predicted_close']}", 
                           (row['year'], row['predicted_close']),
                           textcoords="offset points", xytext=(0,10), ha='center')
        
        # 延长回归线到预测年份
        if future_predictions is not None:
            extended_years = list(self.df['year']) + list(future_predictions['year'])
            extended_X = np.array(extended_years).reshape(-1, 1)
            extended_pred = self.model.predict(extended_X)
            plt.plot(extended_years, extended_pred, 'b--', alpha=0.7, label='回归趋势延长线')
        
        plt.title(f'{self.stock_name}历史数据与未来预测')
        plt.xlabel('年份')
        plt.ylabel('指数点位')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建图片保存路径
        save_path = os.path.join(script_dir, "线性回归.jpg")
        plt.savefig(save_path)
        plt.show()
    
    def generate_report(self):
        """生成分析报告"""
        print("=" * 60)
        print(f"           {self.stock_name}({self.stock_code})年K线线性回归分析报告")
        print("=" * 60)
        
        # 基本统计信息
        print(f"\n1. 基本统计信息:")
        print(f"   数据期间: {self.df['year'].min()}年 - {self.df['year'].max()}年")
        print(f"   最新收盘: {self.df['close'].iloc[-1]:.2f} 点")
        print(f"   历史最高: {self.df['high'].max():.2f} 点")
        print(f"   历史最低: {self.df['low'].min():.2f} 点")
        
        # 回归分析结果
        print(f"\n2. 线性回归分析:")
        print(f"   回归方程: y = {self.model.coef_[0][0]:.2f}x + {self.model.intercept_[0]:.2f}")
        print(f"   年均增长: {self.model.coef_[0][0]:.2f} 点/年")
        
        # 预测未来
        future_predictions = self.predict_future(5)
        print(f"\n3. 未来5年预测:")
        for _, row in future_predictions.iterrows():
            print(f"   {row['year']}年预测: {row['predicted_close']:.2f} 点")
        
        # 投资建议
        print(f"\n4. 分析结论:")
        slope = self.model.coef_[0][0]
        if slope > 100:
            trend = "强劲上升"
            suggestion = "长期看好"
        elif slope > 50:
            trend = "稳步上升" 
            suggestion = "适合长期投资"
        elif slope > 0:
            trend = "缓慢上升"
            suggestion = "谨慎乐观"
        else:
            trend = "下降趋势"
            suggestion = "注意风险"
            
        print(f"   长期趋势: {trend}")
        print(f"   投资建议: {suggestion}")

def main():
    # 创建分析器实例
    analyzer = StockAnalyzer()
    
    # 获取数据 - 可以传入不同的股票名称和代码进行回测
    df = analyzer.fetch_data()
    print("\n前5年数据预览:")
    print(df.head())
    
    # 训练模型
    analyzer.train_model()
    
    # 计算收益率
    analyzer.calculate_annual_return()
    
    # 预测未来
    future_predictions = analyzer.predict_future(5)
    
    # 生成报告
    analyzer.generate_report()
    
    # 绘制图表
    analyzer.plot_analysis(future_predictions)

if __name__ == "__main__":
    main()