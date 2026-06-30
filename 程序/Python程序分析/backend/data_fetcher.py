"""从东方财富拉取股票数据（不复权+前复权+后复权）并写入数据库"""

import sys
import os
import asyncio
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text

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


def _quote_to_dataframe(quote) -> pd.DataFrame:
    """将 StockQuote 转为 DataFrame"""
    if not quote or not quote.quote_lines:
        return pd.DataFrame()
    df = pd.DataFrame(
        [
            {
                "trade_date": q.trade_date.date(),
                "open_price": q.open,
                "high_price": q.high,
                "low_price": q.low,
                "close_price": q.close,
                "volume": int(q.volume),
                "amount": q.amount,
            }
            for q in quote.quote_lines
        ]
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


async def _fetch_all_async(stock_code: str, market: str, end_date: str) -> dict:
    """
    异步并行拉取三种复权类型的行情数据。
    返回 {"none": DataFrame, "forward": DataFrame, "backward": DataFrame}
    """
    reader = EastmoneyQuoteReader()

    async def fetch_one(adjust_type: AdjustPriceType):
        return await reader.read_quote_async(
            market=market,
            stock_code=stock_code,
            adjust_type=adjust_type,
            period_type=PeriodType.DAILY,
            end_date=end_date,
            limit=5000,
        )

    # 三路并行
    results = await asyncio.gather(
        fetch_one(AdjustPriceType.NONE),
        fetch_one(AdjustPriceType.FORWARD),
        fetch_one(AdjustPriceType.BACKWARD),
        return_exceptions=True,
    )

    keys = ["none", "forward", "backward"]
    out = {}
    for key, result in zip(keys, results):
        if isinstance(result, Exception):
            print(f"[{stock_code}] {key} 拉取异常: {result}")
            out[key] = None
        else:
            out[key] = _quote_to_dataframe(result) if result else None
    return out


def fetch_stock_data_full(
    db: Session,
    stock_code: str,
    start_date: str = "2006-01-01",
    end_date: Optional[str] = None,
) -> dict:
    """
    拉取单只股票的三种复权数据并写入数据库。

    - 不复权 → open_price / high_price / low_price / close_price / volume / amount
    - 前复权 → forward_open / forward_high / forward_low / forward_close
    - 后复权 → backward_open / backward_high / backward_low / backward_close

    返回 {"stock_code": str, "status": str, "total_rows": int, "details": [...]}
    """
    market = _guess_market(stock_code)
    if end_date is None:
        end_date = date.today().strftime("%Y%m%d")

    # 1. 并行拉取三种复权
    try:
        data = asyncio.run(_fetch_all_async(stock_code, market, end_date))
    except Exception as e:
        return {
            "stock_code": stock_code,
            "status": "error",
            "total_rows": 0,
            "details": [f"拉取失败: {str(e)}"],
        }

    # 2. 检查不复权数据（主体）
    df_none = data.get("none")
    if df_none is None or df_none.empty:
        return {
            "stock_code": stock_code,
            "status": "error",
            "total_rows": 0,
            "details": ["不复权数据为空，请检查股票代码或网络"],
        }

    # 3. 过滤起始日期
    start_dt = pd.Timestamp(start_date)
    df_none = df_none[df_none["trade_date"] >= start_dt]
    if df_none.empty:
        return {
            "stock_code": stock_code,
            "status": "no_new_data",
            "total_rows": 0,
            "details": [f"{start_date} 之后无数据"],
        }

    # 4. 合并三种复权价格
    df = df_none.set_index("trade_date").sort_index()

    # 合并前复权价格
    df_forward = data.get("forward")
    if df_forward is not None and not df_forward.empty:
        df_forward = df_forward.set_index("trade_date")
        for col in ["open_price", "high_price", "low_price", "close_price"]:
            suffix = col.split("_")[0]  # open, high, low, close
            df[f"forward_{suffix}"] = df_forward[col]

    # 合并后复权价格
    df_backward = data.get("backward")
    if df_backward is not None and not df_backward.empty:
        df_backward = df_backward.set_index("trade_date")
        for col in ["open_price", "high_price", "low_price", "close_price"]:
            suffix = col.split("_")[0]
            df[f"backward_{suffix}"] = df_backward[col]

    # 5. 去重：查询已存在的日期
    existing = pd.read_sql(
        sa_text("SELECT trade_date FROM stock_daily_quote WHERE stock_code = :code"),
        con=db.bind,
        params={"code": stock_code},
    )
    exist_set = set()
    if not existing.empty:
        exist_set = set(pd.to_datetime(existing["trade_date"]).dt.date)

    # 使用 Pandas Series 进行 isin 判断（兼容性更好）
    date_series = pd.Series(df.index.date)  # 转为 Series
    mask = date_series.isin(exist_set)  # 返回布尔 Series
    new_rows = df[~mask].copy()
    update_rows = df[mask].copy()

    details = []
    new_count = 0
    update_count = 0

    # 6. 写入新行
    if not new_rows.empty:
        new_rows = new_rows.reset_index()
        new_rows["stock_code"] = stock_code
        cols_to_write = [
            "stock_code",
            "trade_date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "amount",
        ]
        # 只写存在的列
        for adj_col in [
            "forward_open",
            "forward_high",
            "forward_low",
            "forward_close",
            "backward_open",
            "backward_high",
            "backward_low",
            "backward_close",
        ]:
            if adj_col in new_rows.columns:
                cols_to_write.append(adj_col)

        new_rows[cols_to_write].to_sql(
            name="stock_daily_quote",
            con=db.bind,
            if_exists="append",
            index=False,
            chunksize=500,
        )
        new_count = len(new_rows)

    # 7. 更新已有行的复权价格（批量）
    if not update_rows.empty and any(
        c in update_rows.columns
        for c in [
            "forward_open",
            "forward_high",
            "forward_low",
            "forward_close",
            "backward_open",
            "backward_high",
            "backward_low",
            "backward_close",
        ]
    ):
        set_clauses = []
        for adj_col in [
            "forward_open",
            "forward_high",
            "forward_low",
            "forward_close",
            "backward_open",
            "backward_high",
            "backward_low",
            "backward_close",
        ]:
            if adj_col in update_rows.columns:
                set_clauses.append(f"{adj_col} = :{adj_col}")

        if set_clauses:
            # 构建批量更新参数列表
            update_params_list = []
            for idx, row in update_rows.iterrows():
                params = {"code": stock_code, "date": idx.strftime("%Y-%m-%d")}
                for adj_col in [
                    "forward_open",
                    "forward_high",
                    "forward_low",
                    "forward_close",
                    "backward_open",
                    "backward_high",
                    "backward_low",
                    "backward_close",
                ]:
                    if adj_col in row and pd.notna(row[adj_col]):
                        params[adj_col] = float(row[adj_col])
                if len(params) > 2:
                    update_params_list.append(params)

            if update_params_list:
                set_str = ", ".join(set_clauses)
                # 使用 executemany 批量执行
                db.execute(
                    sa_text(
                        f"UPDATE stock_daily_quote SET {set_str} "
                        f"WHERE stock_code = :code AND trade_date = :date"
                    ),
                    update_params_list,
                )
                db.commit()
                update_count = len(update_rows)

    # 8. 收集详情
    if new_count > 0:
        details.append(f"不复权: 新增 {new_count} 条")
    else:
        details.append("不复权: 数据已是最新")

    forward_ok = data.get("forward") is not None and not data["forward"].empty
    backward_ok = data.get("backward") is not None and not data["backward"].empty

    if forward_ok:
        details.append(
            f"前复权: {'已更新' if update_count > 0 or new_count > 0 else '无新数据'}"
        )
    else:
        details.append("前复权: 获取失败")

    if backward_ok:
        details.append(
            f"后复权: {'已更新' if update_count > 0 or new_count > 0 else '无新数据'}"
        )
    else:
        details.append("后复权: 获取失败")

    failed = [d for d in details if "失败" in d]
    if failed and new_count == 0:
        status = "partial_error"
    elif new_count > 0:
        status = "ok"
    else:
        status = "no_new_data"

    return {
        "stock_code": stock_code,
        "status": status,
        "total_rows": new_count + update_count,
        "details": details,
    }


# ---- 保留旧接口兼容 ----
def fetch_stock_data(
    db: Session,
    stock_code: str,
    start_date: str = "2006-01-01",
) -> dict:
    """拉取单只股票数据（仅不复权），兼容旧接口。"""
    result = fetch_stock_data_full(db, stock_code, start_date)
    # 转换为旧格式
    detail_msgs = result.get("details", [])
    return {
        "stock_code": stock_code,
        "new_rows": result["total_rows"],
        "message": "; ".join(detail_msgs) if detail_msgs else result["status"],
    }
