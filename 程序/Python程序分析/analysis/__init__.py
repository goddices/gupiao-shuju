"""
analysis - 股票分析公共类库

供「根目录中文脚本」与「backend 服务」共用的公共代码层:
    data_access      DB 数据装配四件套（行情/前复权/分红读取与同步）
    kline            emdata 之上的 K 线抓取模板
    trading_calendar 交易日历（假日 JSON + 交易日判断）
    metrics          收益指标（最大回撤、年化）
    chart_utils      matplotlib 公共绘图块（中文字体、权益曲线等）

导入说明:
    - 中文脚本: 脚本自身已把根目录加入 sys.path，直接 `from analysis import ...`
    - backend:  数据装配依赖 backend 的 models/database（命名空间包），
                data_access 会在导入时自动把 backend 目录加入 sys.path
"""

from analysis.data_access import (
    IMPL_PROGRESS,
    load_quotes,
    load_forward_quotes,
    load_dividends,
    ensure_dividends,
)
from analysis.kline import (
    PERIOD_MAPPING,
    EMPTY_COLUMNS,
    resolve_market,
    fetch_kline_df,
)
from analysis.trading_calendar import (
    MAJOR_HOLIDAYS,
    load_holiday_data,
    TradingCalendar,
    find_trading_days_around,
)
from analysis.metrics import (
    calc_max_drawdown,
    annualize_compound,
    PERIODS_PER_YEAR,
    annualize_by_period,
)
from analysis.chart_utils import (
    setup_chinese_fonts,
    EQUITY_COLORS,
    plot_equity_lines,
    set_date_ticks,
    mark_ex_dividend_dates,
    draw_year_dividend_bar,
)

__all__ = [
    # data_access
    "IMPL_PROGRESS", "load_quotes", "load_forward_quotes",
    "load_dividends", "ensure_dividends",
    # kline
    "PERIOD_MAPPING", "EMPTY_COLUMNS", "resolve_market", "fetch_kline_df",
    # trading_calendar
    "MAJOR_HOLIDAYS", "load_holiday_data", "TradingCalendar",
    "find_trading_days_around",
    # metrics
    "calc_max_drawdown", "annualize_compound",
    "PERIODS_PER_YEAR", "annualize_by_period",
    # chart_utils
    "setup_chinese_fonts", "EQUITY_COLORS", "plot_equity_lines",
    "set_date_ticks", "mark_ex_dividend_dates", "draw_year_dividend_bar",
]
