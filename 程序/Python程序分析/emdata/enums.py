"""
市场、复权、周期类型枚举
"""


class Market:
    """市场类型枚举"""

    SHANGHAI = "1"  # 上海证券交易所
    SHENGZHEN = "0"  # 深圳证券交易所


class AdjustPriceType:
    """复权类型枚举"""

    NONE = 0  # 不复权
    FORWARD = 1  # 前复权
    BACKWARD = 2  # 后复权


class PeriodType:
    """周期类型枚举"""

    UNSET = 0  # 未设置
    DAILY = 101  # 日线
    WEEKLY = 102  # 周线
    MONTHLY = 103  # 月线
    MINUTE_1 = 1  # 1分钟
    MINUTE_5 = 5  # 5分钟
    MINUTE_15 = 15  # 15分钟
    MINUTE_30 = 30  # 30分钟
    MINUTE_60 = 60  # 60分钟
