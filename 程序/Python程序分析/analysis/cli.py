# -*- coding: utf-8 -*-
"""
CLI 公共库 —— 参数解析与交互输入

- 父解析器工厂（均 add_help=False，经 sub.add_parser(parents=[...]) 注入子命令，
  避免与子命令自带的 --help 冲突）
- ask()/ask_period()：EOFError 安全的交互输入（管道/重定向下优雅退回默认值）
- build_parser()：主解析器 + 10 个中文子命令（argparse 对中文子命令精确匹配优先，
  「红利再投」与「红利再投增强版」共存无歧义）
- interactive_menu()：无参数时的功能菜单（从 analysis.tools 注册表懒加载模块）

约定：analysis.tools 各模块提供 ANALYSIS_NAME/DESCRIPTION 常量与
add_parser(subparsers)/run(args, saver=None)/interactive_input(saver) 三入口。
"""
import argparse
import importlib
import sys
from datetime import datetime


def code_parent(default: str = "601857",
                help_text: str = "股票代码（默认 601857 中国石油）") -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--code", default=default, help=help_text)
    return p


def range_parent(start_help: str = "起始日期 YYYY-MM-DD（默认：最早有数据）",
                 end_help: str = "结束日期 YYYY-MM-DD（默认：最新有数据）") -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--start", default=None, help=start_help)
    p.add_argument("--end", default=None, help=end_help)
    return p


def db_common_parent(with_tax: bool = True) -> argparse.ArgumentParser:
    """DB 类工具公共参数：--tax/--sync/--no-chart（分红后涨跌统计无 --tax，传 with_tax=False）"""
    p = argparse.ArgumentParser(add_help=False)
    if with_tax:
        p.add_argument("--tax", type=float, default=0.0,
                       help="分红税率 0~1（默认 0 = 长期持有免税）")
    p.add_argument("--sync", action="store_true", help="强制重新从东方财富拉取分红明细")
    p.add_argument("--no-chart", action="store_true",
                   help="不弹出图形窗口（图片仍会保存到 results 目录）")
    return p


def market_parent(no_chart: bool = True) -> argparse.ArgumentParser:
    """行情类工具公共参数：--name/--no-chart"""
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--name", default="上证指数", help="股票名称（仅用于显示，默认 上证指数）")
    if no_chart:
        p.add_argument("--no-chart", action="store_true",
                       help="不弹出图形窗口（图片仍会保存到 results 目录）")
    return p


def ask(prompt: str, default, cast=str):
    """交互输入：EOFError 或空输入/转换失败一律返回默认值"""
    try:
        raw = input(prompt)
    except EOFError:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except (ValueError, TypeError):
        return default


def ask_period() -> str:
    """交互选择分析周期：1/2/3 -> daily/weekly/monthly（默认 daily）"""
    print("\n请选择分析周期：")
    print("1. 日线")
    print("2. 周线")
    print("3. 月线")
    choice = ask("请输入选项（默认：1）: ", "1")
    return {"1": "daily", "2": "weekly", "3": "monthly"}.get(choice, "daily")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _import_tool(name: str):
    from analysis.tools import TOOLS
    stem, _desc = TOOLS[name]
    return importlib.import_module("analysis.tools." + stem)


def build_parser() -> argparse.ArgumentParser:
    """构建主解析器（含 10 个子命令；会 import 全部工具模块，约 1-2s）"""
    from analysis.tools import TOOLS
    parser = argparse.ArgumentParser(
        prog="股票分析",
        description="股票分析统一入口：python 股票分析.py <功能> [参数]；不带功能时进入交互菜单",
    )
    sub = parser.add_subparsers(dest="tool", metavar="功能")
    for name in TOOLS:
        module = _import_tool(name)
        module.add_parser(sub)
    return parser


def dispatch(args: argparse.Namespace) -> int:
    """执行子命令（run 已在 add_parser 时经 set_defaults 挂到 args._run）"""
    run = getattr(args, "_run", None)
    if run is None:
        print("未知功能，请用 --help 查看用法")
        return 2
    return run(args) or 0


def interactive_menu() -> int:
    """无参数交互菜单：列功能 -> 选择 -> 交互输入 -> 执行；EOFError 优雅退出"""
    from analysis.tools import TOOLS
    from result_saver import reset_saver

    names = list(TOOLS)
    print("=== 股票分析工具菜单 ===")
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name} — {TOOLS[name][1]}")
    try:
        raw = input(f"请选择功能（1-{len(names)}，回车退出）: ").strip()
    except EOFError:
        print("未选择功能，退出。")
        return 0
    if not raw:
        return 0
    try:
        idx = int(raw) - 1
    except ValueError:
        print("无效选择")
        return 2
    if not 0 <= idx < len(names):
        print("无效选择")
        return 2

    name = names[idx]
    module = _import_tool(name)
    saver = reset_saver(name)
    try:
        args = module.interactive_input(saver)
    except EOFError:
        saver.finalize()
        return 0
    rc = module.run(args, saver=saver) or 0
    return rc
