"""
收益指标 —— 最大回撤与年化收益率

口径与 dividend_reinvest_engine 内置的 _calc_max_drawdown/_annualize 保持一致；
引擎保持零依赖自包含不 import 本模块，脚本侧（模拟持仓、线性回归等）统一
从这里引用，避免三种年化写法并存。
"""
import statistics
from typing import List, Optional, Sequence

# 各周期每年期数（线性回归口径）
PERIODS_PER_YEAR = {"daily": 250, "weekly": 52, "monthly": 12}


def calc_max_drawdown(assets: Sequence[float]) -> float:
    """最大回撤(%)，从资产序列计算"""
    if not assets:
        return 0.0
    peak = assets[0]
    max_dd = 0.0
    for value in assets:
        peak = max(peak, value)
        if peak > 0:
            max_dd = max(max_dd, (peak - value) / peak * 100)
    return max_dd


def annualize_compound(final: float, initial: float,
                       days: int) -> Optional[float]:
    """按自然日复利年化 (final/initial)^(365/days) - 1；条件不足返回 None"""
    if days <= 0 or initial <= 0 or final <= 0:
        return None
    return (final / initial) ** (365.0 / days) - 1


def annualize_by_period(final: float, initial: float, periods: int,
                        period: str = "daily") -> Optional[float]:
    """按周期年化 (final/initial)^(periods_per_year/periods) - 1

    :param periods: 总期数（交易日数/周数/月数）
    :param period: "daily"(250期/年) / "weekly"(52) / "monthly"(12)
    """
    if periods <= 0 or initial <= 0 or final <= 0:
        return None
    periods_per_year = PERIODS_PER_YEAR.get(str(period).lower(), 250)
    return (final / initial) ** (periods_per_year / periods) - 1


def pct_change_series(close: Sequence[float]) -> List[Optional[float]]:
    """逐期涨跌幅(%)序列，首元素为 None（无前值）；前值为 0 时该期为 None"""
    result: List[Optional[float]] = [None]
    for prev, cur in zip(close, close[1:]):
        result.append((cur - prev) / prev * 100 if prev else None)
    return result


def change_stats(values) -> dict:
    """涨跌幅统计（统一口径，供波动/星期/节日/分红后统计四处共用）

    返回键: count/up_count/down_count/flat_count/up_pct/down_pct/mean/median/std/max_gain/max_loss
    - 原始值不舍入，键名映射与舍入由各调用方 wrapper 处理
    - None 被忽略；空组返回同形状全 0 字典
    - std 为样本标准差(ddof=1)，n<2 时取 0.0
    - median 为 statistics.median（偶数取两中位平均；旧分红后统计取上中位的差异被有意统一）
    """
    vals = [v for v in values if v is not None]
    if not vals:
        return dict.fromkeys(
            ("count", "up_count", "down_count", "flat_count", "up_pct",
             "down_pct", "mean", "median", "std", "max_gain", "max_loss"), 0)
    count = len(vals)
    up = sum(1 for v in vals if v > 0)
    down = sum(1 for v in vals if v < 0)
    return {
        "count": count,
        "up_count": up,
        "down_count": down,
        "flat_count": count - up - down,
        "up_pct": up / count * 100,
        "down_pct": down / count * 100,
        "mean": statistics.mean(vals),
        "median": statistics.median(vals),
        "std": statistics.stdev(vals) if count >= 2 else 0.0,
        "max_gain": max(vals),
        "max_loss": min(vals),
    }


def total_return_pct(initial: float, final: float) -> Optional[float]:
    """期初→期末总收益率(%)；initial<=0 返回 None"""
    if initial <= 0:
        return None
    return (final - initial) / initial * 100


def cumulative_return(change_pct_series) -> float:
    """复合累计收益（小数倍），输入为涨跌幅(%)序列，忽略 None 元素"""
    product = 1.0
    for x in change_pct_series:
        if x is None:
            continue
        product *= 1 + x / 100.0
    return product - 1
