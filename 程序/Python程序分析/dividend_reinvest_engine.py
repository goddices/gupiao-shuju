"""
红利再投模拟引擎（纯计算，零第三方依赖）

用不复权价格模拟长期持股 + 分红到账后"无脑买入"该股，回答：
"个股长期红利再投可以赚多少？"

同一轮循环内并行计算三条权益曲线，保证口径一致：
    reinvest    红利再投（分红到账 → 当日收盘价买入）
    no_reinvest 分红不投（分红现金留存）
    price_only  纯股价（忽略分红，仅不复权价格涨跌）

独立脚本(红利再投.py)与 backend 服务共用本引擎。
"""
from datetime import date, timedelta
from typing import Optional


def _to_date(v) -> Optional[date]:
    """字符串/date → date，非法返回 None"""
    if v is None:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def _safe_float(v, default: float = 0.0) -> float:
    """数值安全转换，None/非法返回默认值"""
    if v is None:
        return default
    try:
        f = float(v)
        return f if f == f else default  # 排除 NaN
    except (ValueError, TypeError):
        return default


def _calc_max_drawdown(assets: list) -> float:
    """最大回撤(%)，从资产序列计算"""
    if not assets:
        return 0.0
    peak = assets[0]
    max_dd = 0.0
    for value in assets:
        peak = max(peak, value)
        if peak > 0:
            max_dd = max(max_dd, (peak - value) / peak * 100)
    return round(max_dd, 2)


def _annualize(final: float, initial: float, days: int) -> Optional[float]:
    """按复利年化 (final/initial)^(365/days) - 1，条件不足返回 None"""
    if days <= 0 or initial <= 0 or final <= 0:
        return None
    return round((final / initial) ** (365.0 / days) - 1, 6)


