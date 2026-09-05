"""
图表公共工具 —— matplotlib 中文环境与复用绘图块

收敛各脚本重复的:
    - 中文字体设置三行样板
    - 权益曲线三线配色
    - 日期刻度(12档)逻辑
    - 除息日标记散点
    - 年度分红到账柱状图
"""
import matplotlib.pyplot as plt

# 三线对比统一配色（与历史脚本一致）
EQUITY_COLORS = {
    "primary": "#cf1322",    # 策略主线（红利再投等）
    "secondary": "#1890ff",  # 对比线（分红不投等）
    "baseline": "#999999",   # 基准线（纯股价等，虚线）
    "marker": "#d4b106",     # 买入日/除息日标记
    "dividend_bar": "#fa8c16",  # 年度分红柱
}


def setup_chinese_fonts():
    """matplotlib 中文字体环境（SimHei 优先，Windows 可用）"""
    plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def plot_equity_lines(ax, dates, lines):
    """绘制多条权益曲线。

    :param lines: [(label, values, style_dict), ...]，style_dict 覆盖
                  线型/颜色/线宽等（如 {"linestyle": "--", "alpha": 0.8}）
    """
    for label, values, style in lines:
        ax.plot(dates, values, label=label, **style)


def set_date_ticks(ax, dates, max_ticks: int = 12):
    """按最多 max_ticks 个刻度设置日期横轴（旋转 30°）"""
    tick_step = max(1, len(dates) // max_ticks)
    idx = list(range(0, len(dates), tick_step))
    ax.set_xticks(idx)
    ax.set_xticklabels([dates[i] for i in idx], rotation=30, fontsize=8)


def mark_ex_dividend_dates(ax, curve_map: dict, events: list,
                           color: str = None, label_prefix: str = "除息日") -> list:
    """在权益曲线上标记除息日（倒三角散点，只标有行情的除息日）

    :param curve_map: {日期: 当日资产}（用于定位散点高度）
    :return: 被标记的除息日列表
    """
    color = color or EQUITY_COLORS["marker"]
    ex_dates = [e["ex_dividend_date"] for e in events if e["ex_dividend_date"] in curve_map]
    if ex_dates:
        ax.scatter(ex_dates, [curve_map[d] for d in ex_dates], marker="v",
                   color=color, s=36, zorder=5, label=f"{label_prefix}({len(ex_dates)})")
    return ex_dates


def draw_year_dividend_bar(ax, events: list,
                           title: str = "年度分红到账金额（元）",
                           empty_text: str = "区间内无分红记录"):
    """按除息日年份汇总到账分红画柱状图（无分红时显示占位文案）"""
    year_cash = {}
    for e in events:
        y = e["ex_dividend_date"][:4]
        year_cash[y] = year_cash.get(y, 0.0) + e["cash_received"]
    if year_cash:
        years = sorted(year_cash)
        values = [year_cash[y] for y in years]
        bars = ax.bar(years, values, color=EQUITY_COLORS["dividend_bar"], alpha=0.85)
        ax.set_title(title)
        ax.set_ylabel("到账金额（元）")
        ax.grid(True, alpha=0.3, axis="y")
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:,.0f}", ha="center", va="bottom", fontsize=8)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
    else:
        ax.text(0.5, 0.5, empty_text, ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="#999")
        ax.set_axis_off()
