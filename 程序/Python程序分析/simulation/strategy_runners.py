# -*- coding: utf-8 -*-
"""strategy_runners —— 红利再投 / 大跌买入 / 分红目标测算的统一装配层

合并原 backend 三个薄 service（dip_buy_service / dividend_reinvest_service /
dividend_target_service），并承接 analysis/tools 下 4 个 CLI 工具（红利再投 /
红利再投增强版 / 大跌分批买入 / 分红目标测算）的「DB 取数 → 引擎调用」段。

双路径契约（由 log 参数区分，两侧行为均与旧版逐字节一致）：
    log=None  web 路径：逐字复刻原三个 service——run_dip_buy 先取分红再按策略取
              行情、total_position 保留 falsy 兜底（0/None → 1000000.0）、空行情
              照常交给引擎报错、不调 ensure_dividends；plan_target 恒不传
              forward_quotes（web 口径）。
    log≠None  CLI 路径：逐字复刻原 4 个工具的日志文案——「共 N 个交易日」、前复权
              ok/miss 文案按 strategy 分支、分红明细行；total_position 原样透传
              （旧工具无 falsy 兜底）；空行情打日志后返回
              {"status": "no_data", "message": ...}（调用方不得再打失败日志）。

本模块无 sys.path 副作用代码——根目录与 backend 目录的注入由 simulation/__init__ 保证。
"""
from sqlalchemy.orm import Session

from analysis.data_access import (
    load_quotes, load_forward_quotes, load_dividends, ensure_dividends,
)
from simulation.dividend_reinvest_engine import (
    simulate_dividend_reinvest, simulate_dip_buy,
    simulate_staged_dip_buy, plan_dividend_target,
)


def _no_data_msg(stock_code: str) -> str:
    return (f"数据库中没有 {stock_code} 的行情数据，请先同步行情"
            f"（导入数据功能或 /api/stocks/{stock_code}/fetch）")


def _load_quotes(db, stock_code: str, log, with_low: bool = False):
    """CLI 路径取不复权行情；空行情时打日志并返回 None"""
    quotes = load_quotes(db, stock_code, with_low=with_low)
    if log is not None and not quotes:
        log(_no_data_msg(stock_code))
        return None
    return quotes


def _load_forward(db, stock_code: str, n_expected: int, log,
                  ok_msg: str = None, miss_msg: str = None):
    """取前复权行情；log 非 None 且 ok_msg 非 None 时按结果打 ok/miss 文案"""
    forward_quotes = load_forward_quotes(db, stock_code, n_expected)
    if log is not None and ok_msg is not None:
        log(ok_msg if forward_quotes else miss_msg)
    return forward_quotes


def _load_dividends(db, stock_code: str, sync: bool, log):
    """CLI 路径走 ensure_dividends（带日志），web 路径走 load_dividends（静默）"""
    if log is not None:
        dividends = ensure_dividends(db, stock_code, sync, log)
        log(f"分红明细: {len(dividends)} 笔（仅统计已实施分配）")
        return dividends
    return load_dividends(db, stock_code)


def run_dividend_reinvest(
    db: Session,
    stock_code: str,
    start_date=None,
    end_date=None,
    initial_cash: float = 100000,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    lot_size: int = 100,
    sync: bool = False,
    log=None,
) -> dict:
    """
    红利再投模拟（web 与 CLI 共用装配）

    :param db: 数据库会话
    :param stock_code: 股票代码
    :param start_date/end_date: 观察区间（可选）
    :param initial_cash: 初始资金
    :param tax_rate: 分红税率（0~1）
    :param reinvest: True=红利再投；False=分红不投
    :param lot_size: 买入整数倍股数（A股=100）
    :param sync: CLI 路径分红缺失时是否同步（web 路径忽略）
    :param log: None=web 路径（原样返回引擎 dict）；可调用对象=CLI 路径（打日志）
    :return: 引擎原始结果 dict（status/summary/dividend_events/equity_curve/warnings）
    """
    if log is None:
        # web 路径：与旧 dividend_reinvest_service 逐行等价
        quotes = load_quotes(db, stock_code)
        forward_quotes = load_forward_quotes(db, stock_code, len(quotes))
        dividends = load_dividends(db, stock_code)
        return simulate_dividend_reinvest(
            quotes=quotes,
            dividends=dividends,
            initial_cash=initial_cash,
            start_date=start_date,
            end_date=end_date,
            tax_rate=tax_rate,
            reinvest=reinvest,
            lot_size=lot_size,
            forward_quotes=forward_quotes,
        )

    # CLI 路径：与 红利再投.py 原 run() 取数段逐行等价
    quotes = _load_quotes(db, stock_code, log)
    if quotes is None:
        return {"status": "no_data", "message": _no_data_msg(stock_code)}
    log(f"共 {len(quotes)} 个交易日（{quotes[0]['trade_date']} ~ {quotes[-1]['trade_date']}）")
    forward_quotes = _load_forward(
        db, stock_code, len(quotes), log,
        ok_msg="已加载前复权行情（成本前复权口径可用）",
        miss_msg="前复权数据缺失，成本前复权口径不可用（请先同步前复权行情）",
    )
    dividends = _load_dividends(db, stock_code, sync, log)
    return simulate_dividend_reinvest(
        quotes=quotes,
        dividends=dividends,
        initial_cash=initial_cash,
        start_date=start_date,
        end_date=end_date,
        tax_rate=tax_rate,
        reinvest=reinvest,
        lot_size=lot_size,
        forward_quotes=forward_quotes,
    )


