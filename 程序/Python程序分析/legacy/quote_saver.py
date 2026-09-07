import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from emdata import (
    EastmoneyQuoteReader,
    Market,
    AdjustPriceType,
    PeriodType,
)

# ---------- 数据库配置 ----------
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "deepstock",
}

# 创建数据库引擎（连接池）
ENGINE = create_engine(
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4",
    echo=False,  # 设为 True 可打印 SQL 日志
)


def create_table_if_not_exists():
    """
    创建数据表（如果不存在）。
    设计唯一索引 (stock_code, trade_date) 防止重复插入。
    """
    with ENGINE.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_daily_quote (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                stock_code VARCHAR(20) NOT NULL COMMENT '股票代码，如601857',
                trade_date DATE NOT NULL COMMENT '交易日期',
                open_price DECIMAL(12, 4) NOT NULL COMMENT '开盘价（不复权）',
                high_price DECIMAL(12, 4) NOT NULL COMMENT '最高价（不复权）',
                low_price DECIMAL(12, 4) NOT NULL COMMENT '最低价（不复权）',
                close_price DECIMAL(12, 4) NOT NULL COMMENT '收盘价（不复权）',
                volume BIGINT NOT NULL COMMENT '成交量（股）',
                amount DECIMAL(20, 4) NOT NULL COMMENT '成交额（）',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
                UNIQUE KEY uk_stock_date (stock_code, trade_date)  -- 关键：防止重复
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日线行情（不复权）';
        """))
        conn.commit()
        print("✅ 数据表检查/创建完成")


def fetch_and_save_stock(market: str, stock_code: str, start_date: str = "2008-01-01"):
    """
    获取单只股票从指定日期开始的不复权日线数据，并存入 MySQL。

    :param market: Market.SHANGHAI 或 Market.SHENGZHEN
    :param stock_code: 6位数字股票代码
    :param start_date: 起始日期字符串，默认 '2008-01-01'
    """
    print(f"🔄 正在处理股票: {stock_code} ...")

    # 1. 从东方财富获取数据（不复权）
    reader = EastmoneyQuoteReader()
    quote = reader.read_quote(
        market=market,
        stock_code=stock_code,
        adjust_type=AdjustPriceType.NONE,  # 必须用不复权
        period_type=PeriodType.DAILY,
        limit=5000,  # 足够覆盖2007年至今
    )

    if not quote or not quote.quote_lines:
        print(f"⚠️ 股票 {stock_code} 获取数据为空，请检查代码或网络。")
        return

    # 2. 转为 Pandas DataFrame
    df = pd.DataFrame(
        [
            {
                "stock_code": stock_code,
                "trade_date": q.trade_date.date(),
                "open_price": q.open,
                "high_price": q.high,
                "low_price": q.low,
                "close_price": q.close,
                "volume": int(q.volume),  # 东方财富返回的成交量是股数，直接取整
                "amount": q.amount,
            }
            for q in quote.quote_lines
        ]
    )

    # 3. 过滤日期：只保留 >= start_date 的数据（解决你不知道上市日期的问题）
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    df = df[df["trade_date"] >= start_dt]

    if df.empty:
        print(f"⚠️ 股票 {stock_code} 在 {start_date} 之后无数据。")
        return

    # 按日期排序
    df = df.sort_values("trade_date").reset_index(drop=True)
    print(f"📊 获取到 {len(df)} 条数据（自 {df['trade_date'].min()} 起）")

    # 4. 写入 MySQL（自动去重）
    with ENGINE.connect() as conn:
        # 先查询该股票已存在的日期
        existing_dates = pd.read_sql(
            f"SELECT trade_date FROM stock_daily_quote WHERE stock_code = '{stock_code}'",
            con=conn,
        )

        if not existing_dates.empty:
            # 转为 set 方便过滤
            exist_set = set(pd.to_datetime(existing_dates["trade_date"]).dt.date)
            df = df[~df["trade_date"].isin(exist_set)]
            print(f"🔄 去重后，新增 {len(df)} 条数据待写入")

        if df.empty:
            print(f"⏭️ 股票 {stock_code} 数据已是最新，无需更新。")
            return

        # 批量插入（pandas 原生支持高效写入）
        df.to_sql(
            name="stock_daily_quote",
            con=ENGINE,
            if_exists="append",  # 追加模式
            index=False,
            chunksize=500,  # 每500条提交一次，防止单条过大
        )
        print(f"✅ 股票 {stock_code} 成功写入 {len(df)} 条数据到数据库")


def main():
    # 初始化建表
    create_table_if_not_exists()

    # ---------- 在这里配置你要抓取的股票列表 ----------
    stocks_to_fetch = [
        {"market": Market.SHANGHAI, "code": "601857"},  # 中国石油
        {"market": Market.SHANGHAI, "code": "600036"},  # 招商银行
        {"market": Market.SHENGZHEN, "code": "000858"},  # 五粮液
    ]

    # 批量执行
    for stock in stocks_to_fetch:
        fetch_and_save_stock(
            market=stock["market"],
            stock_code=stock["code"],
            start_date="2006-01-01",  # 默认起始日，股票上市晚则自动从上市日取
        )

    print("🎉 所有任务执行完毕！")


if __name__ == "__main__":
    main()
