import json
from datetime import datetime
from sqlalchemy import create_engine, text

# ---------- 数据库配置（与之前保持一致） ----------
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "deepstock",
}

ENGINE = create_engine(
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4",
    echo=False,
)


def create_table_if_not_exists():
    """创建分红送转事件表（如果不存在）"""
    with ENGINE.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_dividend_events (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
                event_name VARCHAR(50) COMMENT '事件名称（如 2024年末期）',
                record_date DATE COMMENT '股权登记日',
                ex_dividend_date DATE NOT NULL COMMENT '除权除息日',
                payment_date DATE COMMENT '派息日/到账日',
                cash_per_10 DECIMAL(12, 6) DEFAULT 0 COMMENT '每10股派现金（含税）',
                bonus_per_10 DECIMAL(12, 6) DEFAULT 0 COMMENT '每10股送股数',
                conversion_per_10 DECIMAL(12, 6) DEFAULT 0 COMMENT '每10股转增股数',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
                UNIQUE KEY uk_stock_exdiv (stock_code, ex_dividend_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票分红送转事件表';
        """))
        conn.commit()
        print("✅ 数据表 stock_dividend_events 检查/创建完成")


def import_json_to_db(json_file_path: str, stock_code: str):
    """
    将分红/送转 JSON 文件导入数据库

    :param json_file_path: JSON 文件路径
    :param stock_code: 股票代码（如 '601857'），用于标注数据归属
    """
    # 1. 读取 JSON
    with open(json_file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)  # 假设是列表

    # 如果传入的是单条对象，转为列表处理
    if isinstance(raw_data, dict):
        raw_data = [raw_data]

    print(f"📂 读取到 {len(raw_data)} 条分红记录，准备导入股票 {stock_code}")

    # 2. 解析并转换为 SQL 参数列表
    insert_params = []
    for item in raw_data:
        # 兼容旧格式（只有 per_share）和新格式（cash_per_10）
        if "per_share" in item and "cash_per_10" not in item:
            # 旧格式：每股分红，换算为 每10股
            cash_val = float(item["per_share"]) * 10
        else:
            cash_val = float(item.get("cash_per_10", 0))

        # 送股、转增（默认 0）
        bonus_val = float(item.get("bonus_per_10", 0))
        conversion_val = float(item.get("conversion_per_10", 0))

        # 提取日期（字符串 -> 字符串即可，MySQL 自动识别 YYYY-MM-DD）
        record_date = item.get("record_date")  # 可能为 None
        ex_date = item.get("ex_dividend_date")
        pay_date = item.get("payment_date")

        # 关键字段必须存在
        if not ex_date:
            print(f"⚠️ 跳过一条记录：缺少除权除息日 (ex_dividend_date)，数据: {item}")
            continue

        insert_params.append(
            {
                "stock_code": stock_code,
                "event_name": item.get("annual") or item.get("event_name") or "",
                "record_date": record_date,
                "ex_dividend_date": ex_date,
                "payment_date": pay_date,
                "cash_per_10": cash_val,
                "bonus_per_10": bonus_val,
                "conversion_per_10": conversion_val,
            }
        )

    if not insert_params:
        print("⚠️ 无有效数据可导入。")
        return

    # 3. 执行批量插入（利用 ON DUPLICATE KEY UPDATE 实现幂等性）
    insert_sql = text("""
        INSERT INTO stock_dividend_events
        (stock_code, event_name, record_date, ex_dividend_date, payment_date, 
         cash_per_10, bonus_per_10, conversion_per_10)
        VALUES 
        (:stock_code, :event_name, :record_date, :ex_dividend_date, :payment_date, 
         :cash_per_10, :bonus_per_10, :conversion_per_10)
        ON DUPLICATE KEY UPDATE
            event_name = VALUES(event_name),
            record_date = VALUES(record_date),
            payment_date = VALUES(payment_date),
            cash_per_10 = VALUES(cash_per_10),
            bonus_per_10 = VALUES(bonus_per_10),
            conversion_per_10 = VALUES(conversion_per_10);
    """)

    with ENGINE.connect() as conn:
        for params in insert_params:
            conn.execute(insert_sql, params)
        conn.commit()

    print(f"✅ 成功导入/更新 {len(insert_params)} 条记录至 stock_dividend_events 表")


# ================== 使用示例 ==================
if __name__ == "__main__":
    # 初始化建表
    create_table_if_not_exists()

    # ---------- 示例 1：导入你之前提供的中国石油 JSON（旧格式） ----------
    # # 为了方便演示，我直接把旧 JSON 放入变量（你也可以存为 .json 文件）
    # old_dividend_json_str = """
    # [
    #   {"seq":1,"annual":"2007年末期","plan_10shares":"1.5686","per_share":0.15686,"record_date":"2008-06-12","ex_dividend_date":"2008-06-13","payment_date":"2008-06-30"},
    #   {"seq":37,"annual":"2025年末期","plan_10shares":"2.5000","per_share":0.25000,"record_date":"2026-06-25","ex_dividend_date":"2026-06-26","payment_date":"2026-06-26"}
    # ]
    # """
    # # 保存为临时文件（模拟文件导入）
    # with open("temp_601857.json", "w", encoding="utf-8") as f:
    #     f.write(old_dividend_json_str)

    # 调用导入
    import_json_to_db("temp_601857.json", stock_code="601857")

    # ---------- 示例 2：如果你有送转股的 JSON，可以用新格式 ----------
    # 新格式样例（包含送股和转增）
    # new_format_json = """
    # [
    #   {
    #     "event_name": "2024年末期",
    #     "record_date": "2025-06-20",
    #     "ex_dividend_date": "2025-06-23",
    #     "payment_date": "2025-06-30",
    #     "cash_per_10": 2.5,
    #     "bonus_per_10": 2.0,
    #     "conversion_per_10": 3.0
    #   }
    # ]
    # """
    # with open("temp_new_format.json", "w", encoding="utf-8") as f:
    #     f.write(new_format_json)

    # 导入新格式（假设是另一只股票，如 000001）
    # import_json_to_db('temp_new_format.json', stock_code='000001')

    print("🎉 所有数据导入完成！")
