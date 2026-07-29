"""拉取股票数据（不复权+前复权+后复权）并写入数据库，支持多数据源"""

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

from emdata import (
    get_quote_reader,
    Market,
    AdjustPriceType,
    PeriodType,
)
from models import StockDailyQuote, StockCoreData


def _guess_market(stock_code: str) -> str:
    """根据股票代码推断市场：6开头=上海，0/3开头=深圳（上证指数000001例外=上海）"""
    if stock_code == "000001":
        return Market.SHANGHAI  # 上证指数
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


async def _fetch_all_async(stock_code: str, market: str, end_date: str, db_cookies: list = None) -> dict:
    """
    异步并行拉取三种复权类型的行情数据。
    返回 {"none": DataFrame, "forward": DataFrame, "backward": DataFrame}
    """
    reader = get_quote_reader(db_cookies=db_cookies)

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

    # 0. 尝试从核心数据获取上市日期作为起始日期
    if start_date == "2006-01-01":
        core = db.query(StockCoreData).filter(StockCoreData.stock_code == stock_code).first()
        if core and core.list_date:
            try:
                # 校验 list_date 格式为 YYYY-MM-DD (10字符) 或 YYYYMMDD (8字符)
                ld = str(core.list_date).strip()
                if len(ld) in (8, 10) and ld[:4].isdigit():
                    pd.Timestamp(ld)  # 验证可解析
                    start_date = ld
            except (ValueError, pd.errors.OutOfBoundsDatetime):
                pass  # 格式异常则保持默认 start_date

    # 1. 并行拉取三种复权
    try:
        # 从数据库加载已验证的 Cookie 列表作为最终兜底
        from services import get_fallback_cookies
        db_cookies = get_fallback_cookies(db)
        data = asyncio.run(_fetch_all_async(stock_code, market, end_date, db_cookies))
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

    # 直接使用 df.index.isin，索引自动对齐，不会报错
    mask = df.index.isin(exist_set)
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

    # 7. 更新已有行：全部价格替换为新数据
    if not update_rows.empty:
        all_price_cols = [
            "open_price", "high_price", "low_price", "close_price",
            "volume", "amount",
            "forward_open", "forward_high", "forward_low", "forward_close",
            "backward_open", "backward_high", "backward_low", "backward_close",
        ]
        # 只更新 update_rows 中实际存在的列
        set_clauses = []
        for col in all_price_cols:
            if col in update_rows.columns:
                set_clauses.append(f"{col} = :{col}")

        if set_clauses:
            update_params_list = []
            for idx, row in update_rows.iterrows():
                params = {"code": stock_code, "date": idx.strftime("%Y-%m-%d")}
                for col in all_price_cols:
                    if col in row and pd.notna(row[col]):
                        params[col] = float(row[col])
                update_params_list.append(params)

            if update_params_list:
                set_str = ", ".join(set_clauses)
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

    if update_count > 0:
        details.append(f"已替换 {update_count} 条已有记录的全部价格")
    else:
        details.append("无已有记录需要替换")

    failed = [d for d in details if "失败" in d]
    if failed and new_count == 0 and update_count == 0:
        status = "error"
    elif new_count > 0 or update_count > 0:
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
