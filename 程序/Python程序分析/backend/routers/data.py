"""数据管理 API 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import FetchRequest, FetchResponse
from data_fetcher import fetch_stock_data

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/fetch", response_model=FetchResponse)
def trigger_fetch(req: FetchRequest, db: Session = Depends(get_db)):
    """触发从东方财富拉取股票数据"""
    if not req.stock_codes:
        raise HTTPException(status_code=400, detail="stock_codes 不能为空")

    details = []
    success_count = 0
    for code in req.stock_codes:
        try:
            result = fetch_stock_data(db, code, req.start_date or "2006-01-01")
            details.append(result)
            if result["new_rows"] > 0:
                success_count += 1
        except Exception as e:
            details.append({
                "stock_code": code,
                "new_rows": 0,
                "message": f"错误: {str(e)}",
            })

    return FetchResponse(
        status="ok" if success_count > 0 else "no_new_data",
        message=f"处理完成: {success_count}/{len(req.stock_codes)} 只股票有新数据",
        details=details,
    )
