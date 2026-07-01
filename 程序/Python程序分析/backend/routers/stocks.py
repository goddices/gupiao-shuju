"""股票行情相关 API 路由"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    QuoteListResponse,
    StockStatsOut,
    StockSummaryOut,
    StockInfoOut,
    StockInfoSyncOut,
    StockFetchOut,
    DividendEventOut,
    StockCoreDataOut,
    StockCoreDataSyncOut,
)
from services import (
    get_available_stocks,
    get_all_stock_infos,
    get_stock_quotes,
    get_stock_stats,
    get_stock_dividends,
    sync_stock_list,
    get_stock_core_data,
    sync_stock_core_data,
)
from data_fetcher import fetch_stock_data_full

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("", response_model=list[StockSummaryOut])
def list_stocks(db: Session = Depends(get_db)):
    """获取所有有数据的股票列表"""
    return get_available_stocks(db)


@router.get("/info", response_model=list[StockInfoOut])
def list_stock_infos(
    q: str = Query(None, description="搜索关键字（按代码或名称模糊匹配）"),
    db: Session = Depends(get_db),
):
    """获取全量股票代码和名称（用于数据管理页搜索选择）"""
    return get_all_stock_infos(db, q=q)


@router.post("/sync", response_model=StockInfoSyncOut)
def sync_stocks(db: Session = Depends(get_db)):
    """从东方财富同步全市场股票代码和名称"""
    return sync_stock_list(db)


@router.post("/{stock_code}/fetch", response_model=StockFetchOut)
def fetch_stock_quotes(stock_code: str, db: Session = Depends(get_db)):
    """同步单只股票的行情数据（不复权+前复权+后复权）"""
    result = fetch_stock_data_full(db, stock_code)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail="; ".join(result["details"]))
    return result


@router.get("/{stock_code}/quotes", response_model=QuoteListResponse)
def stock_quotes(
    stock_code: str,
    adjust_type: str = Query("none", description="复权类型: none / forward / backward"),
    start_date: Optional[date] = Query(None, description="起始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=5000, description="每页条数"),
    db: Session = Depends(get_db),
):
    """分页获取日K线数据"""
    if adjust_type not in ("none", "forward", "backward"):
        raise HTTPException(status_code=400, detail="adjust_type 必须为 none / forward / backward")
    return get_stock_quotes(
        db, stock_code, adjust_type, start_date, end_date, page, page_size
    )


@router.get("/{stock_code}/core-data", response_model=StockCoreDataOut)
def stock_core_data(stock_code: str, db: Session = Depends(get_db)):
    """从数据库获取个股核心数据"""
    result = get_stock_core_data(db, stock_code)
    if result is None:
        raise HTTPException(status_code=404, detail=f"股票 {stock_code} 暂无核心数据，请先同步")
    return result


@router.post("/{stock_code}/fetch-core-data", response_model=StockCoreDataSyncOut)
def fetch_stock_core(stock_code: str, db: Session = Depends(get_db)):
    """从东方财富同步个股核心数据并保存到数据库"""
    result = sync_stock_core_data(db, stock_code)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/{stock_code}/stats", response_model=StockStatsOut)
def stock_stats(stock_code: str, db: Session = Depends(get_db)):
    """获取股票统计信息"""
    result = get_stock_stats(db, stock_code)
    if result["total_records"] == 0:
        raise HTTPException(status_code=404, detail=f"股票 {stock_code} 无数据")
    return result


@router.get("/{stock_code}/dividends")
def stock_dividends(
    stock_code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """获取分红事件列表"""
    return get_stock_dividends(db, stock_code, page, page_size)
