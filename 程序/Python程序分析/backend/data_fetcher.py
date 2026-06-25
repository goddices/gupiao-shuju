"""从东方财富拉取股票数据并存入数据库"""
import sys
import os
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

# 将父目录加入 sys.path 以导入现有模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eastmoney_quote_reader import (
    EastmoneyQuoteReader,
    Market,
    AdjustPriceType,
    PeriodType,
)
from models import StockDailyQuote


def _guess_market(stock_code: str) -> str:
    """根据股票代码推断市场：6开头=上海，0/3开头=深圳"""
    if stock_code.startswith("6"):
        return Market.SHANGHAI
    return Market.SHENGZHEN


def fetch_stock_data(
    db: Session,
    stock_code: str,
    start_date: str = "2006-01-01",
) -> dict:
    """
    拉取单只股票数据并写入数据库。
    返回 {"stock_code": str, "new_rows": int, "message": str}
    """
    market = _guess_market(stock_code)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()

    reader = EastmoneyQuoteReader()
    quote = reader.read_quote(
        market=market,
        stock_code=stock_code,
        adjust_type=AdjustPriceType.NONE,
        period_type=PeriodType.DAILY,
        limit=5000,
    )

    if not quote or not quote.quote_lines:
        return {
            "stock_code": stock_code,
            "new_rows": 0,
            "message": f"获取数据为空，请检查股票代码或网络",
        }

    # 转为 DataFrame
    df = pd.DataFrame([
        {
            "stock_code": stock_code,
            "trade_date": q.trade_date.date(),
            "open_price": q.open,
            "high_price": q.high,
            "low_price": q.low,
            "close_price": q.close,
            "volume": int(q.volume),
            "amount": q.amount,
        }
        for q in quote.quote_lines
    ])

    # 过滤日期
    df = df[df["trade_date"] >= start_dt]
    if df.empty:
        return {
            "stock_code": stock_code,
            "new_rows": 0,
            "message": f"在 {start_date} 之后无数据",
        }

    df = df.sort_values("trade_date").reset_index(drop=True)

    # 去重：查询已存在的日期
    existing_dates = pd.read_sql(
        f"SELECT trade_date FROM stock_daily_quote WHERE stock_code = '{stock_code}'",
        con=db.bind,
    )
    if not existing_dates.empty:
        exist_set = set(pd.to_datetime(existing_dates["trade_date"]).dt.date)
        df = df[~df["trade_date"].isin(exist_set)]

    if df.empty:
        return {
            "stock_code": stock_code,
            "new_rows": 0,
            "message": f"数据已是最新，无需更新（共 {len(quote.quote_lines)} 条）",
        }

    new_count = len(df)
    df.to_sql(
        name="stock_daily_quote",
        con=db.bind,
        if_exists="append",
        index=False,
        chunksize=500,
    )

    return {
        "stock_code": stock_code,
        "new_rows": new_count,
        "message": f"成功写入 {new_count} 条新数据",
    }
