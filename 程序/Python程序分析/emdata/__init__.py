"""
emdata - 东方财富数据获取模块

用法:
    from emdata import EastmoneyQuoteReader, Market, AdjustPriceType, PeriodType
    from emdata import EastmoneyStockListReader, EastmoneyCurrentCoreDataReader
    from emdata import StockQuote, StockQuoteLine, StockInfo
    from emdata import generate_eastmoney_cookie_str
"""

from emdata.config import MAX_RETRIES, RETRY_DELAY_MIN, RETRY_DELAY_MAX, _is_connection_error
from emdata.enums import Market, AdjustPriceType, PeriodType
from emdata.models import StockQuoteLine, StockQuote, QuoteMappers, StockInfo
from emdata.cookie import generate_eastmoney_cookie_str
from emdata.quote_reader import EastmoneyQuoteReader
from emdata.stock_list_reader import EastmoneyStockListReader
from emdata.core_data_reader import EastmoneyCurrentCoreDataReader

__all__ = [
    "MAX_RETRIES", "RETRY_DELAY_MIN", "RETRY_DELAY_MAX", "_is_connection_error",
    "Market", "AdjustPriceType", "PeriodType",
    "StockQuoteLine", "StockQuote", "QuoteMappers", "StockInfo",
    "generate_eastmoney_cookie_str",
    "EastmoneyQuoteReader",
    "EastmoneyStockListReader",
    "EastmoneyCurrentCoreDataReader",
]