def run_dip_buy(
    db: Session,
    stock_code: str,
    dip_pct: float,
    buy_amount: float,
    start_date=None,
    end_date=None,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    lot_size: int = 100,
    strategy: str = "drawdown",
    total_position: float = None,
    buy_ratio: float = 5.0,
    sync: bool = False,
    log=None,
) -> dict:
    """
    大跌买入 + 红利再投模拟（web 与 CLI 共用装配）

    :param db: 数据库会话
    :param stock_code: 股票代码
    :param dip_pct: drawdown=回撤买入幅度（%）；daily_drop=当日盘中跌幅阈值（%）
    :param buy_amount: drawdown 模式买入金额（元）
    :param start_date/end_date: 观察区间（可选）
    :param tax_rate: 分红税率（0~1）
    :param reinvest: True=红利再投；False=分红不投
    :param lot_size: 买入整数倍股数（A股=100）
    :param strategy: "drawdown" | "daily_drop"
    :param total_position: daily_drop 模式总仓位（元）
    :param buy_ratio: daily_drop 模式每笔买入占总仓位比例（%）
    :param sync: CLI 路径分红缺失时是否同步（web 路径忽略）
    :param log: None=web 路径（原样返回引擎 dict）；可调用对象=CLI 路径（打日志）
    :return: 引擎原始结果 dict
    """
    if log is None:
        # web 路径：与旧 dip_buy_service 逐行等价（先取分红，再按策略取行情；
        # total_position 保留 falsy 兜底：0/None → 1000000.0）
        dividends = load_dividends(db, stock_code)
        if strategy == "daily_drop":
            quotes = load_quotes(db, stock_code, with_low=True)
            forward_quotes = load_forward_quotes(db, stock_code, len(quotes))
            return simulate_staged_dip_buy(
                quotes=quotes,
                dividends=dividends,
                total_position=total_position if total_position else 1000000.0,
                buy_ratio=buy_ratio,
                dip_pct=dip_pct,
                start_date=start_date,
                end_date=end_date,
                tax_rate=tax_rate,
                reinvest=reinvest,
                lot_size=lot_size,
                forward_quotes=forward_quotes,
            )
        quotes = load_quotes(db, stock_code)
        forward_quotes = load_forward_quotes(db, stock_code, len(quotes))
        return simulate_dip_buy(
            quotes=quotes,
            dividends=dividends,
            dip_pct=dip_pct,
            buy_amount=buy_amount,
            start_date=start_date,
            end_date=end_date,
            tax_rate=tax_rate,
            reinvest=reinvest,
            lot_size=lot_size,
            trigger_quotes=forward_quotes,
        )

    # CLI 路径：与 大跌分批买入.py（daily_drop）/ 红利再投增强版.py（drawdown）
    # 原 run() 取数段逐行等价；total_position 原样透传（旧工具无 falsy 兜底）
    quotes = _load_quotes(db, stock_code, log, with_low=(strategy == "daily_drop"))
    if quotes is None:
        return {"status": "no_data", "message": _no_data_msg(stock_code)}
    log(f"共 {len(quotes)} 个交易日（{quotes[0]['trade_date']} ~ {quotes[-1]['trade_date']}）")
    if strategy == "daily_drop":
        forward_quotes = _load_forward(
            db, stock_code, len(quotes), log,
            ok_msg="已加载前复权行情（成本前复权口径可用）",
            miss_msg="前复权数据缺失，成本前复权口径不可用（请先同步前复权行情）",
        )
        dividends = _load_dividends(db, stock_code, sync, log)
        return simulate_staged_dip_buy(
            quotes=quotes,
            dividends=dividends,
            total_position=total_position,
            buy_ratio=buy_ratio,
            dip_pct=dip_pct,
            start_date=start_date,
            end_date=end_date,
            tax_rate=tax_rate,
            reinvest=reinvest,
            lot_size=lot_size,
            forward_quotes=forward_quotes,
        )
    forward_quotes = _load_forward(
        db, stock_code, len(quotes), log,
        ok_msg="回撤检测使用前复权价格（避免送转除权造成假跌破）",
        miss_msg="前复权数据缺失，回撤检测回退为不复权价格",
    )
    dividends = _load_dividends(db, stock_code, sync, log)
    return simulate_dip_buy(
        quotes=quotes,
        dividends=dividends,
        dip_pct=dip_pct,
        buy_amount=buy_amount,
        start_date=start_date,
        end_date=end_date,
        tax_rate=tax_rate,
        reinvest=reinvest,
        lot_size=lot_size,
        trigger_quotes=forward_quotes,
    )


