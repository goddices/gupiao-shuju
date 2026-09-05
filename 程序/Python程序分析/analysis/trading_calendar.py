"""
交易日历 —— 假日 JSON 加载与交易日判断

收敛「节日涨跌分析 HolidayAnalyzer.load_holiday_data/_build_non_trading_set/
is_trading_day/find_trading_days_around」与「backend/services.py
_load_holiday_data」两份重复实现；同时供星期涨跌预测等场景做节假日感知的
下一交易日推算。

假日数据目录: <项目根>/public_data/cn_holidays/china_holidays_{year}.json
"""
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta

# 主要节日列表（按重要性排序，与历史实现一致）
MAJOR_HOLIDAYS = ["春节", "国庆节", "劳动节", "端午节", "中秋节", "清明节", "元旦"]

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "public_data", "cn_holidays",
)


def _to_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()


def _to_str(v) -> str:
    """date/datetime/字符串 → 'YYYY-MM-DD'"""
    if isinstance(v, str):
        return v[:10]
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    return str(v)[:10]


def load_holiday_data(start_year: int = 2008, end_year: int = 2026,
                      data_dir: str = _DATA_DIR) -> tuple:
    """加载各年假日 JSON

    :return: (holiday_events, non_trading_dates_set)
        holiday_events: [{"name","year","start","end","dates"}]
        non_trading_dates_set: 非交易日 = 周末 ∪ 法定假 - 补班日
    """
    public_holidays = set()
    transfer_workdays = set()
    holiday_events_by_name = defaultdict(list)

    for year in range(start_year, end_year + 1):
        filename = os.path.join(data_dir, f"china_holidays_{year}.json")
        if not os.path.exists(filename):
            continue
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("dates", []):
            d = entry["date"]
            if entry["type"] == "public_holiday":
                public_holidays.add(d)
                holiday_events_by_name[(entry["name"], year)].append(d)
            elif entry["type"] == "transfer_workday":
                transfer_workdays.add(d)

    holiday_events = []
    for (name, year), dates in holiday_events_by_name.items():
        if name not in MAJOR_HOLIDAYS:
            continue
        dates_sorted = sorted(dates)
        holiday_events.append({
            "name": name,
            "year": year,
            "start": dates_sorted[0],
            "end": dates_sorted[-1],
            "dates": dates_sorted,
        })
    holiday_events.sort(key=lambda x: (x["year"], MAJOR_HOLIDAYS.index(x["name"])))

    # 构建非交易日集合
    non_trading = set()
    current = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    while current <= end:
        d_str = current.strftime("%Y-%m-%d")
        is_weekend = current.weekday() >= 5
        is_holiday = d_str in public_holidays
        is_workday_transfer = d_str in transfer_workdays
        if (is_weekend or is_holiday) and not is_workday_transfer:
            non_trading.add(d_str)
        current += timedelta(days=1)

    return holiday_events, non_trading


class TradingCalendar:
    """交易日历: 非交易日 = 周末 ∪ 法定假 - 补班日（范围由假日文件决定）"""

    def __init__(self, start_year: int = 2008, end_year: int = 2026):
        self.start_year = start_year
        self.end_year = end_year
        self.holiday_events, self.non_trading_dates = load_holiday_data(
            start_year, end_year)

    def is_trading_day(self, d) -> bool:
        return _to_str(d) not in self.non_trading_dates

    def _in_range(self, d: date) -> bool:
        return date(self.start_year, 1, 1) <= d <= date(self.end_year, 12, 31)

    def next_trading_day(self, d, max_iterations: int = 60) -> date:
        """d 之后第一个交易日；超出日历范围时退化为只跳过周末"""
        current = _to_date(d) + timedelta(days=1)
        for _ in range(max_iterations):
            if self._in_range(current):
                if self.is_trading_day(current):
                    return current
            elif current.weekday() < 5:
                return current
            current += timedelta(days=1)
        return current

    def prev_trading_day(self, d, max_iterations: int = 60) -> date:
        """d 之前第一个交易日；超出日历范围时退化为只跳过周末"""
        current = _to_date(d) - timedelta(days=1)
        for _ in range(max_iterations):
            if self._in_range(current):
                if self.is_trading_day(current):
                    return current
            elif current.weekday() < 5:
                return current
            current -= timedelta(days=1)
        return current


def find_trading_days_around(target_date_str: str, direction: str = "before",
                             count: int = 7, calendar: TradingCalendar = None,
                             trading_dates: set = None,
                             max_iterations: int = 60) -> list:
    """从目标日期起向前/后找 count 个交易日

    优先使用实际行情中出现的交易日集合（trading_dates），
    否则按日历规则判断。
    :return: ['YYYY-MM-DD', ...]（before 时按时间倒序，与历史实现一致）
    """
    if calendar is None:
        calendar = TradingCalendar()
    result = []
    target = datetime.strptime(str(target_date_str)[:10], "%Y-%m-%d")
    current = target + timedelta(days=-1 if direction == "before" else 1)

    for _ in range(max_iterations):
        if len(result) >= count:
            break
        d_str = current.strftime("%Y-%m-%d")
        if trading_dates:
            is_trading = d_str in trading_dates
        else:
            is_trading = calendar.is_trading_day(d_str)
        if is_trading:
            result.append(d_str)
        current += timedelta(days=-1 if direction == "before" else 1)

    return result
