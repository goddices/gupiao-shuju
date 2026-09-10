#!/bin/bash
# 同步配置文件中的股票日K线行情到数据库（不复权 + 前复权 + 后复权）
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

# TickFlow API Key: 环境变量已配置时优先，否则用这里的默认值
: "${TICKFLOW_API_KEY:=tk_aef1f7190ff44f32b5226f796a3c38ea}"
export TICKFLOW_API_KEY

# 数据源参数生效:通过环境变量传给 Python（config/datasource.py 读取）
if [ -n "$DATA_SOURCE" ]; then
    export DATA_SOURCE="$DATA_SOURCE"
fi

# 股票列表从配置文件读取（含 ignore 字段，循环时判断，为 true 则跳过同步）
STOCKS_FILE="$SCRIPT_DIR/config/sync_stocks.yaml"

STOCKS=()
NAMES=()
IGNORES=()
while IFS='|' read -r code name ignore; do
    STOCKS+=("$code")
    NAMES+=("$name")
    IGNORES+=("$ignore")
done < <(python3 - "$STOCKS_FILE" <<'PYEOF'
import sys, yaml

try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
except FileNotFoundError:
    sys.exit(f"配置文件不存在: {sys.argv[1]}")

for s in data.get("stocks", []):
    ignore = "true" if s.get("ignore", False) else "false"
    print(f"{s['code']}|{s['name']}|{ignore}")
PYEOF
)

if [ ${#STOCKS[@]} -eq 0 ]; then
    echo "错误: 未从 $STOCKS_FILE 读到任何待同步股票"
    exit 1
fi

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
SKIP=0

for i in "${!STOCKS[@]}"; do
    code="${STOCKS[$i]}"
    name="${NAMES[$i]}"

    if [ "${IGNORES[$i]}" = "true" ]; then
        echo "[$code $name] 跳过 (ignore: true)"
        ((SKIP++))
        continue
    fi

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
echo "同步完成: $OK 成功, $FAIL 失败, $SKIP 跳过"
echo "=========================================="