def simulate_dividend_reinvest(
    quotes: list,
    dividends: list,
    initial_cash: float = 100000,
    start_date=None,
    end_date=None,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    lot_size: int = 100,
) -> dict:
    """
    红利再投模拟

    :param quotes: 不复权日线 [{"trade_date": date|str, "close_price": float}]（升序）
    :param dividends: 分红明细 [{"ex_dividend_date": date|str, "cash_per_10": float,
                                  "bonus_per_10": float, "conversion_per_10": float,
                                  "report_date": date|str(可选, 同除息日多条时取最新)}]
    :param initial_cash: 初始资金（元）
    :param start_date: 起始日期（含），None = 数据最早
    :param end_date: 结束日期（含），None = 数据最晚
    :param tax_rate: 分红税率（0~1），长期持有(>1年)免税默认 0
    :param reinvest: True=红利再投；False=分红不投（现金留存）
    :param lot_size: 买入整数倍股数（A股=100）
    :return: {"status", "summary", "dividend_events", "equity_curve", "warnings"}
    """
    start_d = _to_date(start_date)
    end_d = _to_date(end_date)

    # ---------- 1. 行情预处理 ----------
    rows = []
    for q in quotes:
        d = _to_date(q.get("trade_date"))
        close = _safe_float(q.get("close_price"), default=-1.0)
        if d is None or close <= 0:
            continue
        if start_d and d < start_d:
            continue
        if end_d and d > end_d:
            continue
        rows.append({"trade_date": d, "close": close})
    rows.sort(key=lambda r: r["trade_date"])

    if not rows:
        return {"status": "error", "message": "区间内无行情数据（不复权价格缺失），请先同步行情"}

    # ---------- 2. 分红预处理（按除息日索引，同除息日多条取报告期最新） ----------
    div_map = {}
    skipped_ex_dates = []
    for dv in dividends:
        ex_d = _to_date(dv.get("ex_dividend_date"))
        if ex_d is None:
            continue
        if start_d and ex_d < start_d:
            continue
        if end_d and ex_d > end_d:
            continue
        # 同除息日多条（如A/B股）：报告期最新优先
        existing = div_map.get(ex_d)
        if existing is not None:
            cur_rpt = _to_date(dv.get("report_date"))
            old_rpt = _to_date(existing.get("report_date"))
            if old_rpt and (cur_rpt is None or cur_rpt < old_rpt):
                continue
        div_map[ex_d] = {
            "cash_per_10": _safe_float(dv.get("cash_per_10")),
            "bonus_per_10": _safe_float(dv.get("bonus_per_10")),
            "conversion_per_10": _safe_float(dv.get("conversion_per_10")),
            "report_date": dv.get("report_date"),
        }

    trading_dates = {r["trade_date"] for r in rows}
    for ex_d in div_map:
        if ex_d not in trading_dates:
            skipped_ex_dates.append(str(ex_d))

    # ---------- 3. 期初建仓（三条线共享同一笔买入） ----------
    warnings = []
    first_close = rows[0]["close"]
    buy_lots = int(initial_cash / (first_close * lot_size))
    buy_shares = buy_lots * lot_size
    if buy_shares == 0:
        buy_shares = int(initial_cash / first_close)
        if buy_shares > 0:
            warnings.append(
                f"初始资金不足1手(100股)，按零股买入 {buy_shares} 股（实际A股交易需100股整数倍）"
            )
        else:
            return {
                "status": "error",
                "message": f"初始资金 {initial_cash} 元不足以在期初收盘价 {first_close} 买入1股",
            }

    shares_re = buy_shares
    shares_nr = buy_shares
    shares_po = buy_shares
    cash_re = initial_cash - buy_shares * first_close
    cash_nr = cash_re
    cash_po = cash_re

    total_div_re = 0.0
    total_div_nr = 0.0
    total_reinvested = 0.0
    reinvest_count = 0

    # ---------- 4. 主循环：逐交易日 ----------
    equity_curve = []
    dividend_events = []

    for row in rows:
        d = row["trade_date"]
        price = row["close"]
        dv = div_map.get(d)

        if dv is not None:
            # 除息日：先到账（不复权序列中当日收盘价已是除息后价格）
            cash_amt_re = shares_re * (dv["cash_per_10"] / 10.0) * (1.0 - tax_rate)
            cash_amt_nr = shares_nr * (dv["cash_per_10"] / 10.0) * (1.0 - tax_rate)
            shares_before_re = shares_re
            shares_before_nr = shares_nr

            # 送股/转增（每10股口径，向下取整）
            add_re = int(shares_re * dv["bonus_per_10"] / 10.0) + int(
                shares_re * dv["conversion_per_10"] / 10.0
            )
            add_nr = int(shares_nr * dv["bonus_per_10"] / 10.0) + int(
                shares_nr * dv["conversion_per_10"] / 10.0
            )
            shares_re += add_re
            shares_nr += add_nr

            if cash_amt_re > 0 or cash_amt_nr > 0 or add_re > 0:
                total_div_re += cash_amt_re
                total_div_nr += cash_amt_nr
            cash_re += cash_amt_re
            cash_nr += cash_amt_nr

            # 红利再投：用全部可用现金按当日收盘价无脑买入
            reinvest_shares = 0
            reinvest_amount = 0.0
            if reinvest and price > 0 and cash_re >= price * lot_size:
                lots = int(cash_re / (price * lot_size))
                reinvest_shares = lots * lot_size
                reinvest_amount = reinvest_shares * price
                cash_re -= reinvest_amount
                shares_re += reinvest_shares
                total_reinvested += reinvest_amount
                reinvest_count += 1

            dividend_events.append({
                "ex_dividend_date": str(d),
                "report_date": str(dv["report_date"]) if dv.get("report_date") else None,
                "cash_per_10": round(dv["cash_per_10"], 4),
                "bonus_per_10": round(dv["bonus_per_10"], 4),
                "conversion_per_10": round(dv["conversion_per_10"], 4),
                "cash_received": round(cash_amt_re, 2),
                "bonus_shares": add_re,
                "close_price": price,
                "shares_before": shares_before_re,
                "shares_after": shares_re,
                "reinvest_shares": reinvest_shares,
                "reinvest_amount": round(reinvest_amount, 2),
                "cash_after": round(cash_re, 2),
                "asset_after": round(cash_re + shares_re * price, 2),
            })

        equity_curve.append({
            "trade_date": str(d),
            "reinvest_asset": round(cash_re + shares_re * price, 2),
            "no_reinvest_asset": round(cash_nr + shares_nr * price, 2),
            "price_only_asset": round(cash_po + shares_po * price, 2),
        })

    # ---------- 5. 汇总 ----------
    if not dividend_events:
        warnings.append("区间内无分红记录（红利再投曲线与纯股价曲线相同）")
    for ex in skipped_ex_dates:
        warnings.append(f"除息日 {ex} 无行情数据（非交易日或行情缺失），该笔分红未计入")

    last_close = rows[-1]["close"]
    days = (rows[-1]["trade_date"] - rows[0]["trade_date"]).days

    # 三条线的资产序列（分开计算回撤）
    re_assets = [e["reinvest_asset"] for e in equity_curve]
    nr_assets = [e["no_reinvest_asset"] for e in equity_curve]
    po_assets = [e["price_only_asset"] for e in equity_curve]

    def _build_line(assets, final_shares, final_cash, total_div=0.0, total_reinv=None, reinv_cnt=0):
        final_asset = round(assets[-1], 2)
        return {
            "final_asset": final_asset,
            "total_return_pct": round((final_asset - initial_cash) / initial_cash * 100, 2),
            "annual_return_pct": _annualize(final_asset, initial_cash, days),
            "max_drawdown_pct": _calc_max_drawdown(assets),
            "final_shares": final_shares,
            "final_cash": round(final_cash, 2),
            "total_dividends": round(total_div, 2),
            **({"total_reinvested": round(total_reinv, 2), "reinvest_count": reinv_cnt}
               if total_reinv is not None else {}),
        }

    summary = {
        "start_date": str(rows[0]["trade_date"]),
        "end_date": str(rows[-1]["trade_date"]),
        "trading_days": len(rows),
        "first_close": first_close,
        "last_close": last_close,
        "period_return_pct": round((last_close - first_close) / first_close * 100, 2),
        "dividend_count": len(dividend_events),
        "reinvest": _build_line(re_assets, shares_re, cash_re,
                                total_div_re, total_reinvested, reinvest_count),
        "no_reinvest": _build_line(nr_assets, shares_nr, cash_nr, total_div_nr),
        "price_only": _build_line(po_assets, shares_po, cash_po),
    }

    return {
        "status": "ok",
        "summary": summary,
        "dividend_events": dividend_events,
        "equity_curve": equity_curve,
        "warnings": warnings,
    }


