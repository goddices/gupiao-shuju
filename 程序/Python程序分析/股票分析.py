# -*- coding: utf-8 -*-
"""
股票分析 —— 统一入口：合并原 10 个中文分析脚本，用「功能」子命令 + 参数区分

用法:
    python 股票分析.py                       # 无参数 -> 交互菜单
    python 股票分析.py --help                # 列出全部功能与参数
    python 股票分析.py 红利再投 --code 601857 --start 2020-01-01 --end 2026-09-05
    python 股票分析.py 波动分析 --code 000001 --period daily --no-chart
    python 股票分析.py 分红后涨跌统计 --code 601728 --days 5,10,30

功能（10 项）: 红利再投 / 红利再投增强版 / 大跌分批买入 / 分红目标测算 /
分红后涨跌统计（以上走 MySQL）；星期涨跌分析 / 节日涨跌分析 / 波动分析 /
线性回归 / 模拟持仓（以上走网络行情）。

各功能实现位于 analysis/tools/，公共代码在 analysis/（参数解析、数据访问、
涨跌幅/收益率统计、报告输出、图表）。结果与图表保存到
results/{功能名}/{yyyymmdd}/ 下（目录契约与旧脚本一致）。
"""
import os
import sys
import traceback

import result_saver
from analysis.cli import build_parser, dispatch, interactive_menu


def main() -> int:
    # 保证 results/ 落盘到脚本所在目录（与旧脚本行为一致），可从任意目录调用
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Windows 控制台 GBK：报告含 emoji 等字符时防编码崩溃（不强制 UTF-8，改替换策略）
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass

    if len(sys.argv) == 1:
        return interactive_menu()

    try:
        parser = build_parser()
        args = parser.parse_args()
        return dispatch(args)
    except Exception:
        # 兜底：工具抛异常时补记 traceback 并关闭结果日志
        # （正常路径工具自行 finalize；finalize 非幂等，直接查 _saver 而非 get_saver）
        traceback.print_exc()
        saver = getattr(result_saver, "_saver", None)
        if saver is not None:
            try:
                saver.finalize()
            except Exception:
                pass
        return 2


if __name__ == "__main__":
    sys.exit(main())
