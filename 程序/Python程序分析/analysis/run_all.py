# -*- coding: utf-8 -*-
"""
单股全分析 —— 先同步数据，再对指定股票执行全部分析

流程:
    1. 同步核心数据（上市日期/名称，供行情同步确定起始日期）
    2. 同步行情（不复权 + 前复权 + 后复权，全量）
    3. 同步分红明细（DB 类分析依赖）
    4. 依次运行全部 10 个分析功能（DB 类 5 个 + 行情类 5 个），
       每个功能独立子进程执行（与 run_all_analysis.sh 模式一致），
       结果保存到 results/{功能名}/{yyyymmdd}/（目录契约与其他入口一致）

用法:
    python -m analysis.run_all 601857                        # 同步 + 全部分析
    python -m analysis.run_all 600519 --name 贵州茅台
    python -m analysis.run_all 601857 --no-sync              # 跳过同步直接分析
    python -m analysis.run_all 601857 --tools 红利再投,线性回归
    python -m analysis.run_all 601857 --start 2015-01-01 --end 2026-09-20

analyze_stock.sh 是本模块的 shell 封装（配置环境变量后调用本模块）。
"""
import argparse
import os
import subprocess
import sys
from datetime import date, datetime

# 项目根目录（analysis/ 的上一级），子进程以此为准，保证 results/ 落盘位置一致
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# backend 包内使用裸导入（from db_config import ...），需把 backend/ 目录也加入 sys.path
for _p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DEFAULT_START = "2008-01-01"        # 行情类分析的默认起始日期（与 run_all_analysis.sh 一致）
SHORT_START = "2024-01-01"          # 模拟持仓使用较短的日期范围（与 run_all_analysis.sh 一致）

# 行情类功能: (功能名, 额外参数)；参数 --code/--name/--start/--end/--no-chart
MARKET_TOOLS = [
    ("星期涨跌分析", []),
    ("节日涨跌分析", []),
    ("波动分析", ["--period", "daily"]),
    ("线性回归", ["--period", "daily"]),
]

# 模拟持仓: 无 --name 参数，且使用较短的日期范围
MOCK_TOOL = "模拟持仓"

# DB 类功能: (功能名, 是否带日期范围)；参数 --code [--start/--end] --no-chart
DB_TOOLS = [
    ("红利再投", True),
    ("红利再投增强版", True),
    ("大跌分批买入", True),
    ("分红目标测算", False),      # 无 --start/--end，只有 --buy-date
    ("分红后涨跌统计", True),
]

ALL_TOOL_NAMES = ([name for name, _ in DB_TOOLS]
                  + [name for name, _ in MARKET_TOOLS]
                  + [MOCK_TOOL])


def today_dash() -> str:
    return date.today().strftime("%Y-%m-%d")


def sync_one_stock(db, code: str, log=print) -> dict:
    """同步单只股票的全部数据: 核心数据 → 行情(三种复权,全量) → 分红明细

    各步失败不中断（指数无分红/核心数据等场景），最终返回各步状态与股票名称。
    """
    from backend.services import (
        get_stock_name, sync_stock_core_data, sync_stock_dividends,
    )
    from backend.data_fetcher import fetch_stock_data_full

    results = {}

    # 1. 核心数据（上市日期供行情同步确定起始日期；名称作为兜底）
    log("[同步 1/3] 核心数据...")
    try:
        r = sync_stock_core_data(db, code)
        log(f"    {r['status']}: {r['message']}")
        results["core"] = r["status"]
    except Exception as e:
        log(f"    失败（忽略，继续）: {e}")
        results["core"] = "error"

    # 2. 行情（不复权 + 前复权 + 后复权，全量；与 sync_quotes.sh 单只逻辑一致）
    log("[同步 2/3] 行情（不复权/前复权/后复权，全量）...")
    try:
        r = fetch_stock_data_full(
            db, code, start_date="2006-01-01",
            end_date=date.today().strftime("%Y%m%d"),
        )
        log(f"    {r['status']} | {r['total_rows']} rows | {' | '.join(r['details'])}")
        db.commit()
        results["quotes"] = r["status"]
    except Exception as e:
        db.rollback()
        log(f"    失败: {e}")
        results["quotes"] = "error"

    # 3. 分红明细（红利再投等 DB 类分析依赖）
    log("[同步 3/3] 分红明细...")
    try:
        r = sync_stock_dividends(db, code)
        log(f"    {r['status']}: {r['message']}")
        results["dividends"] = r["status"]
    except Exception as e:
        log(f"    失败（忽略，继续）: {e}")
        results["dividends"] = "error"

    # 名称解析: stock_info → 核心数据 → 代码本身（数据库不可用时退回代码）
    name = None
    try:
        name = get_stock_name(db, code)
        if not name:
            from backend.models import StockCoreData
            core = db.query(StockCoreData).filter(StockCoreData.stock_code == code).first()
            name = core.stock_name if core else None
    except Exception:
        pass
    results["name"] = name or code
    return results


def _run_tool(tool: str, code: str, extra: list, name: str = None,
              start: str = None, end: str = None, show_chart: bool = False,
              log=print) -> int:
    """以子进程运行 股票分析.py 的单个功能，返回退出码"""
    cmd = [sys.executable, "股票分析.py", tool, "--code", code]
    if name:
        cmd += ["--name", name]
    if start:
        cmd += ["--start", start]
    if end:
        cmd += ["--end", end]
    if not show_chart:
        cmd.append("--no-chart")
    cmd += extra

    log(f"  >> 股票分析.py {tool} --code {code}")
    env = dict(os.environ, MPLBACKEND="Agg")
    r = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)
    if r.returncode == 0:
        log(f"  ✓ {tool} 完成")
    else:
        log(f"  ✗ {tool} 失败 (exit code: {r.returncode})")
    return r.returncode


