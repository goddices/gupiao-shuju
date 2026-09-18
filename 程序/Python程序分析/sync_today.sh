#!/bin/bash
# 只同步当天（或指定交易日）行情到数据库 —— 增量快速同步
# 每只股票仅拉取最近 10 根K线并写入/更新当天一行，远快于 sync_quotes.sh 全量同步，
# 适合每个交易日收盘后定时执行（crontab 示例见文件末尾）
# 用法: bash sync_today.sh [数据源] [日期]
#       bash sync_today.sh                    # 默认 tickflow + 今天
#       bash sync_today.sh tickflow           # TickFlow + 今天
#       bash sync_today.sh eastmoney 20260915 # 东方财富 + 指定日期
#       bash sync_today.sh "" 20260915        # 配置默认数据源 + 指定日期
#
# 注意: 前复权价格随最新行情每日变动，本脚本不回刷历史前复权价；
#       请定期用 sync_quotes.sh 做全量同步校准。
#
# crontab 示例（交易日 16:30 执行）:
#   30 16 * * 1-5 cd /path/to/Python程序分析 && bash sync_today.sh >> logs/sync_today.log 2>&1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DATA_SOURCE="${1:-}"
TRADE_DATE="${2:-$(date +%Y%m%d)}"

# 校验日期格式 YYYYMMDD
if ! [[ "$TRADE_DATE" =~ ^[0-9]{8}$ ]]; then
    echo "错误: 日期格式应为 YYYYMMDD，收到: $TRADE_DATE"
    exit 1
fi

# TickFlow API Key: 环境变量已配置时优先，否则用这里的默认值
: "${TICKFLOW_API_KEY:=tk_aef1f7190ff44f32b5226f796a3c38ea}"
export TICKFLOW_API_KEY

# 数据源参数生效:通过环境变量传给 Python（config/datasource.py 读取）
if [ -n "$DATA_SOURCE" ]; then
    export DATA_SOURCE="$DATA_SOURCE"
fi

# 非交易日直接退出，避免无谓的 API 请求
if ! python3 - "$TRADE_DATE" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from analysis.trading_calendar import TradingCalendar

d = sys.argv[1]
d_fmt = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
sys.exit(0 if TradingCalendar().is_trading_day(d_fmt) else 1)
PYEOF
then
    echo "$TRADE_DATE 是非交易日（周末/节假日），跳过同步"
    exit 0
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
echo "同步当天股票行情（增量快速同步）"
if [ -n "$DATA_SOURCE" ]; then
    echo "数据源: $DATA_SOURCE (指定)"
else
    echo "数据源: 配置默认"
fi
echo "交易日: $TRADE_DATE"
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
from backend.data_fetcher import fetch_stock_data_today

db = SessionLocal()
for attempt in range(3):
    try:
        r = fetch_stock_data_today(db, '$code', trade_date='$TRADE_DATE')
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
