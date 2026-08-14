"""
TickFlow 数据源实现 —— 与 emdata 完全一致的接口

用法:
    from emdata.tickflow_reader import TickFlowQuoteReader

接口对应关系:
    TickFlowQuoteReader  ←→ EastmoneyQuoteReader / AKShareQuoteReader

API Key 默认使用 tickflow方式.md 中提供的 key，
可通过环境变量 TICKFLOW_API_KEY 覆盖。
"""

import os
from datetime import datetime
from typing import Optional, Any

import pandas as pd

from emdata.enums import AdjustPriceType, PeriodType
from emdata.models import StockQuoteLine, StockQuote, QuoteMappers


# 默认 API Key（见 tickflow方式.md）
DEFAULT_API_KEY = "tk_aef1f7190ff44f32b5226f796a3c38ea"

# 单次单标的最多获取 10000 根 K 线
MAX_KLINES = 10000


def _get_api_key() -> str:
    """获取 API Key，优先环境变量"""
    return os.getenv("TICKFLOW_API_KEY", DEFAULT_API_KEY)


def _code_to_symbol(stock_code: str, market: str) -> str:
    """将 代码+市场 转为 TickFlow symbol 格式，如 600000 + 1 → 600000.SH"""
    code = stock_code.strip()
    if "." in code:
        return code  # 已带市场后缀

    suffix_map = {"1": "SH", "0": "SZ", "2": "BJ"}
    if market and str(market).upper() in ("SH", "SZ", "BJ", "US", "HK"):
        suffix = str(market).upper()
    else:
        suffix = suffix_map.get(str(market))

    if not suffix:
        # 根据代码前缀猜测：6/9=沪，4/8=北交所，其余=深
        if code.startswith(("6", "9")):
            suffix = "SH"
        elif code.startswith(("4", "8")):
            suffix = "BJ"
        else:
            suffix = "SZ"
    return f"{code}.{suffix}"


def _adjust_to_tickflow(adjust_type) -> str:
    """将 AdjustPriceType 转为 TickFlow adjust 参数。
    使用差值复权（forward_additive/backward_additive），与东方财富、同花顺一致。"""
    mapping = {
        AdjustPriceType.NONE: "none",
        AdjustPriceType.FORWARD: "forward_additive",
        AdjustPriceType.BACKWARD: "backward_additive",
    }
    return mapping.get(adjust_type, "none")


def _period_to_tickflow(period_type) -> str:
    """将 PeriodType 转为 TickFlow period 参数"""
    mapping = {
        PeriodType.DAILY: "1d",
        PeriodType.WEEKLY: "1w",
        PeriodType.MONTHLY: "1M",
        PeriodType.MINUTE_1: "1m",
        PeriodType.MINUTE_5: "5m",
        PeriodType.MINUTE_15: "15m",
        PeriodType.MINUTE_30: "30m",
        PeriodType.MINUTE_60: "60m",
    }
    return mapping.get(period_type, "1d")


def _end_date_to_ms(end_date: str) -> Optional[int]:
    """将 YYYYMMDD 转为当日 23:59:59 的毫秒时间戳；无效值返回 None（默认取到当前）"""
    if not end_date or end_date == "20500101":
        return None
    try:
        dt = datetime.strptime(end_date, "%Y%m%d")
        return int(dt.replace(hour=23, minute=59, second=59).timestamp() * 1000)
    except ValueError:
        return None


def _df_to_quote(df: pd.DataFrame, period_type) -> Optional[StockQuote]:
    """将 TickFlow 返回的 DataFrame 转为 StockQuote"""
    if df is None or df.empty:
        return None

    stock_name = "未知股票"
    if "name" in df.columns and pd.notna(df["name"].iloc[0]):
        stock_name = str(df["name"].iloc[0])

    quote_lines = []
    for _, row in df.iterrows():
        try:
            trade_date = pd.Timestamp(row["trade_date"]).to_pydatetime()
            quote_lines.append(StockQuoteLine(
                trade_date=trade_date,
                open_price=float(row["open"]),
                close_price=float(row["close"]),
                high_price=float(row["high"]),
                low_price=float(row["low"]),
                trade_volume=float(row["volume"]),
                trade_amount=float(row["amount"]),
            ))
        except Exception as e:
            print(f"TickFlow 解析K线失败: {e}")
            continue

    if not quote_lines:
        return None

    # 按交易日排序
    quote_lines.sort(key=lambda x: x.trade_date)

    return StockQuote(
        stock_name=stock_name,
        quote_lines=quote_lines,
        period_type=period_type,
    )


# ============================================================
#  TickFlowQuoteReader —— K线数据读取器
# ============================================================

class TickFlowQuoteReader:
    """
    TickFlow 行情数据读取器
    接口与 EastmoneyQuoteReader / AKShareQuoteReader 完全一致
    """

    def __init__(self, mappers: QuoteMappers = None, cookie: str = None, db_cookies: list = None):
        self.mappers = mappers or QuoteMappers()
        self.api_key = _get_api_key()
        # cookie/db_cookies 参数仅保留兼容性，TickFlow 不需要

    async def read_quote_async(
        self,
        market: str,
        stock_code: str,
        adjust_type: AdjustPriceType,
        period_type: PeriodType,
        end_date: str = "20500101",
        limit: int = 744,
        token: Any = None,
    ) -> Optional[StockQuote]:
        """
        异步获取股票行情数据（TickFlow 实现）

        参数与 EastmoneyQuoteReader.read_quote_async 完全一致。
        """
        from tickflow import AsyncTickFlow

        symbol = _code_to_symbol(stock_code, market)
        period = _period_to_tickflow(period_type)
        adjust = _adjust_to_tickflow(adjust_type)
        end_ms = _end_date_to_ms(end_date)
        count = min(limit, MAX_KLINES)

        try:
            async with AsyncTickFlow(api_key=self.api_key) as client:
                df = await client.klines.get(
                    symbol,
                    period=period,
                    count=count,
                    end_time=end_ms,
                    adjust=adjust,
                    as_dataframe=True,
                )
        except Exception as e:
            print(f"TickFlow 获取行情失败 {symbol}: {e}")
            return None

        return _df_to_quote(df, period_type)

    async def read_quote_from_stream_async(
        self, stream: Any, token: Any = None
    ) -> Optional[StockQuote]:
        """
        从流中读取行情数据（TickFlow 不走流式接口，返回 None）
        """
        return None

    def read_quote(
        self,
        market: str,
        stock_code: str,
        adjust_type: AdjustPriceType,
        period_type: PeriodType,
        end_date: str = "20500101",
        limit: int = 744,
    ) -> Optional[StockQuote]:
        """同步获取股票行情数据"""
        from tickflow import TickFlow

        symbol = _code_to_symbol(stock_code, market)
        period = _period_to_tickflow(period_type)
        adjust = _adjust_to_tickflow(adjust_type)
        end_ms = _end_date_to_ms(end_date)
        count = min(limit, MAX_KLINES)

        client = TickFlow(api_key=self.api_key)
        try:
            df = client.klines.get(
                symbol,
                period=period,
                count=count,
                end_time=end_ms,
                adjust=adjust,
                as_dataframe=True,
            )
        except Exception as e:
            print(f"TickFlow 获取行情失败 {symbol}: {e}")
            return None
        finally:
            if hasattr(client, "close"):
                try:
                    client.close()
                except Exception:
                    pass

        return _df_to_quote(df, period_type)
