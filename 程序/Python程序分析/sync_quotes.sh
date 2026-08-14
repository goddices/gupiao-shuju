#!/bin/bash
# 同步6只默认股票的日K线行情到数据库（不复权 + 前复权 + 后复权）
# 复权数据写入 forward_* / backward_* 字段；主数据源失败时自动用 AKShare 兜底
# 用法: bash sync_quotes.sh [数据源]
#       bash sync_quotes.sh tickflow    # TickFlow
#       bash sync_quotes.sh eastmoney   # 东方财富
#       bash sync_quotes.sh akshare     # AKShare
#       bash sync_quotes.sh             # 默认 tickflow

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DATA_SOURCE="${1:-}"
TODAY=$(date +%Y%m%d)

# 数据源参数生效:通过环境变量传给 Python（config/datasource.py 读取）
if [ -n "$DATA_SOURCE" ]; then
    export DATA_SOURCE="$DATA_SOURCE"
fi

# 默认6只股票: 中国石油 中国移动 上证指数 贵州茅台 寒武纪 中芯国际
STOCKS=("601857" "600941" "000001" "600519" "688256" "688981")
NAMES=("中国石油" "中国移动" "上证指数" "贵州茅台" "寒武纪" "中芯国际")

echo "=========================================="
echo "同步股票行情"
if [ -n "$DATA_SOURCE" ]; then
    echo "数据源: $DATA_SOURCE (指定)"
else
    echo "数据源: 配置默认"
fi
echo "日期: $TODAY"
echo "股票: ${STOCKS[*]}"
echo "=========================================="
echo ""

OK=0
FAIL=0

for i in "${!STOCKS[@]}"; do
    code="${STOCKS[$i]}"
    name="${NAMES[$i]}"

    echo -n "[$code $name] "
    python3 -c "
import sys, time
sys.path.insert(0, '.')
sys.path.insert(0, 'backend')
from backend.database import SessionLocal
from backend.data_fetcher import fetch_stock_data_full

db = SessionLocal()
for attempt in range(3):
    try:
        r = fetch_stock_data_full(db, '$code', start_date='2006-01-01', end_date='$TODAY')
        print(r['status'] + ' | ' + str(r['total_rows']) + ' rows | ' + ' | '.join(r['details']))
        db.commit()
        exit(0 if r['status'] in ('ok', 'no_new_data') else 1)
    except Exception as e:
        if attempt < 2:
            time.sleep(8 * (attempt + 1))
        else:
            print('FAIL: ' + str(e))
            db.rollback()
            exit(1)
db.close()
"
    rc=$?
    if [ $rc -eq 0 ]; then
        ((OK++))
    else
        ((FAIL++))
    fi
    sleep 1.5
done

echo ""
echo "=========================================="
echo "同步完成: $OK 成功, $FAIL 失败"
echo "=========================================="
