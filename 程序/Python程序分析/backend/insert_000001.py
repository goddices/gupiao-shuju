"""插入上证指数到 stock_info 表"""
import sys
sys.path.insert(0, '.')
from database import SessionLocal
from models import StockInfo
from sqlalchemy import select

db = SessionLocal()
try:
    existing = db.execute(
        select(StockInfo).where(StockInfo.stock_code == '000001')
    ).scalar_one_or_none()

    if existing:
        print(f'已存在: {existing.stock_code} {existing.stock_name} market={existing.market}')
        existing.stock_name = '上证指数'
        existing.market = 'SH'
        db.commit()
        print('已更新为: 000001 上证指数 SH')
    else:
        s = StockInfo(stock_code='000001', stock_name='上证指数', market='SH')
        db.add(s)
        db.commit()
        print('已插入: 000001 上证指数 SH')
finally:
    db.close()