def plan_target(
    db: Session,
    stock_code: str,
    buy_date,
    target_annual_dividend: float,
    tax_rate: float = 0.0,
    reinvest: bool = True,
    reference: str = "last_year",
    lot_size: int = 100,
    forward_quotes=None,
    sync: bool = False,
    log=None,
) -> dict:
    """
    分红目标测算：目标每年分红到账 X 元，需要在买入日投入多少钱？（web 与 CLI 共用装配）

    :param db: 数据库会话
    :param stock_code: 股票代码
    :param buy_date: 买入日期（非交易日顺延到下一交易日）
    :param target_annual_dividend: 目标每年分红到账金额（元）
    :param tax_rate: 分红税率（0~1）
    :param reinvest: True=红利再投；False=分红不投
    :param reference: 每股年分红基准 — "last_year"=去年全年 / "trailing"=最近12个月
    :param lot_size: 买入整数倍股数（A股=100）
    :param forward_quotes: web 路径忽略（恒不传，保持 web 口径）；CLI 路径内部自取并透传
    :param sync: CLI 路径分红缺失时是否同步（web 路径忽略）
    :param log: None=web 路径（原样返回引擎 dict）；可调用对象=CLI 路径（打日志）
    :return: 引擎原始结果 dict（status/summary）
    """
    if log is None:
        # web 路径：与旧 dividend_target_service 逐行等价（不取前复权，
        # 恒不传 forward_quotes → 引擎默认 None）
        quotes = load_quotes(db, stock_code)
        dividends = load_dividends(db, stock_code)
        return plan_dividend_target(
            quotes=quotes,
            dividends=dividends,
            buy_date=buy_date,
            target_annual_dividend=target_annual_dividend,
            tax_rate=tax_rate,
            reinvest=reinvest,
            reference=reference,
            lot_size=lot_size,
        )

    # CLI 路径：与 分红目标测算.py 原 run() 取数段逐行等价
    # （静默加载前复权并透传给引擎——前复权仅影响 reinvest_plan.warnings）
    quotes = _load_quotes(db, stock_code, log)
    if quotes is None:
        return {"status": "no_data", "message": _no_data_msg(stock_code)}
    log(f"共 {len(quotes)} 个交易日（{quotes[0]['trade_date']} ~ {quotes[-1]['trade_date']}）")
    forward_quotes = _load_forward(db, stock_code, len(quotes), log)
    dividends = _load_dividends(db, stock_code, sync, log)
    return plan_dividend_target(
        quotes=quotes,
        dividends=dividends,
        buy_date=buy_date,
        target_annual_dividend=target_annual_dividend,
        tax_rate=tax_rate,
        reinvest=reinvest,
        reference=reference,
        lot_size=lot_size,
        forward_quotes=forward_quotes,
    )
