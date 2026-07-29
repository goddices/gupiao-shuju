"""模拟买卖持仓 API"""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from simulation_service import (
    get_account_summary,
    execute_buy,
    execute_sell,
    reset_account,
    get_trade_history,
    update_fee_config,
)

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.get("/account")
def account_summary(db: Session = Depends(get_db)):
    """账户概览：现金、持仓、总资产、总盈亏"""
    return get_account_summary(db)


@router.post("/buy")
def buy(
    stock_code: str = Query(..., description="股票代码"),
    stock_name: str = Query("", description="股票名称（可选，自动补齐）"),
    shares: int = Query(100, ge=100, description="买入股数（100的整数倍）"),
    price: Optional[float] = Query(None, description="成交价，留空则用最新收盘价"),
    trade_date: Optional[date] = Query(None, description="交易日期，留空则用最新行情日期"),
    db: Session = Depends(get_db),
):
    """买入股票"""
    return execute_buy(db, stock_code, stock_name, shares, price, trade_date)


@router.post("/sell")
def sell(
    stock_code: str = Query(..., description="股票代码"),
    shares: int = Query(100, ge=100, description="卖出股数（100的整数倍）"),
    price: Optional[float] = Query(None, description="成交价，留空则用最新收盘价"),
    trade_date: Optional[date] = Query(None, description="交易日期，留空则用最新行情日期"),
    db: Session = Depends(get_db),
):
    """卖出股票（自动计算佣金+印花税）"""
    return execute_sell(db, stock_code, shares, price, trade_date)


@router.get("/trades")
def trade_history(
    limit: int = Query(50, ge=1, le=500, description="返回条数"),
    db: Session = Depends(get_db),
):
    """交易记录"""
    return get_trade_history(db, limit)


@router.post("/reset")
def reset(
    initial_cash: float = Query(100000, description="重置后的初始资金"),
    db: Session = Depends(get_db),
):
    """重置账户：清空持仓和交易记录"""
    return reset_account(db, initial_cash)


@router.put("/fee-config")
def set_fee_config(
    commission_rate: Optional[float] = Query(None, description="佣金费率（如 0.0003 = 万分之三）"),
    min_commission: Optional[float] = Query(None, description="最低佣金（元）"),
    stamp_tax_rate: Optional[float] = Query(None, description="印花税率（如 0.0005 = 万分之五）"),
    db: Session = Depends(get_db),
):
    """更新费率配置"""
    return update_fee_config(db, commission_rate, min_commission, stamp_tax_rate)