def plan_dividend_target(
    quotes: list,
    dividends: list,
    buy_date,
    target_annual_dividend: float,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    reference: str = "last_year",
    lot_size: int = 100,
) -> dict:
    """
    分红目标测算：要达到目标年分红（如 20 万/年），需要在买入日投入多少钱？

    :param quotes: 不复权日线 [{"trade_date", "close_price"}]（升序）
    :param dividends: 分红明细 [{"ex_dividend_date", "cash_per_10", "bonus_per_10",
                                  "conversion_per_10", "report_date"}]
    :param buy_date: 买入日期（非交易日则顺延到下一交易日收盘价买入）
    :param target_annual_dividend: 目标每年分红到账金额（元）
    :param tax_rate: 分红税率（0~1）
    :param reinvest: True=红利再投（分红买入更多股，期初可以少买）；False=分红不投
    :param reference: 每股年分红基准 — "last_year"=去年全年(除息日在上一个日历年)；
                      "trailing"=最近12个月
    :param lot_size: A股买入整数倍（100）
    :return: {"status", "summary"}，summary 含 reinvest/no_reinvest 两套方案与差额
    """
    # ---------- 1. 行情预处理 ----------
    rows = []
    for q in quotes:
        d = _to_date(q.get("trade_date"))
        close = _safe_float(q.get("close_price"), default=-1.0)
        if d is None or close <= 0:
            continue
        rows.append({"trade_date": d, "close": close})
    rows.sort(key=lambda r: r["trade_date"])
    if not rows:
        return {"status": "error", "message": "无行情数据，请先同步行情"}

    now_d = rows[-1]["trade_date"]

    # ---------- 2. 买入日定位（非交易日顺延到下一交易日） ----------
    buy_d = _to_date(buy_date)
    if buy_d is None:
        return {"status": "error", "message": f"买入日期 {buy_date} 无效"}
    buy_rows = [r for r in rows if r["trade_date"] >= buy_d]
    if not buy_rows:
        return {"status": "error", "message": f"买入日期 {buy_date} 晚于最新行情 {now_d}"}
    buy_row = buy_rows[0]
    buy_trade_date = buy_row["trade_date"]
    buy_price = buy_row["close"]

    # ---------- 3. 每股年分红基准 ----------
    ref_divs = []
    for dv in dividends:
        ex_d = _to_date(dv.get("ex_dividend_date"))
        if ex_d is None:
            continue
        if reference == "trailing":
            start_d = now_d - timedelta(days=365)
            if start_d < ex_d <= now_d:
                ref_divs.append({"ex_dividend_date": str(ex_d), "report_date": dv.get("report_date"),
                                 "cash_per_10": _safe_float(dv.get("cash_per_10"))})
        else:  # last_year
            if ex_d.year == now_d.year - 1:
                ref_divs.append({"ex_dividend_date": str(ex_d), "report_date": dv.get("report_date"),
                                 "cash_per_10": _safe_float(dv.get("cash_per_10"))})

    # 去年全年无分红 → 回退最近12个月
    reference_used = reference
    if sum(d["cash_per_10"] for d in ref_divs) <= 0 and reference != "trailing":
        reference_used = "trailing"
        ref_divs = []
        start_d = now_d - timedelta(days=365)
        for dv in dividends:
            ex_d = _to_date(dv.get("ex_dividend_date"))
            if ex_d is None:
                continue
            if start_d < ex_d <= now_d:
                ref_divs.append({"ex_dividend_date": str(ex_d), "report_date": dv.get("report_date"),
                                 "cash_per_10": _safe_float(dv.get("cash_per_10"))})

    d_per_share = sum(d["cash_per_10"] for d in ref_divs) / 10.0
    if d_per_share <= 0:
        return {"status": "error", "message": "参考期内无分红记录，无法测算"}

    if target_annual_dividend <= 0:
        return {"status": "error", "message": f"目标年分红 {target_annual_dividend} 无效，必须大于 0"}

    d_net = d_per_share * (1.0 - tax_rate)  # 税后每股年分红
    target_shares = int(-(-target_annual_dividend // (d_net * lot_size))) * lot_size  # 向上取整到整手

    if reference_used == "last_year":
        ref_label = f"去年全年({now_d.year - 1})"
    else:
        ref_label = f"最近12个月({str(now_d - timedelta(days=365))}~{str(now_d)})"

    # ---------- 4. 买入后的分红（除息日严格晚于买入交易日，当天买入不享受当天除息） ----------
    sim_dividends = []
    for dv in dividends:
        ex_d = _to_date(dv.get("ex_dividend_date"))
        if ex_d is None or ex_d <= buy_trade_date:
            continue
        sim_dividends.append({
            "ex_dividend_date": dv.get("ex_dividend_date"),
            "report_date": dv.get("report_date"),
            "cash_per_10": _safe_float(dv.get("cash_per_10")),
            "bonus_per_10": _safe_float(dv.get("bonus_per_10")),
            "conversion_per_10": _safe_float(dv.get("conversion_per_10")),
        })
    sim_quotes = [{"trade_date": r["trade_date"], "close_price": r["close"]}
                  for r in rows if r["trade_date"] >= buy_trade_date]

    # ---------- 5. 分红不投方案：目标股数 × 买入价 ----------
    no_reinvest = {
        "required_shares": target_shares,
        "required_amount": round(target_shares * buy_price, 2),
        "actual_annual_dividend": round(target_shares * d_net, 2),
    }

    # ---------- 6. 红利再投方案：按"手数"二分搜索最少期初持股 ----------
    # 每次用精确资金(手数×买入价，无零钱)模拟，避免零钱边界影响结果
    reinvest_plan = None
    saving_amount = None
    saving_pct = None
    if reinvest:
        def _final_shares(shares: int) -> int:
            res = simulate_dividend_reinvest(
                quotes=sim_quotes,
                dividends=sim_dividends,
                initial_cash=shares * buy_price,
                tax_rate=tax_rate,
                reinvest=True,
                lot_size=lot_size,
            )
            if res["status"] != "ok":
                return 0
            return res["summary"]["reinvest"]["final_shares"]

        # 上界校验：目标股数满仓必能达标
        if _final_shares(target_shares) < target_shares:
            return {"status": "error", "message": "按目标股数全仓买入仍无法达标（数据异常）"}

        low_lots, high_lots = 1, target_shares // lot_size
        while low_lots < high_lots:
            mid_lots = (low_lots + high_lots) // 2
            if _final_shares(mid_lots * lot_size) >= target_shares:
                high_lots = mid_lots
            else:
                low_lots = mid_lots + 1

        required_shares = low_lots * lot_size
        required_amount = round(required_shares * buy_price, 2)

        # 用确定的手数跑一遍，取最终口径
        res = simulate_dividend_reinvest(
            quotes=sim_quotes, dividends=sim_dividends,
            initial_cash=required_amount, tax_rate=tax_rate,
            reinvest=True, lot_size=lot_size,
        )
        line = res["summary"]["reinvest"]
        reinvest_plan = {
            "required_shares": required_shares,
            "required_amount": required_amount,
            "final_shares": line["final_shares"],
            "actual_annual_dividend": round(line["final_shares"] * d_net, 2),
            "total_dividends_received": line["total_dividends"],
            "reinvest_count": line["reinvest_count"],
            "total_reinvested": line["total_reinvested"],
            "warnings": res["warnings"],
        }
        saving_amount = round(no_reinvest["required_amount"] - required_amount, 2)
        saving_pct = round(saving_amount / no_reinvest["required_amount"] * 100, 2)

    return {
        "status": "ok",
        "summary": {
            "buy_date": str(buy_d),
            "actual_buy_date": str(buy_trade_date),
            "buy_price": round(buy_price, 4),
            "now_date": str(now_d),
            "reference": {
                "type": reference_used,
                "label": ref_label,
                "d_per_share": round(d_per_share, 6),
                "d_net_per_share": round(d_net, 6),
                "dividend_count": len(ref_divs),
                "dividends": ref_divs,
            },
            "target_annual_dividend": target_annual_dividend,
            "target_shares": target_shares,
            "tax_rate": tax_rate,
            "reinvest": reinvest_plan,
            "no_reinvest": no_reinvest,
            "saving_amount": saving_amount,
            "saving_pct": saving_pct,
        },
    }


def simulate_dip_buy(
    quotes: list,
    dividends: list,
    dip_pct: float,
    buy_amount: float,
    start_date=None,
    end_date=None,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    lot_size: int = 100,
    trigger_quotes: list = None,
) -> dict:
    """
    红利再投增强版：大跌买入 + 红利再投

    观察期内股价从（滚动）历史最高点首次回撤 ≥ dip_pct% 时，按当日收盘价买入
    buy_amount 元，之后按红利再投策略持有至期末，输出三策略收益对比。

    :param quotes: 不复权日线 [{"trade_date", "close_price"}]（升序），用于买入与模拟
    :param dividends: 分红明细（同 simulate_dividend_reinvest）
    :param dip_pct: 触发买入的回撤幅度（%），如 20 表示从高点跌 20% 买入
    :param buy_amount: 买入金额（元）
    :param start_date/end_date: 观察区间（默认数据首尾）
    :param tax_rate: 分红税率
    :param reinvest: True=红利再投；False=分红不投
    :param lot_size: 买入整数倍（A股=100）
    :param trigger_quotes: 回撤检测所用价格序列（建议前复权，避免送转除权造成假跌破；
                           缺省用不复权 quotes 自身）
    :return: {"status", "trigger", "summary", "dividend_events", "equity_curve", "warnings"}
    """
    start_d = _to_date(start_date)
    end_d = _to_date(end_date)

    # ---------- 1. 行情预处理 ----------
    rows = []
    for q in quotes:
        d = _to_date(q.get("trade_date"))
        close = _safe_float(q.get("close_price"), default=-1.0)
        if d is None or close <= 0:
            continue
        if start_d and d < start_d:
            continue
        if end_d and d > end_d:
            continue
        rows.append({"trade_date": d, "close": close})
    rows.sort(key=lambda r: r["trade_date"])
    if len(rows) < 2:
        return {"status": "error", "message": "观察区间内行情不足（至少2个交易日）"}

    # 回撤检测价格序列（前复权优先）
    trig_map = {}
    if trigger_quotes:
        for q in trigger_quotes:
            d = _to_date(q.get("trade_date"))
            p = _safe_float(q.get("close_price"), default=-1.0)
            if d is not None and p > 0:
                trig_map[d] = p
    series_label = "前复权" if trig_map else "不复权"

    if dip_pct < 0:
        return {"status": "error", "message": f"回撤幅度 {dip_pct}% 无效，必须 ≥ 0"}
    if buy_amount <= 0:
        return {"status": "error", "message": f"买入金额 {buy_amount} 元无效，必须大于 0"}

    # ---------- 2. 首次回撤触发 ----------
    peak_price = None
    peak_date = None
    buy_row = None
    max_dd = 0.0
    for r in rows:
        p = trig_map.get(r["trade_date"], r["close"])
        if peak_price is None or p > peak_price:
            peak_price = p
            peak_date = r["trade_date"]
        if peak_price > 0:
            dd = (peak_price - p) / peak_price * 100
            max_dd = max(max_dd, dd)
        if p <= peak_price * (1.0 - dip_pct / 100.0):
            buy_row = r
            break

    if buy_row is None:
        return {
            "status": "error",
            "message": f"观察区间内从未出现回撤 ≥{dip_pct:.1f}% 的买点（期间最大回撤 {max_dd:.1f}%）",
        }

    buy_date = buy_row["trade_date"]
    buy_price = buy_row["close"]  # 实际买入用不复权收盘价
    buy_trigger_price = trig_map.get(buy_date, buy_price)
    actual_dip_pct = round((peak_price - buy_trigger_price) / peak_price * 100, 2)

    # ---------- 3. 买入后红利再投模拟 ----------
    sim_quotes = [
        {"trade_date": r["trade_date"], "close_price": r["close"]}
        for r in rows if r["trade_date"] >= buy_date
    ]
    sim_dividends = []
    for dv in dividends:
        ex_d = _to_date(dv.get("ex_dividend_date"))
        if ex_d is None or ex_d <= buy_date:
            continue  # 买入日当天除息不享受，且买入价已是除息后价格
        sim_dividends.append({
            "ex_dividend_date": dv.get("ex_dividend_date"),
            "report_date": dv.get("report_date"),
            "cash_per_10": _safe_float(dv.get("cash_per_10")),
            "bonus_per_10": _safe_float(dv.get("bonus_per_10")),
            "conversion_per_10": _safe_float(dv.get("conversion_per_10")),
        })

    res = simulate_dividend_reinvest(
        quotes=sim_quotes,
        dividends=sim_dividends,
        initial_cash=buy_amount,
        tax_rate=tax_rate,
        reinvest=reinvest,
        lot_size=lot_size,
    )
    if res["status"] != "ok":
        return res

    # 实际买入股数（整手；不足一手则零股买入，与引擎口径一致）
    buy_lots = int(buy_amount / (buy_price * lot_size))
    initial_shares = buy_lots * lot_size
    if initial_shares == 0:
        initial_shares = int(buy_amount / buy_price)

    return {
        "status": "ok",
        "trigger": {
            "dip_pct": dip_pct,
            "buy_amount": buy_amount,
            "buy_date": str(buy_date),
            "buy_price": round(buy_price, 4),
            "buy_trigger_price": round(buy_trigger_price, 4),
            "peak_date": str(peak_date),
            "peak_price": round(peak_price, 4),
            "actual_dip_pct": actual_dip_pct,
            "trigger_series": series_label,
            "initial_shares": initial_shares,
        },
        "summary": res["summary"],
        "dividend_events": res["dividend_events"],
        "equity_curve": res["equity_curve"],
        "warnings": res["warnings"],
    }


def simulate_staged_dip_buy(
    quotes: list,
    dividends: list,
    total_position: float,
    buy_ratio: float = 5.0,
    dip_pct: float = 3.0,
    start_date=None,
    end_date=None,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    lot_size: int = 100,
) -> dict:
    """
    大跌分批买入 + 红利再投（当日跌幅触发）

    策略：每个交易日若盘中最低价较前收盘跌幅 ≥ dip_pct%（当天大跌），
    按当日最低价买入一笔，金额 = 总仓位 × buy_ratio%（每次触发买一笔，
    直至现金用完），此后分红到账"无脑买入"该股（红利再投）。

    对比线（同一循环内并行计算，口径一致）：
        staged_reinvest   分批买入 + 红利再投（本策略）
        lump_reinvest     首个触发日一次性全仓买入 + 红利再投
        lump_no_reinvest  首个触发日一次性全仓买入 + 分红不投

    :param quotes: 不复权日线 [{"trade_date", "low_price", "close_price"}]（升序）
    :param dividends: 分红明细（同 simulate_dividend_reinvest）
    :param total_position: 总仓位资金（元）
    :param buy_ratio: 每笔买入占总仓位比例（%），默认 5
    :param dip_pct: 当日大跌阈值（%），默认 3（最低价 ≤ 前收盘 × (1-dip%) 触发）
    :param start_date/end_date: 观察区间（默认数据首尾）
    :param tax_rate: 分红税率
    :param reinvest: True=红利再投；False=分红不投
    :param lot_size: 买入整数倍（A股=100）
    :return: {"status", "params", "triggers", "summary", "dividend_events",
              "equity_curve", "warnings"}
    """
    start_d = _to_date(start_date)
    end_d = _to_date(end_date)

    # ---------- 1. 行情预处理 ----------
    rows = []
    for q in quotes:
        d = _to_date(q.get("trade_date"))
        close = _safe_float(q.get("close_price"), default=-1.0)
        if d is None or close <= 0:
            continue
        if start_d and d < start_d:
            continue
        if end_d and d > end_d:
            continue
        low = _safe_float(q.get("low_price"), default=-1.0)
        if low <= 0:
            low = close  # 缺最低价时回退收盘价
        rows.append({"trade_date": d, "low": low, "close": close})
    rows.sort(key=lambda r: r["trade_date"])
    if len(rows) < 2:
        return {"status": "error", "message": "观察区间内行情不足（至少2个交易日）"}
    if total_position <= 0:
        return {"status": "error", "message": f"总仓位 {total_position} 元无效，必须大于 0"}
    if buy_ratio <= 0 or buy_ratio > 100:
        return {"status": "error", "message": f"每笔比例 {buy_ratio}% 无效，必须在 (0, 100] 区间"}
    if dip_pct < 0:
        return {"status": "error", "message": f"当日跌幅阈值 {dip_pct}% 无效，必须 ≥ 0"}

    # ---------- 2. 触发日扫描（最低价较前收盘跌幅 ≥ dip_pct%） ----------
    triggers = []  # [{trade_date, prev_close, low, drop_pct}]
    max_daily_dd = 0.0
    prev_close = None
    for r in rows:
        if prev_close is not None and prev_close > 0:
            dd = (prev_close - r["low"]) / prev_close * 100
            if dd >= dip_pct:
                triggers.append({
                    "trade_date": r["trade_date"],
                    "prev_close": prev_close,
                    "low": r["low"],
                    "drop_pct": round(dd, 2),
                })
            max_daily_dd = max(max_daily_dd, dd)
        prev_close = r["close"]

    if not triggers:
        return {
            "status": "error",
            "message": f"观察区间内从未出现单日跌幅 ≥{dip_pct:.1f}% 的交易日"
                       f"（期间最大单日跌幅 {max_daily_dd:.2f}%）",
        }

    first_trigger_date = triggers[0]["trade_date"]
    trig_set = {t["trade_date"] for t in triggers}

    # ---------- 3. 分红预处理（买入日之后才有持仓，除息日 ≤ 首触日的不参与） ----------
    div_map = {}
    for dv in dividends:
        ex_d = _to_date(dv.get("ex_dividend_date"))
        if ex_d is None or ex_d <= first_trigger_date:
            continue
        if end_d and ex_d > end_d:
            continue
        existing = div_map.get(ex_d)
        if existing is not None:
            cur_rpt = _to_date(dv.get("report_date"))
            old_rpt = _to_date(existing.get("report_date"))
            if old_rpt is not None and (cur_rpt is None or cur_rpt <= old_rpt):
                continue
        div_map[ex_d] = {
            "cash_per_10": _safe_float(dv.get("cash_per_10")),
            "bonus_per_10": _safe_float(dv.get("bonus_per_10")),
            "conversion_per_10": _safe_float(dv.get("conversion_per_10")),
            "report_date": dv.get("report_date"),
        }

    # ---------- 4. 逐日模拟（三线并行） ----------
    sim_rows = [r for r in rows if r["trade_date"] >= first_trigger_date]

    cash_st = total_position
    shares_st = 0
    cash_lr = total_position
    shares_lr = 0
    cash_ln = total_position
    shares_ln = 0

    tranche = total_position * buy_ratio / 100.0
    buy_log = []  # A线每笔买入明细
    total_div_st = 0.0
    total_reinvested = 0.0
    reinvest_count = 0
    total_div_lr = 0.0
    total_div_ln = 0.0
    dividend_events = []
    equity_curve = []
    warnings = []
    cash_exhausted = False
    tranche_too_small_hint = False

    for r in sim_rows:
        d = r["trade_date"]
        low, close = r["low"], r["close"]

        # a) 除息日：三线各自结算分红（A/B 再投，C 不投），除息日买入不享有当日分红
        dv = div_map.get(d)
        if dv is not None and close > 0:
            cash_per_share = dv["cash_per_10"] / 10.0 * (1.0 - tax_rate)
            bonus_ratio = (dv["bonus_per_10"] + dv["conversion_per_10"]) / 10.0

            for tag in ("A", "B", "C"):
                if tag == "A":
                    shares, cash = shares_st, cash_st
                elif tag == "B":
                    shares, cash = shares_lr, cash_lr
                else:
                    shares, cash = shares_ln, cash_ln
                if shares <= 0:
                    continue
                cash_amt = shares * cash_per_share
                add_shares = int(shares * bonus_ratio) if bonus_ratio > 0 else 0
                cash += cash_amt
                shares += add_shares
                reinv_shares, reinv_amount = 0, 0.0
                do_reinvest = (tag in ("A", "B") and reinvest)
                if do_reinvest and cash >= close * lot_size:
                    lots = int(cash / (close * lot_size))
                    reinv_shares = lots * lot_size
                    reinv_amount = reinv_shares * close
                    cash -= reinv_amount
                    shares += reinv_shares
                if tag == "A":
                    shares_st, cash_st = shares, cash
                    total_div_st += cash_amt
                    total_reinvested += reinv_amount
                    if reinv_shares > 0:
                        reinvest_count += 1
                    dividend_events.append({
                        "ex_dividend_date": str(d),
                        "report_date": str(dv["report_date"]) if dv.get("report_date") else None,
                        "cash_per_10": round(dv["cash_per_10"], 4),
                        "bonus_per_10": round(dv["bonus_per_10"], 4),
                        "conversion_per_10": round(dv["conversion_per_10"], 4),
                        "cash_received": round(cash_amt, 2),
                        "bonus_shares": add_shares,
                        "close_price": close,
                        "reinvest_shares": reinv_shares,
                        "reinvest_amount": round(reinv_amount, 2),
                    })
                elif tag == "B":
                    shares_lr, cash_lr = shares, cash
                    total_div_lr += cash_amt
                else:
                    shares_ln, cash_ln = shares, cash
                    total_div_ln += cash_amt

        # b) 触发日买入：A 线每笔 tranche；B/C 线首触日全仓（均按当日最低价成交）
        if d in trig_set:
            if not cash_exhausted:
                available = min(tranche, cash_st)
                lots = int(available / (low * lot_size))
                if lots > 0:
                    spend = lots * lot_size * low
                    cash_st -= spend
                    shares_st += lots * lot_size
                    buy_log.append({
                        "buy_date": str(d),
                        "buy_price": round(low, 4),
                        "buy_amount": round(spend, 2),
                        "buy_shares": lots * lot_size,
                    })
                elif cash_st < low * lot_size:
                    cash_exhausted = True
                    warnings.append(
                        f"{d} 起剩余现金 {cash_st:,.2f} 元不足一手，后续触发日未再买入")
                elif not tranche_too_small_hint:
                    tranche_too_small_hint = True
                    warnings.append(
                        f"每笔金额 {tranche:,.0f} 元不足一手（约 {low * lot_size:,.0f} 元），"
                        f"触发日无法买入，请调大 --ratio 或总仓位")

        if d == first_trigger_date:
            lots = int(cash_lr / (low * lot_size))
            spend = lots * lot_size * low
            cash_lr -= spend
            shares_lr += lots * lot_size
            lots = int(cash_ln / (low * lot_size))
            spend = lots * lot_size * low
            cash_ln -= spend
            shares_ln += lots * lot_size

        # c) 每日权益曲线（按收盘价计市值）
        equity_curve.append({
            "trade_date": str(d),
            "staged_asset": round(cash_st + shares_st * close, 2),
            "lump_re_asset": round(cash_lr + shares_lr * close, 2),
            "lump_nr_asset": round(cash_ln + shares_ln * close, 2),
        })

    # 回填买入明细的前收盘与跌幅
    trig_info = {str(t["trade_date"]): t for t in triggers}
    for b in buy_log:
        t = trig_info.get(b["buy_date"])
        b["prev_close"] = t["prev_close"] if t else None
        b["drop_pct"] = t["drop_pct"] if t else None

    if not dividend_events:
        warnings.append("买入后无分红记录（红利再投曲线与分红不投曲线相同）")

    # ---------- 5. 汇总 ----------
    last_close = sim_rows[-1]["close"]
    first_close = sim_rows[0]["close"]
    days = (sim_rows[-1]["trade_date"] - sim_rows[0]["trade_date"]).days

    def _build_line(assets, final_shares, final_cash, total_div=0.0, total_reinv=None, reinv_cnt=0):
        final_asset = round(assets[-1], 2)
        return {
            "final_asset": final_asset,
            "total_return_pct": round((final_asset - total_position) / total_position * 100, 2),
            "annual_return_pct": _annualize(final_asset, total_position, days),
            "max_drawdown_pct": _calc_max_drawdown(assets),
            "final_shares": final_shares,
            "final_cash": round(final_cash, 2),
            "total_dividends": round(total_div, 2),
            **({"total_reinvested": round(total_reinv, 2), "reinvest_count": reinv_cnt}
               if total_reinv is not None else {}),
        }

    st_assets = [e["staged_asset"] for e in equity_curve]
    lr_assets = [e["lump_re_asset"] for e in equity_curve]
    ln_assets = [e["lump_nr_asset"] for e in equity_curve]

    total_invested = sum(b["buy_amount"] for b in buy_log)

    summary = {
        "start_date": str(sim_rows[0]["trade_date"]),
        "end_date": str(sim_rows[-1]["trade_date"]),
        "trading_days": len(sim_rows),
        "first_close": first_close,
        "last_close": last_close,
        "period_return_pct": round((last_close - first_close) / first_close * 100, 2),
        "trigger_count": len(buy_log),
        "total_invested": round(total_invested, 2),
        "leftover_cash": round(cash_st, 2),
        "tranche": round(tranche, 2),
        "dividend_count": len(dividend_events),
        "staged_reinvest": _build_line(st_assets, shares_st, cash_st,
                                       total_div_st, total_reinvested, reinvest_count),
        "lump_reinvest": _build_line(lr_assets, shares_lr, cash_lr, total_div_lr),
        "lump_no_reinvest": _build_line(ln_assets, shares_ln, cash_ln, total_div_ln),
    }

    return {
        "status": "ok",
        "params": {
            "total_position": total_position,
            "buy_ratio": buy_ratio,
            "dip_pct": dip_pct,
            "first_trigger_date": str(first_trigger_date),
        },
        "triggers": buy_log,
        "summary": summary,
        "dividend_events": dividend_events,
        "equity_curve": equity_curve,
        "warnings": warnings,
    }


def simulate_baseline_only(
    quotes: list,
    initial_cash: float = 100000,
    start_date=None,
    end_date=None,
    lot_size: int = 100,
) -> dict:
    """快捷入口：仅计算"分红不投"基准（分红数据缺失时的降级路径）"""
    return simulate_dividend_reinvest(
        quotes, [], initial_cash, start_date, end_date,
        tax_rate=0.0, reinvest=False, lot_size=lot_size,
    )
