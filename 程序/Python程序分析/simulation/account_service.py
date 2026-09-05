"""模拟买卖持仓服务 —— A股费用计算、买卖、持仓管理"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import SimulationAccount, SimulationPosition, SimulationTrade, StockInfo, StockDailyQuote
from database import SessionLocal


# ============================================================
#  费用计算
# ============================================================

def calc_commission(amount: float, rate: float, min_fee: float = 5.0) -> float:
    """计算佣金（买卖双向收取），不低于最低佣金"""
    fee = amount * rate
    return max(fee, min_fee)


def calc_stamp_tax(amount: float, rate: float) -> float:
    """计算印花税（仅卖出时收取）"""
    return amount * rate


# ============================================================
#  账户管理
# ============================================================

def get_or_create_account(db: Session) -> SimulationAccount:
    """获取或创建默认账户"""
    account = db.query(SimulationAccount).first()
    if not account:
        account = SimulationAccount(
            name="默认账户",
            initial_cash=Decimal("100000"),
            cash=Decimal("100000"),
            commission_rate=Decimal("0.0001"),
            min_commission=Decimal("5.00"),
            stamp_tax_rate=Decimal("0.0005"),
        )
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


def get_account_summary(db: Session) -> dict:
    """账户概览：现金、持仓市值、总盈亏"""
    account = get_or_create_account(db)

    positions = db.query(SimulationPosition).filter(
        SimulationPosition.account_id == account.id,
        SimulationPosition.shares > 0,
    ).all()

    # 刷新持仓的最新市价
    for pos in positions:
        quote = db.query(StockDailyQuote).filter(
            StockDailyQuote.stock_code == pos.stock_code,
        ).order_by(StockDailyQuote.trade_date.desc()).first()
        if quote:
            pos.current_price = quote.close_price

    db.commit()

    total_market_value = Decimal("0")
    total_cost = Decimal("0")
    for pos in positions:
        if pos.current_price:
            total_market_value += Decimal(str(pos.current_price)) * pos.shares
        total_cost += pos.total_cost

    total_pl = total_market_value + account.cash - account.initial_cash
    total_pl_pct = float(total_pl / account.initial_cash * 100) if account.initial_cash > 0 else 0

    return {
        "account_id": account.id,
        "account_name": account.name,
        "initial_cash": float(account.initial_cash),
        "cash": float(account.cash),
        "total_market_value": float(total_market_value),
        "total_assets": float(account.cash + total_market_value),
        "total_cost": float(total_cost),
        "total_pl": float(total_pl),
        "total_pl_pct": round(total_pl_pct, 2),
        "commission_rate": float(account.commission_rate),
        "min_commission": float(account.min_commission),
        "stamp_tax_rate": float(account.stamp_tax_rate),
        "positions": [
            {
                "id": p.id,
                "stock_code": p.stock_code,
                "stock_name": p.stock_name,
                "shares": p.shares,
                "avg_cost": float(p.avg_cost),
                "total_cost": float(p.total_cost),
                "current_price": float(p.current_price) if p.current_price else None,
                "market_value": float(p.current_price * p.shares) if p.current_price else 0,
                "pl": float(Decimal(str(p.current_price or 0)) * p.shares - p.total_cost),
                "pl_pct": round(float((Decimal(str(p.current_price or 0)) - p.avg_cost) / p.avg_cost * 100), 2) if p.avg_cost > 0 else 0,
            }
            for p in positions
        ],
    }


def update_fee_config(db: Session, commission_rate: float = None, min_commission: float = None, stamp_tax_rate: float = None) -> dict:
    """更新费率配置"""
    account = get_or_create_account(db)
    if commission_rate is not None:
        account.commission_rate = Decimal(str(commission_rate))
    if min_commission is not None:
        account.min_commission = Decimal(str(min_commission))
    if stamp_tax_rate is not None:
        account.stamp_tax_rate = Decimal(str(stamp_tax_rate))
    db.commit()
    return {
        "commission_rate": float(account.commission_rate),
        "min_commission": float(account.min_commission),
        "stamp_tax_rate": float(account.stamp_tax_rate),
    }


# ============================================================
#  买卖交易
# ============================================================

def execute_buy(
    db: Session,
    stock_code: str,
    stock_name: str = "",
    shares: int = 100,
    price: Optional[float] = None,
    trade_date: Optional[date] = None,
) -> dict:
    """买入股票"""
    if shares <= 0:
        return {"status": "error", "message": "买入股数必须大于0"}
    if shares % 100 != 0:
        return {"status": "error", "message": "A股买入必须是100股（1手）的整数倍"}

    account = get_or_create_account(db)

    # 获取最新市价
    if price is None:
        quote = db.query(StockDailyQuote).filter(
            StockDailyQuote.stock_code == stock_code,
        ).order_by(StockDailyQuote.trade_date.desc()).first()
        if not quote:
            return {"status": "error", "message": f"数据库中没有 {stock_code} 的行情，请先导入"}
        price = float(quote.close_price)
        if trade_date is None:
            trade_date = quote.trade_date

    if trade_date is None:
        trade_date = date.today()

    # 补齐股票名称
    if not stock_name:
        info = db.query(StockInfo).filter(StockInfo.stock_code == stock_code).first()
        stock_name = info.stock_name if info else stock_code

    amount = price * shares
    commission = calc_commission(amount, float(account.commission_rate), float(account.min_commission))
    total_cost = amount + commission

    if account.cash < Decimal(str(total_cost)):
        return {
            "status": "error",
            "message": f"现金不足！需要 ¥{total_cost:.2f}，当前现金 ¥{float(account.cash):.2f}",
        }

    # 扣款
    account.cash -= Decimal(str(total_cost))

    # 更新持仓
    pos = db.query(SimulationPosition).filter(
        SimulationPosition.account_id == account.id,
        SimulationPosition.stock_code == stock_code,
    ).first()

    if pos:
        # 加仓
        total_shares = pos.shares + shares
        total_cost_all = float(pos.total_cost) + total_cost
        pos.shares = total_shares
        pos.avg_cost = Decimal(str(total_cost_all / total_shares))
        pos.total_cost = Decimal(str(total_cost_all))
    else:
        pos = SimulationPosition(
            account_id=account.id,
            stock_code=stock_code,
            stock_name=stock_name,
            shares=shares,
            avg_cost=Decimal(str(total_cost / shares)),
            total_cost=Decimal(str(total_cost)),
        )
        db.add(pos)

    # 记录交易
    trade = SimulationTrade(
        account_id=account.id,
        stock_code=stock_code,
        stock_name=stock_name,
        trade_type="buy",
        shares=shares,
        price=Decimal(str(price)),
        amount=Decimal(str(amount)),
        commission=Decimal(str(commission)),
        stamp_tax=0,
        trade_date=trade_date,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)

    return {
        "status": "ok",
        "message": f"买入 {stock_name}({stock_code}) {shares}股 @ ¥{price:.2f}",
        "trade_id": trade.id,
        "shares": shares,
        "price": price,
        "amount": round(amount, 2),
        "commission": round(commission, 2),
        "total_cost": round(total_cost, 2),
        "cash_remaining": float(account.cash),
    }


def execute_sell(
    db: Session,
    stock_code: str,
    shares: int = 100,
    price: Optional[float] = None,
    trade_date: Optional[date] = None,
) -> dict:
    """卖出股票"""
    if shares <= 0:
        return {"status": "error", "message": "卖出股数必须大于0"}
    if shares % 100 != 0:
        return {"status": "error", "message": "A股卖出必须是100股（1手）的整数倍"}

    account = get_or_create_account(db)

    pos = db.query(SimulationPosition).filter(
        SimulationPosition.account_id == account.id,
        SimulationPosition.stock_code == stock_code,
    ).first()

    if not pos or pos.shares <= 0:
        return {"status": "error", "message": f"没有 {stock_code} 的持仓"}
    if pos.shares < shares:
        return {"status": "error", "message": f"持仓不足！持有 {pos.shares} 股，试图卖出 {shares} 股"}

    stock_name = pos.stock_name

    if price is None:
        quote = db.query(StockDailyQuote).filter(
            StockDailyQuote.stock_code == stock_code,
        ).order_by(StockDailyQuote.trade_date.desc()).first()
        if not quote:
            return {"status": "error", "message": f"数据库中没有 {stock_code} 的行情"}
        price = float(quote.close_price)
        if trade_date is None:
            trade_date = quote.trade_date

    if trade_date is None:
        trade_date = date.today()

    amount = price * shares
    commission = calc_commission(amount, float(account.commission_rate), float(account.min_commission))
    stamp_tax = calc_stamp_tax(amount, float(account.stamp_tax_rate))
    total_fee = commission + stamp_tax
    net_proceeds = amount - total_fee

    # 计算盈亏
    sell_cost_portion = float(pos.avg_cost) * shares
    profit_loss = net_proceeds - sell_cost_portion
    profit_loss_pct = (profit_loss / sell_cost_portion * 100) if sell_cost_portion > 0 else 0

    # 更新现金
    account.cash += Decimal(str(net_proceeds))

    # 更新持仓
    pos.shares -= shares
    if pos.shares == 0:
        pos.avg_cost = Decimal("0")
        pos.total_cost = Decimal("0")
    else:
        pos.total_cost -= Decimal(str(sell_cost_portion))

    # 记录交易
    trade = SimulationTrade(
        account_id=account.id,
        stock_code=stock_code,
        stock_name=stock_name,
        trade_type="sell",
        shares=shares,
        price=Decimal(str(price)),
        amount=Decimal(str(amount)),
        commission=Decimal(str(commission)),
        stamp_tax=Decimal(str(stamp_tax)),
        profit_loss=Decimal(str(round(profit_loss, 2))),
        profit_loss_pct=Decimal(str(round(profit_loss_pct, 4))),
        trade_date=trade_date,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)

    return {
        "status": "ok",
        "message": f"卖出 {stock_name}({stock_code}) {shares}股 @ ¥{price:.2f}",
        "trade_id": trade.id,
        "shares": shares,
        "price": price,
        "amount": round(amount, 2),
        "commission": round(commission, 2),
        "stamp_tax": round(stamp_tax, 2),
        "net_proceeds": round(net_proceeds, 2),
        "profit_loss": round(profit_loss, 2),
        "profit_loss_pct": round(profit_loss_pct, 2),
        "cash_remaining": float(account.cash),
    }


def reset_account(db: Session, initial_cash: float = 100000) -> dict:
    """重置账户：清空持仓和交易记录，恢复初始资金"""
    account = get_or_create_account(db)

    # 清空持仓
    db.query(SimulationPosition).filter(SimulationPosition.account_id == account.id).delete()
    # 清空交易记录
    db.query(SimulationTrade).filter(SimulationTrade.account_id == account.id).delete()

    account.cash = Decimal(str(initial_cash))
    account.initial_cash = Decimal(str(initial_cash))
    db.commit()

    return {"status": "ok", "message": f"账户已重置，初始资金 ¥{initial_cash:,.0f}"}


def get_trade_history(db: Session, limit: int = 50) -> list:
    """获取交易记录"""
    account = get_or_create_account(db)
    trades = db.query(SimulationTrade).filter(
        SimulationTrade.account_id == account.id
    ).order_by(SimulationTrade.created_at.desc()).limit(limit).all()

    return [
        {
            "id": t.id,
            "stock_code": t.stock_code,
            "stock_name": t.stock_name,
            "trade_type": t.trade_type,
            "shares": t.shares,
            "price": float(t.price),
            "amount": float(t.amount),
            "commission": float(t.commission),
            "stamp_tax": float(t.stamp_tax),
            "profit_loss": float(t.profit_loss) if t.profit_loss else None,
            "profit_loss_pct": float(t.profit_loss_pct) if t.profit_loss_pct else None,
            "trade_date": str(t.trade_date),
        }
        for t in trades
    ]
