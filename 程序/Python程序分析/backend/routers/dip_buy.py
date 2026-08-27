"""大跌买入 + 红利再投 API 路由（两种策略：高点回撤一次性买入 / 当日大跌分批买入）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import DipBuyRequest
from services import get_stock_name
from dip_buy_service import run_dip_buy

router = APIRouter(prefix="/api/dip-buy", tags=["dip-buy"])


@router.post("/{stock_code}/simulate")
def simulate_dip_buy(
    stock_code: str,
    request: DipBuyRequest,
    db: Session = Depends(get_db),
):
    """大跌买入 + 红利再投：strategy=drawdown（回撤 x% 一次性买 y 万）
    或 strategy=daily_drop（当天盘中大跌 x% 按最低价买入总仓位 y% 的一笔）"""
    result = run_dip_buy(
        db,
        stock_code,
        dip_pct=request.dip_pct,
        buy_amount=request.buy_amount * 10000,  # 万元 → 元
        start_date=request.start_date,
        end_date=request.end_date,
        tax_rate=request.tax_rate,
        reinvest=request.reinvest,
        strategy=request.strategy,
        total_position=request.total_position * 10000,  # 万元 → 元
        buy_ratio=request.buy_ratio,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "模拟失败"))
    return {
        "status": result["status"],
        "stock_code": stock_code,
        "stock_name": get_stock_name(db, stock_code) or stock_code,
        "strategy": request.strategy,
        "params": result.get("params"),
        "trigger": result.get("trigger"),
        "triggers": result.get("triggers", []),
        "summary": result["summary"],
        "dividend_events": result["dividend_events"],
        "equity_curve": result["equity_curve"],
        "warnings": result["warnings"],
    }