def run_all_analysis(code: str, name: str = None, start: str = None, end: str = None,
                     sync: bool = True, tools: list = None, show_chart: bool = False,
                     log=print) -> int:
    """先同步数据，再对指定股票执行全部分析

    :param code: 股票代码（如 601857）
    :param name: 股票名称（仅用于显示；None 时同步后从数据库解析）
    :param start/end: 分析区间 YYYY-MM-DD（默认 2008-01-01 ~ 今天；模拟持仓固定短区间）
    :param sync: 是否先同步数据（False 则直接用库内已有数据分析）
    :param tools: 只运行指定功能子集（None = 全部 10 个）
    :param show_chart: 是否弹出图形窗口（默认否，图片仍保存到 results/）
    :return: 0=全部成功, 1=有失败
    """
    end = end or today_dash()
    start = start or DEFAULT_START

    log("=" * 42)
    log(f"单股全分析: {code}")
    log(f"日期: {end}   分析区间: {start} ~ {end}")
    log("=" * 42)

    # ---------- 1. 同步数据 ----------
    if sync:
        from backend.database import SessionLocal
        db = SessionLocal()
        try:
            r = sync_one_stock(db, code, log=log)
        finally:
            db.close()
        if name is None:
            name = r.get("name") or code
        if r.get("quotes") not in ("ok", "no_new_data"):
            log("行情同步未成功，仍继续分析（使用库内已有数据）")
    if name is None:
        name = code

    log(f"\n股票: {name}({code})")
    selected = set(tools) if tools else None

    def wanted(tool_name: str) -> bool:
        return selected is None or tool_name in selected

    # ---------- 2. 执行全部分析 ----------
    results = []  # (功能名, 退出码)

    db_tools = [(t, rng) for t, rng in DB_TOOLS if wanted(t)]
    if db_tools:
        log(f"\n----- DB 类分析 ({len(db_tools)} 个) -----")
        for tool, with_range in db_tools:
            rc = _run_tool(tool, code, [], show_chart=show_chart,
                           start=start if with_range else None,
                           end=end if with_range else None, log=log)
            results.append((tool, rc))

    market_tools = [(t, ex) for t, ex in MARKET_TOOLS if wanted(t)]
    if market_tools:
        log(f"\n----- 行情类分析 ({len(market_tools)} 个) -----")
        for tool, extra in market_tools:
            rc = _run_tool(tool, code, extra, name=name,
                           start=start, end=end, show_chart=show_chart, log=log)
            results.append((tool, rc))

    if wanted(MOCK_TOOL):
        log("\n----- 模拟持仓 -----")
        # 模拟持仓无 --name，且固定使用较短区间（与 run_all_analysis.sh 一致）
        mock_start = SHORT_START if start == DEFAULT_START else start
        rc = _run_tool(MOCK_TOOL, code, [], start=mock_start, end=end,
                       show_chart=show_chart, log=log)
        results.append((MOCK_TOOL, rc))

    # ---------- 3. 汇总 ----------
    ok = [t for t, rc in results if rc == 0]
    fail = [t for t, rc in results if rc != 0]
    log("\n" + "=" * 42)
    log(f"全部分析完成: {len(ok)} 成功, {len(fail)} 失败")
    if fail:
        log(f"失败功能: {', '.join(fail)}")
    log(f"结果目录: {os.path.join(PROJECT_ROOT, 'results')}")
    log("=" * 42)
    return 1 if fail else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="analysis.run_all",
        description="对指定股票先同步数据，再执行全部分析",
    )
    p.add_argument("code", help="股票代码（如 601857）")
    p.add_argument("--name", default=None,
                   help="股票名称（仅用于显示；默认同步后从数据库解析）")
    p.add_argument("--start", default=None,
                   help=f"分析起始日期 YYYY-MM-DD（默认 {DEFAULT_START}）")
    p.add_argument("--end", default=None,
                   help="分析结束日期 YYYY-MM-DD（默认今天）")
    p.add_argument("--no-sync", action="store_true",
                   help="跳过数据同步，直接用库内已有数据分析")
    p.add_argument("--tools", default=None,
                   help="只运行指定功能（逗号分隔），可选: " + ",".join(ALL_TOOL_NAMES))
    p.add_argument("--show-chart", action="store_true",
                   help="弹出图形窗口（默认不弹，图片仍保存到 results/）")
    return p


def main() -> int:
    os.chdir(PROJECT_ROOT)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass

    args = build_parser().parse_args()
    tools = None
    if args.tools:
        tools = [t.strip() for t in args.tools.split(",") if t.strip()]
        unknown = [t for t in tools if t not in ALL_TOOL_NAMES]
        if unknown:
            print(f"未知功能: {', '.join(unknown)}")
            print("可选: " + ", ".join(ALL_TOOL_NAMES))
            return 2
    return run_all_analysis(
        args.code, name=args.name, start=args.start, end=args.end,
        sync=not args.no_sync, tools=tools, show_chart=args.show_chart,
    )


if __name__ == "__main__":
    sys.exit(main())
