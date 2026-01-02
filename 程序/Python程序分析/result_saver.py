import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt
from io import StringIO
import contextlib

class ResultSaver:
    def __init__(self, analysis_name):
        """
        初始化结果保存器
        
        Args:
            analysis_name: 分析程序名称（如：股票K线分析、线性回归等）
        """
        self.analysis_name = analysis_name
        self.results_dir = "results"
        self.create_results_dir()
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_dir = os.path.join(self.results_dir, f"{self.timestamp}_{analysis_name}")
        self.create_session_dir()
        
        # 创建日志文件
        self.log_file = os.path.join(self.session_dir, f"{analysis_name}_analysis_log.txt")
        self.current_log = []
        
    def create_results_dir(self):
        """创建results目录"""
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    def create_session_dir(self):
        """创建当前分析会话的目录"""
        if not os.path.exists(self.session_dir):
            os.makedirs(self.session_dir)
    
    def log(self, message):
        """
        记录日志消息
        
        Args:
            message: 要记录的消息
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.current_log.append(log_entry)
        print(message)  # 同时输出到控制台
    
    def save_log(self):
        """保存日志到文件"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"{self.analysis_name} 分析结果日志\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            for entry in self.current_log:
                f.write(entry + "\n")
    
    def save_chart(self, filename=None, tight_layout=True):
        """
        保存当前图表
        
        Args:
            filename: 图表文件名，如果为None则使用默认命名
            tight_layout: 是否使用紧凑布局
        """
        if filename is None:
            filename = f"{self.analysis_name}_analysis_chart.jpg"
        
        chart_path = os.path.join(self.session_dir, filename)
        
        if tight_layout:
            plt.tight_layout()
        
        plt.savefig(chart_path, format='jpg', dpi=300, bbox_inches='tight')
        self.log(f"图表已保存至: {chart_path}")
        
        return chart_path
    
    def capture_print_output(self, func, *args, **kwargs):
        """
        捕获函数中的print输出并记录到日志
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        # 重定向stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            result = func(*args, **kwargs)
            
            # 获取捕获的输出
            output = captured_output.getvalue()
            if output:
                self.log("分析结果:")
                self.log(output)
            
            return result
            
        finally:
            # 恢复stdout
            sys.stdout = old_stdout
    
    def get_session_info(self):
        """获取当前会话信息"""
        return {
            'analysis_name': self.analysis_name,
            'timestamp': self.timestamp,
            'session_dir': self.session_dir,
            'log_file': self.log_file
        }
    
    def finalize(self):
        """完成分析，保存所有结果"""
        self.save_log()
        self.log(f"分析完成，结果已保存至: {self.session_dir}")

# 全局结果保存器实例
_saver = None

def get_saver(analysis_name="分析程序"):
    """获取全局结果保存器实例"""
    global _saver
    if _saver is None:
        _saver = ResultSaver(analysis_name)
    return _saver

def reset_saver(analysis_name="分析程序"):
    """重置结果保存器"""
    global _saver
    _saver = ResultSaver(analysis_name)
    return _saver