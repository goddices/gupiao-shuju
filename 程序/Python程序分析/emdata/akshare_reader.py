"""
AKShare 数据源实现 —— 实现与 emdata 完全一致的接口

用法:
    from emdata.akshare_reader import (
        AKShareQuoteReader,
        AKShareStockListReader,
        AKShareCoreDataReader,
    )

接口对应关系:
    AKShareQuoteReader       ←→ EastmoneyQuoteReader
    AKShareStockListReader   ←→ EastmoneyStockListReader
    AKShareCoreDataReader    ←→ EastmoneyCurrentCoreDataReader
"""

import asyncio
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any

from emdata.enums import Market, AdjustPriceType, PeriodType
from emdata.models import StockQuoteLine, StockQuote, QuoteMappers, StockInfo


# ============================================================
#  工具函数：市场/周期/复权类型转换
# ============================================================

def _market_to_akshare(code: str, market: str) -> str:
    """将 emdata 市场代码转为 AKShare symbol 格式。
    AKShare 直接使用 6 位数字代码即可，不需前后缀。
    """
    return code


def _period_to_akshare(period_type) -> str:
    """将 PeriodType 转为 AKShare period 参数"""
    mapping = {
        PeriodType.DAILY: "daily",
        PeriodType.WEEKLY: "weekly",
        PeriodType.MONTHLY: "monthly",
    }
    return mapping.get(period_type, "daily")


def _adjust_to_akshare(adjust_type) -> str:
    """将 AdjustPriceType 转为 AKShare adjust 参数"""
    mapping = {
        AdjustPriceType.NONE: "",
        AdjustPriceType.FORWARD: "qfq",
        AdjustPriceType.BACKWARD: "hfq",
    }
    return mapping.get(adjust_type, "")


def _date_to_akshare(date_str: str) -> str:
    """将 YYYYMMDD 转为 AKShare 日期格式 YYYYMMDD (相同)"""
    if not date_str or date_str == "20500101":
        return datetime.now().strftime("%Y%m%d")
    return date_str


# ============================================================
#  AKShareQuoteReader —— K线数据读取器
# ============================================================

class AKShareQuoteReader:
    """
    AKShare 行情数据读取器
    接口与 EastmoneyQuoteReader 完全一致
    """

    def __init__(self, mappers: QuoteMappers = None, cookie: str = None):
        self.mappers = mappers or QuoteMappers()
        # cookie 参数仅保留兼容性，AKShare 不需要 cookie

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
        异步获取股票行情数据（AKShare 实现）

        参数与 EastmoneyQuoteReader.read_quote_async 完全一致。
        AKShare 是同步库，此处在线程池中执行以避免阻塞事件循环。
        """
        return await asyncio.to_thread(
            self._read_quote_sync,
            market, stock_code, adjust_type, period_type, end_date, limit,
        )

    def _read_quote_sync(
        self,
        market: str,
        stock_code: str,
        adjust_type: AdjustPriceType,
        period_type: PeriodType,
        end_date: str,
        limit: int,
    ) -> Optional[StockQuote]:
        """同步获取 K 线数据（核心实现，含自动重试）"""
        import akshare as ak
        import time

        symbol = _market_to_akshare(stock_code, market)
        period = _period_to_akshare(period_type)
        adjust = _adjust_to_akshare(adjust_type)
        end = _date_to_akshare(end_date)

        # AKShare 用 start_date 参数，我们设为足够早的日期
        start_date = "19900101"

        # 自动重试（最多 3 次，应对 AKShare 偶发限流）
        last_error = None
        for attempt in range(3):
            try:
                df: pd.DataFrame = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end,
                    adjust=adjust,
                )
                if df is not None and not df.empty:
                    break
            except Exception as e:
                last_error = e
                if attempt < 2:
                    wait = 3 * (attempt + 1)
                    print(f"AKShare 获取行情失败 {stock_code} (attempt {attempt+1}): {e}，{wait}s后重试...")
                    time.sleep(wait)
        else:
            print(f"AKShare 获取行情失败 {stock_code}: {last_error}")
            return None

        if df is None or df.empty:
            return None

        # 限制条数（取最后 limit 条）
        if len(df) > limit:
            df = df.iloc[-limit:]

        # 获取股票名称（从 AKShare spot 数据中查询，或使用代码）
        stock_name = stock_code

        # 转换为 StockQuoteLine 列表
        quote_lines = []
        for _, row in df.iterrows():
            try:
                trade_date = pd.Timestamp(row["日期"]).to_pydatetime()
                quote_lines.append(StockQuoteLine(
                    trade_date=trade_date,
                    open_price=float(row["开盘"]),
                    close_price=float(row["收盘"]),
                    high_price=float(row["最高"]),
                    low_price=float(row["最低"]),
                    trade_volume=float(row["成交量"]),
                    trade_amount=float(row["成交额"]),
                ))
            except Exception as e:
                print(f"AKShare 解析K线失败: {e}")
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

    async def read_quote_from_stream_async(
        self, stream: Any, token: Any = None
    ) -> Optional[StockQuote]:
        """
        从流中读取行情数据（AKShare 不支持流式读取，返回 None）
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
        return self._read_quote_sync(
            market, stock_code, adjust_type, period_type, end_date, limit,
        )


