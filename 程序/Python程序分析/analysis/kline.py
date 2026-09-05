"""
K 线抓取模板 —— emdata 之上的统一数据获取

把第一代分析脚本（星期涨跌分析 / 节日涨跌分析 / 波动分析 / 线性回归 /
模拟持仓）中逐行复制的 fetch_kline_data 收敛为单一函数:

    df, quote_name = await fetch_kline_df("000001", "2008-01-01", "2026-01-01",
                                          stock_name="上证指数")
"""
from datetime import datetime

import pandas as pd

from emdata import AdjustPriceType, Market, PeriodType, get_quote_reader

PERIOD_MAPPING = {
    "daily": PeriodType.DAILY,
    "weekly": PeriodType.WEEKLY,
    "monthly": PeriodType.MONTHLY,
}

# 与历史脚本保持一致的统一空 DataFrame 列名
EMPTY_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def resolve_market(stock_code: str, stock_name: str = "") -> str:
    """判断交易所: 000001(上证指数) 与 6 开头 → 沪市，其余 → 深市"""
    if stock_code == "000001" and stock_name in ("上证指数", "上证综指", ""):
        return Market.SHANGHAI
    return Market.SHANGHAI if stock_code.startswith("6") else Market.SHENGZHEN


async def fetch_kline_df(
    stock_code: str,
    start_date: str,
    end_date: str,
    stock_name: str = "",
    period: str = "daily",
    adjust=AdjustPriceType.NONE,
    limit: int = None,
    raise_on_empty: bool = False,
    log=print,
) -> tuple:
    """抓取 K 线并转为 DataFrame（按日期升序、按区间过滤）

    :param period: daily / weekly / monthly
    :param adjust: AdjustPriceType.NONE（不复权）/ FORWARD（前复权）等
    :param limit: 抓取条数；None 时日线按区间天数自动估算
    :param raise_on_empty: True 时数据为空抛 RuntimeError（模拟持仓等严格场景）
    :return: (df, 行情接口返回的股票名称)
    """
    end_date = end_date or datetime.now().strftime("%Y-%m-%d")
    period_type = PERIOD_MAPPING.get(str(period).lower(), PeriodType.DAILY)
    market_code = resolve_market(stock_code, stock_name)

    if limit is None:
        if period_type == PeriodType.DAILY:
            days_diff = (
                datetime.strptime(end_date, "%Y-%m-%d")
                - datetime.strptime(start_date, "%Y-%m-%d")
            ).days + 100
            limit = min(max(days_diff, 1000), 5000)
        else:
            limit = 2000

    log(f"正在获取{stock_name}({stock_code}) {start_date}至{end_date}的{period}K线数据...")
    reader = get_quote_reader()

    quote = None
    try:
        quote = await reader.read_quote_async(
            market=market_code,
            stock_code=stock_code,
            adjust_type=adjust,
            period_type=period_type,
            end_date=end_date.replace("-", ""),
            limit=limit,
        )
    except Exception as e:
        log(f"获取数据时出错: {e}")

    if quote is None:
        msg = f"无法获取{stock_name}({stock_code})的数据"
        if raise_on_empty:
            raise RuntimeError(msg)
        log(msg)
        return pd.DataFrame(columns=EMPTY_COLUMNS), ""

    rows = [
        {
            "date": line.trade_date,
            "open": line.open,
            "high": line.high,
            "low": line.low,
            "close": line.close,
            "volume": line.volume,
        }
        for line in quote.quote_lines
    ]
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    if start_date or end_date:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)].reset_index(drop=True)

    if df.empty and raise_on_empty:
        raise RuntimeError(f"{start_date} 至 {end_date} 范围内无交易数据")

    log(f"成功获取 {len(df)} 条{period}K线数据")
    return df, quote.stock_name
