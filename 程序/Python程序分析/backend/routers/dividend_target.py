"""分红目标测算 API 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import DividendTargetRequest
from services import get_stock_name
from dividend_target_service import plan_target

router = APIRouter(prefix="/api/dividend-target", tags=["dividend-target"])


@router.post("/{stock_code}/plan")
def plan_dividend_target(
    stock_code: str,
    request: DividendTargetRequest,
    db: Session = Depends(get_db),
):
    """分红目标测算：目标每年分红到账 X 元，需要在买入日投入多少钱"""
    result = plan_target(
        db,
        stock_code,
        buy_date=request.buy_date,
        target_annual_dividend=request.target_annual_dividend,
        tax_rate=request.tax_rate,
        reinvest=request.reinvest,
        reference=request.reference,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "测算失败"))
    return {
        "status": result["status"],
        "stock_code": stock_code,
        "stock_name": get_stock_name(db, stock_code) or stock_code,
        "summary": result["summary"],
    }
