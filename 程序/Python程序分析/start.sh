#!/bin/bash
#
# start.sh — 启动前后端服务
# 用法: ./start.sh          (前台运行，Ctrl+C 同时停止)
#       ./start.sh -b        (后台运行)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}服务已停止${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  股票分析系统 - 启动中...${NC}"
echo -e "${GREEN}========================================${NC}"

# 启动后端 (FastAPI on port 8000)
echo -e "${YELLOW}[1/2] 启动后端服务 (FastAPI :8000)...${NC}"
cd "$BACKEND_DIR"
python3 main.py &
BACKEND_PID=$!
echo -e "${GREEN}  后端 PID: $BACKEND_PID${NC}"

# 启动前端 (Vite on port 5173)
echo -e "${YELLOW}[2/2] 启动前端服务 (Vite :5173)...${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}  前端 PID: $FRONTEND_PID${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  后端:  http://localhost:8000${NC}"
echo -e "${GREEN}  前端:  http://localhost:5173${NC}"
echo -e "${GREEN}  按 Ctrl+C 停止所有服务${NC}"
echo -e "${GREEN}========================================${NC}"

# 等待任意子进程退出
wait
