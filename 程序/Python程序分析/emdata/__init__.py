"""
emdata - 股票数据获取模块

支持多种数据源，通过 config/datasource.py 切换:
    export DATA_SOURCE=eastmoney   # 东方财富 (默认)
    export DATA_SOURCE=akshare     # AKShare

工厂函数 (推荐使用，自动根据配置选择数据源):
    from emdata import get_quote_reader, get_stock_list_reader, get_core_data_reader

直接导入特定数据源:
    from emdata import EastmoneyQuoteReader, AKShareQuoteReader
    from emdata import Market, AdjustPriceType, PeriodType
"""

from emdata.config import MAX_RETRIES, RETRY_DELAY_MIN, RETRY_DELAY_MAX, _is_connection_error, SEED_COOKIE
from emdata.enums import Market, AdjustPriceType, PeriodType
from emdata.models import StockQuoteLine, StockQuote, QuoteMappers, StockInfo
from emdata.cookie import generate_eastmoney_cookie_str
from emdata.quote_reader import EastmoneyQuoteReader
from emdata.stock_list_reader import EastmoneyStockListReader
from emdata.core_data_reader import EastmoneyCurrentCoreDataReader
from emdata.akshare_reader import (
    AKShareQuoteReader,
    AKShareStockListReader,
    AKShareCoreDataReader,
)


# ============================================================
#  工厂函数 —— 根据 config/datasource.py 配置自动选择数据源
# ============================================================

def get_quote_reader(*args, **kwargs):
    """
    获取行情读取器实例

    根据 config.datasource.DATA_SOURCE 自动选择:
        - "eastmoney" → EastmoneyQuoteReader
        - "akshare"   → AKShareQuoteReader

    用法:
        reader = get_quote_reader()
        quote = await reader.read_quote_async(...)
    """
    from config.datasource import get_data_source
    ds = get_data_source()
    if ds == "akshare":
        return AKShareQuoteReader(*args, **kwargs)
    return EastmoneyQuoteReader(*args, **kwargs)


def get_stock_list_reader(*args, **kwargs):
    """
    获取股票列表读取器实例

    用法:
        reader = get_stock_list_reader()
        stocks = await reader.fetch_all_stocks(...)
    """
    from config.datasource import get_data_source
    ds = get_data_source()
    if ds == "akshare":
        return AKShareStockListReader(*args, **kwargs)
    return EastmoneyStockListReader(*args, **kwargs)


def get_core_data_reader(*args, **kwargs):
    """
    获取核心数据读取器实例

    用法:
        reader = get_core_data_reader()
        info = await reader.fetch_stock_info_async(...)
    """
    from config.datasource import get_data_source
    ds = get_data_source()
    if ds == "akshare":
        return AKShareCoreDataReader(*args, **kwargs)
    return EastmoneyCurrentCoreDataReader(*args, **kwargs)


__all__ = [
    # 配置常量
    "MAX_RETRIES", "RETRY_DELAY_MIN", "RETRY_DELAY_MAX", "_is_connection_error",
    # 枚举
    "Market", "AdjustPriceType", "PeriodType",
    # 数据模型
    "StockQuoteLine", "StockQuote", "QuoteMappers", "StockInfo",
    # Cookie 工具
    "generate_eastmoney_cookie_str",
    # 东方财富读取器
    "EastmoneyQuoteReader",
    "EastmoneyStockListReader",
    "EastmoneyCurrentCoreDataReader",
    # AKShare 读取器
    "AKShareQuoteReader",
    "AKShareStockListReader",
    "AKShareCoreDataReader",
    # 工厂函数
    "get_quote_reader",
    "get_stock_list_reader",
    "get_core_data_reader",
]