# ============================================================
#  AKShareStockListReader —— 股票列表读取器
# ============================================================

class AKShareStockListReader:
    """
    AKShare 股票列表读取器
    接口与 EastmoneyStockListReader 一致
    """

    def __init__(self, cookie: Optional[str] = None):
        # cookie 参数仅保留兼容性
        pass

    async def fetch_page(
        self,
        session: Any,
        fs: str,
        page: int,
        size: int = 100,
        skip_first_cookie: bool = False,
    ) -> Optional[List[Dict]]:
        """
        异步获取单页股票列表

        fs 参数在 AKShare 中含义不同：
        - 东财用 fs 过滤板块，如 "m:0+t:6" 表示沪市A股
        - AKShare 直接获取全市场数据，这里忽略 fs 参数
        但保留分页逻辑以兼容接口
        """
        all_stocks = await self.fetch_all_stocks(fs, size=size)
        if all_stocks is None:
            return None

        start = (page - 1) * size
        end = start + size
        page_stocks = all_stocks[start:end]
        return page_stocks if page_stocks else None

    async def fetch_all_stocks(
        self, fs: str = "", size: int = 100, max_pages: int = 200
    ) -> List[Dict]:
        """
        获取全市场 A 股股票列表

        返回与 EastmoneyStockListReader 相同格式的 dict 列表:
        [{"code": "600519", "market": "1", "name": "贵州茅台", "price": ..., "change_pct": ..., ...}, ...]
        """
        return await asyncio.to_thread(self._fetch_all_sync)

    def _fetch_all_sync(self) -> List[Dict]:
        """同步获取全市场股票列表"""
        import akshare as ak

        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            print(f"AKShare 获取股票列表失败: {e}")
            return []

        if df is None or df.empty:
            return []

        stocks = []
        for _, row in df.iterrows():
            try:
                code = str(row.get("代码", "")).strip()
                if len(code) < 6:
                    continue

                # 推断市场: 6开头=上海(1), 0/3开头=深圳(0)
                market = "1" if code.startswith("6") else "0"

                stock = {
                    "code": code,
                    "market": market,
                    "name": str(row.get("名称", "")),
                    "price": _safe_float(row.get("最新价")),
                    "change_pct": _safe_float(row.get("涨跌幅")),
                    "change_amount": _safe_float(row.get("涨跌额")),
                    "volume": _safe_float(row.get("成交量")),
                    "pe": _safe_float(row.get("市盈率-动态")),
                }
                stocks.append(stock)
            except Exception:
                continue

        print(f"AKShare 共获取 {len(stocks)} 条股票记录")
        return stocks


# ============================================================
#  AKShareCoreDataReader —— 个股核心数据读取器
# ============================================================

