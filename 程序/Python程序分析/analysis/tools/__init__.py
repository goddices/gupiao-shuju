# -*- coding: utf-8 -*-
"""
tools 包 —— 统一入口的功能实现（10 个模块，按需懒加载）

TOOLS 注册表只存字符串（模块名 + 描述），import analysis.tools 零副作用，
web 后端进程永不加载这里的工具链（matplotlib/sklearn/result_saver 等）。

每个工具模块约定提供：
    ANALYSIS_NAME  str    子命令名 = ResultSaver analysis_name（保持旧 results/ 目录契约）
    DESCRIPTION    str    菜单/--help 一行描述
    add_parser(subparsers)   注册子命令并 set_defaults(_run=run)
    run(args, saver=None)    执行（saver 为 None 时自行 reset_saver(ANALYSIS_NAME)）
    interactive_input(saver) 菜单路径的交互输入，返回 argparse.Namespace

私有模块（下划线前缀，不入 TOOLS，不会被当工具加载）：
    _reinvest_common  红利再投/红利再投增强版/大跌分批买入 三工具共用的
                      报告节、对比图骨架、run() 骨架与公共问项
"""
TOOLS = {
    "红利再投": ("红利再投", "个股长期红利再投收益模拟（不复权 + 分红无脑再投）"),
    "红利再投增强版": ("红利再投增强版", "大跌 x% 买入 y 万 + 红利再投，对比收益率"),
    "大跌分批买入": ("大跌分批买入", "当天大跌 x% 按最低价买入总仓位 y% 一笔 + 红利再投"),
    "分红目标测算": ("分红目标测算", "目标每年分红到账金额反推需投入本金"),
    "分红后涨跌统计": ("分红后涨跌统计", "除息日后 N 日窗口涨跌与下跌概率统计"),
    "星期涨跌分析": ("星期涨跌分析", "按星期几分组统计涨跌分布并预测未来交易日"),
    "节日涨跌分析": ("节日涨跌分析", "法定节假日前后涨跌对比与热力图"),
    "波动分析": ("波动分析", "K线波动幅度/涨跌幅分布/趋势统计"),
    "线性回归": ("线性回归", "收盘价线性回归趋势与未来预测"),
    "模拟持仓": ("模拟持仓", "买入持有/理想买卖/均线策略三策略模拟对比"),
}
