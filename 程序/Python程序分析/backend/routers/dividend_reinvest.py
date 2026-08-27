"""红利再投模拟 API 路由"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import DividendSimulateRequest
from services import sync_stock_dividends, get_stock_dividend_details, get_stock_name
from dividend_reinvest_service import run_dividend_reinvest

router = APIRouter(prefix="/api/dividend-reinvest", tags=["dividend-reinvest"])


@router.get("/{stock_code}/dividends")
def dividend_details(
    stock_code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """获取个股分红明细列表（东方财富数据）"""
    return get_stock_dividend_details(db, stock_code, page, page_size)


@router.post("/{stock_code}/sync")
def sync_dividends(stock_code: str, db: Session = Depends(get_db)):
    """从东方财富同步个股分红明细并保存到数据库"""
    result = sync_stock_dividends(db, stock_code)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/{stock_code}/simulate")
def simulate_dividend_reinvest(
    stock_code: str,
    request: DividendSimulateRequest,
    db: Session = Depends(get_db),
):
    """红利再投模拟：不复权价格 + 分红到账后无脑买入，与两个基准对比"""
    result = run_dividend_reinvest(
        db,
        stock_code,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_cash=request.initial_cash,
        tax_rate=request.tax_rate,
        reinvest=request.reinvest,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "模拟失败"))
    return {
        "status": result["status"],
        "stock_code": stock_code,
        "stock_name": get_stock_name(db, stock_code) or stock_code,
        "summary": result["summary"],
        "dividend_events": result["dividend_events"],
        "equity_curve": result["equity_curve"],
        "warnings": result["warnings"],
    }
