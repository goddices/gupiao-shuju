"""
TickFlow 数据源实现 —— 与 emdata 完全一致的接口

用法:
    from emdata.tickflow_reader import TickFlowQuoteReader

接口对应关系:
    TickFlowQuoteReader  ←→ EastmoneyQuoteReader / AKShareQuoteReader

底层走单条 K 线接口（client.klines.get，逐只获取）:
    read_quote[_async]         单只获取
    read_quotes_batch[_async]  多只获取，内部逐只循环单条接口

注意: 批量接口 /v1/klines/batch 需要额外权限，当前 key 无权限
（NO_KLINE_BATCH_PERMISSION），故未使用；key 升级后可从
git 提交 503ef79 恢复批量实现。

API Key 默认使用 tickflow方式.md 中提供的 key，
可通过环境变量 TICKFLOW_API_KEY 覆盖。
"""

import os
from datetime import datetime
from typing import Optional, Any, Dict, List

import pandas as pd

from emdata.enums import AdjustPriceType, PeriodType
from emdata.models import StockQuoteLine, StockQuote, QuoteMappers


# 单次单标的最多获取 10000 根 K 线
MAX_KLINES = 10000


def _get_api_key() -> str:
    """获取 API Key：仅从环境变量 TICKFLOW_API_KEY 读取（2026-09 移除仓库内硬编码默认 key，
    旧默认 key 视为已泄漏，请轮换后经 env 注入，见 tickflow方式.md）"""
    key = os.getenv("TICKFLOW_API_KEY")
    if not key:
        raise RuntimeError(
            "未配置 TickFlow API Key：请设置环境变量 TICKFLOW_API_KEY"
            "（ export TICKFLOW_API_KEY=<你的 key> ），用法见 tickflow方式.md"
        )
    return key


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

    底层走单条 K 线接口（client.klines.get）：
    - read_quote[_async]：单只获取
    - read_quotes_batch[_async]：多只获取，内部逐只循环
      （批量接口 /v1/klines/batch 当前 key 无权限，未使用）
    """

    def __init__(self, mappers: QuoteMappers = None, cookie: str = None, db_cookies: list = None):
        self.mappers = mappers or QuoteMappers()
        self.api_key = _get_api_key()
        # cookie/db_cookies 参数仅保留兼容性，TickFlow 不需要

    # --------------------------------------------------------
    #  内部工具
    # --------------------------------------------------------

    @staticmethod
    def _to_symbols(market: str, stock_codes: List[str]) -> List[str]:
        """stock_code 列表 → TickFlow symbol 列表（已带 .SH/.SZ 后缀的原样保留）"""
        return [_code_to_symbol(code, market) for code in stock_codes]

    @staticmethod
    def _kline_params(adjust_type, period_type, end_date: str, limit: int) -> Dict[str, Any]:
        """构造 K 线接口公共参数（period/count/end_time/adjust），None 值不下发"""
        params = {
            "period": _period_to_tickflow(period_type),
            "count": min(limit, MAX_KLINES),
            "end_time": _end_date_to_ms(end_date),
            "adjust": _adjust_to_tickflow(adjust_type),
        }
        return {k: v for k, v in params.items() if v is not None}

    async def _fetch_each_async(
        self, symbols: List[str], params: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        """逐只并发调用单条 K 线接口（核心实现）"""
        import asyncio

        from tickflow import AsyncTickFlow

        async def fetch_one(client, symbol):
            try:
                return symbol, await client.klines.get(
                    symbol, **params, as_dataframe=True
                )
            except Exception as e:
                print(f"TickFlow 获取行情失败 {symbol}: {e}")
                return symbol, None

        async with AsyncTickFlow(api_key=self.api_key) as client:
            pairs = await asyncio.gather(*(fetch_one(client, s) for s in symbols))
        return {symbol: df for symbol, df in pairs}

    def _fetch_each(
        self, symbols: List[str], params: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        """逐只调用单条 K 线接口（核心实现）"""
        from tickflow import TickFlow

        dfs: Dict[str, pd.DataFrame] = {}
        client = TickFlow(api_key=self.api_key)
        try:
            for symbol in symbols:
                try:
                    dfs[symbol] = client.klines.get(
                        symbol, **params, as_dataframe=True
                    )
                except Exception as e:
                    print(f"TickFlow 获取行情失败 {symbol}: {e}")
                    dfs[symbol] = None
        finally:
            if hasattr(client, "close"):
                try:
                    client.close()
                except Exception:
                    pass
        return dfs

    @staticmethod
    def _dfs_to_quotes(
        stock_codes: List[str],
        symbols: List[str],
        dfs: Optional[Dict[str, pd.DataFrame]],
        period_type,
    ) -> Dict[str, StockQuote]:
        """批量返回的 {symbol: DataFrame} → {stock_code: StockQuote}（无数据的不出现）"""
        quotes: Dict[str, StockQuote] = {}
        for code, symbol in zip(stock_codes, symbols):
            df = dfs.get(symbol) if dfs else None
            quote = _df_to_quote(df, period_type)
            if quote is not None:
                quotes[code] = quote
        return quotes

    # --------------------------------------------------------
    #  多只获取（逐只循环单条接口）
    # --------------------------------------------------------

    async def read_quotes_batch_async(
        self,
        market: str,
        stock_codes: List[str],
        adjust_type: AdjustPriceType,
        period_type: PeriodType,
        end_date: str = "20500101",
        limit: int = 744,
        token: Any = None,
    ) -> Dict[str, StockQuote]:
        """
        异步获取多只股票行情（内部逐只并发调用单条 K 线接口）。

        返回 {stock_code: StockQuote}；获取失败或无数据的股票不出现在结果中。
        """
        if not stock_codes:
            return {}

        symbols = self._to_symbols(market, stock_codes)
        params = self._kline_params(adjust_type, period_type, end_date, limit)
        dfs = await self._fetch_each_async(symbols, params)
        return self._dfs_to_quotes(stock_codes, symbols, dfs, period_type)

    def read_quotes_batch(
        self,
        market: str,
        stock_codes: List[str],
        adjust_type: AdjustPriceType,
        period_type: PeriodType,
        end_date: str = "20500101",
        limit: int = 744,
    ) -> Dict[str, StockQuote]:
        """
        同步获取多只股票行情（内部逐只调用单条 K 线接口）。

        返回 {stock_code: StockQuote}；获取失败或无数据的股票不出现在结果中。
        """
        if not stock_codes:
            return {}

        symbols = self._to_symbols(market, stock_codes)
        params = self._kline_params(adjust_type, period_type, end_date, limit)
        dfs = self._fetch_each(symbols, params)
        return self._dfs_to_quotes(stock_codes, symbols, dfs, period_type)

    # --------------------------------------------------------
    #  单只获取
    # --------------------------------------------------------

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
        异步获取单只股票行情数据（单条 K 线接口）

        参数与 EastmoneyQuoteReader.read_quote_async 完全一致。
        """
        quotes = await self.read_quotes_batch_async(
            market, [stock_code], adjust_type, period_type, end_date, limit, token,
        )
        return quotes.get(stock_code)

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
        """同步获取单只股票行情数据（单条 K 线接口）"""
        quotes = self.read_quotes_batch(
            market, [stock_code], adjust_type, period_type, end_date, limit,
        )
        return quotes.get(stock_code)
