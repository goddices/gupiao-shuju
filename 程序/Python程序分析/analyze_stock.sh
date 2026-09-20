#!/bin/bash
# 对指定股票先同步数据（核心数据 + 行情三复权全量 + 分红明细），再执行全部分析
# 分析包括: 红利再投 / 红利再投增强版 / 大跌分批买入 / 分红目标测算 / 分红后涨跌统计 /
#          星期涨跌分析 / 节日涨跌分析 / 波动分析 / 线性回归 / 模拟持仓
# 结果自动保存到 results/{功能名}/{yyyymmdd}/ 目录
#
# 用法: bash analyze_stock.sh <股票代码> [股票名称] [额外参数...]
#       bash analyze_stock.sh 601857                    # 同步 + 全部分析
#       bash analyze_stock.sh 600519 贵州茅台
#       bash analyze_stock.sh 601857 "" --no-sync       # 跳过同步直接分析
#       bash analyze_stock.sh 601857 "" --tools 红利再投,线性回归
#       bash analyze_stock.sh 601857 "" --start 2015-01-01
#
# 数据源: 默认走配置（config/datasource.py），可用环境变量覆盖，如:
#       DATA_SOURCE=tickflow bash analyze_stock.sh 601857

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ $# -lt 1 ]; then
    echo "错误: 缺少股票代码"
    echo "用法: bash analyze_stock.sh <股票代码> [股票名称] [额外参数...]"
    exit 1
fi

CODE="$1"
NAME="${2:-}"
if [ $# -ge 1 ]; then shift; fi
if [ $# -ge 1 ]; then shift; fi
# 剩余参数原样透传给 analysis.run_all（如 --no-sync / --tools / --start / --end）

export MPLBACKEND=Agg
export PYTHONIOENCODING=utf-8

# TickFlow API Key: 环境变量已配置时优先，否则用这里的默认值
: "${TICKFLOW_API_KEY:=tk_aef1f7190ff44f32b5226f796a3c38ea}"
export TICKFLOW_API_KEY

ARGS=("$CODE")
if [ -n "$NAME" ]; then
    ARGS+=(--name "$NAME")
fi
ARGS+=("$@")

python3 -m analysis.run_all "${ARGS[@]}"