class AKShareCoreDataReader:
    """
    AKShare 个股核心数据读取器
    接口与 EastmoneyCurrentCoreDataReader 一致
    """

    def __init__(self, cookie: Optional[str] = None):
        pass

    async def fetch_stock_info_async(
        self,
        market: str,
        stock_code: str,
        fallback_cookies: list = None,
    ) -> Optional[StockInfo]:
        """异步获取个股核心数据"""
        return await asyncio.to_thread(
            self._fetch_stock_info_sync, market, stock_code,
        )

    def _fetch_stock_info_sync(
        self, market: str, stock_code: str
    ) -> Optional[StockInfo]:
        """同步获取个股核心数据"""
        import akshare as ak

        info = StockInfo(stock_code=stock_code, market=market)

        # 1. 获取个股基本信息 (stock_individual_info_em)
        try:
            df_info = ak.stock_individual_info_em(symbol=stock_code)
            if df_info is not None and not df_info.empty:
                info_dict = {}
                for _, row in df_info.iterrows():
                    key = str(row.get("item", ""))
                    val = row.get("value")
                    info_dict[key] = val

                info.stock_name = str(info_dict.get("股票简称", "")) or None
                info.total_market_cap = _safe_float(info_dict.get("总市值"))
                info.float_market_cap = _safe_float(info_dict.get("流通市值"))
                info.total_shares = _safe_float(info_dict.get("总股本"))
                info.float_shares = _safe_float(info_dict.get("流通股"))
                # 上市日期
                list_date_raw = info_dict.get("上市时间")
                if list_date_raw:
                    try:
                        info.list_date = str(list_date_raw)
                    except Exception:
                        pass
        except Exception as e:
            print(f"AKShare 获取个股信息失败 {stock_code}: {e}")

        # 2. 获取实时行情 (stock_zh_a_spot_em 中筛选)
        try:
            df_spot = ak.stock_zh_a_spot_em()
            if df_spot is not None and not df_spot.empty:
                row = df_spot[df_spot["代码"] == stock_code]
                if not row.empty:
                    r = row.iloc[0]
                    info.pe_dynamic = _safe_float(r.get("市盈率-动态"))
                    info.pb = _safe_float(r.get("市净率"))
                    info.change_pct = _safe_float(r.get("涨跌幅"))
        except Exception as e:
            print(f"AKShare 获取实时行情失败 {stock_code}: {e}")

        # 3. 获取财务指标 (stock_financial_analysis_indicator)
        # AKShare 字段名含单位后缀如 "净资产收益率(%)"、"销售毛利率(%)"
        try:
            df_fin = ak.stock_financial_analysis_indicator(symbol=stock_code)
            if df_fin is not None and not df_fin.empty:
                # 找最近一条有数据的行（早期年份可能全 NaN）
                latest = None
                for i in range(len(df_fin)):
                    row = df_fin.iloc[i]
                    if row.notna().sum() > 10:  # 至少有10个有效字段
                        latest = row
                        break
                if latest is None:
                    latest = df_fin.iloc[-1]

                info.eps = _safe_float(latest.get("摊薄每股收益(元)")) or _safe_float(latest.get("每股收益_调整后(元)"))
                info.navps = _safe_float(latest.get("每股净资产_调整前(元)")) or _safe_float(latest.get("每股净资产_调整后(元)"))
                info.roe = _safe_float(latest.get("净资产收益率(%)"))
                info.gross_margin = _safe_float(latest.get("销售毛利率(%)"))
                info.net_margin = _safe_float(latest.get("销售净利率(%)"))
                info.revenue_yoy = _safe_float(latest.get("主营业务收入增长率(%)"))
                info.profit_yoy = _safe_float(latest.get("净利润增长率(%)"))
                info.debt_ratio = _safe_float(latest.get("资产负债率(%)"))
                info.retained_eps = _safe_float(latest.get("每股未分配利润(元)"))
                info.revenue = _safe_float(latest.get("主营业务利润(元)"))
                # 净利润: 从扣非净利润获取
                info.net_profit = _safe_float(latest.get("扣除非经常性损益后的净利润(元)"))
        except Exception as e:
            print(f"AKShare 获取财务指标失败 {stock_code}: {e}")

        # 如果所有字段都是 None（除了 stock_code 和 market），返回 None
        has_data = any(
            getattr(info, f.name) is not None
            for f in info.__dataclass_fields__.values()
            if f.name not in ("stock_code", "market")
        )
        return info if has_data else None

    def fetch_stock_info(
        self,
        market: str,
        stock_code: str,
        fallback_cookies: list = None,
    ) -> Optional[StockInfo]:
        """同步获取个股核心数据"""
        return self._fetch_stock_info_sync(market, stock_code)


# ============================================================
#  工具函数
# ============================================================

def _safe_float(value) -> Optional[float]:
    """安全转换为 float"""
    if value is None:
        return None
    try:
        if isinstance(value, str) and "%" in value:
            return float(value.replace("%", ""))
        return float(value)
    except (ValueError, TypeError):
        return None
