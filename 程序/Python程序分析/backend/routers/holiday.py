"""节日涨跌分析 API 路由"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import HolidayAnalysisResponse
from services import get_holiday_analysis, get_all_stock_infos

router = APIRouter(prefix="/api/holiday", tags=["holiday"])


@router.get("/analysis", response_model=HolidayAnalysisResponse)
def holiday_analysis(
    stock_code: str = Query("000001", description="股票代码"),
    db: Session = Depends(get_db),
):
    """获取节日前后涨跌分析"""
    result = get_holiday_analysis(db, stock_code)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # 补充股票名称
    stock_infos = get_all_stock_infos(db, q=stock_code)
    stock_name = None
    for info in stock_infos:
        if info["stock_code"] == stock_code:
            stock_name = info["stock_name"]
            break
    result["stock_name"] = stock_name

    return result
