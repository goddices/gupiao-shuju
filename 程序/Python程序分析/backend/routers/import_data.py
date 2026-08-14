"""数据导入 API 路由 —— 支持行情和基础信息的批量手动导入"""
import sys
import os
import time
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# 确保项目根在 sys.path 中以导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.datasource import set_data_source, get_data_source


router = APIRouter(prefix="/api/import", tags=["import"])


# ============================================================
#  Pydantic 模型
# ============================================================

class ImportQuotesRequest(BaseModel):
    stock_codes: List[str] = Field(..., min_length=1, description="股票代码列表")
    start_date: str = Field("2006-01-01", description="起始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期 YYYYMMDD，默认今天")
    data_source: str = Field("tickflow", description="数据源: tickflow / eastmoney / akshare")
    period: str = Field("daily", description="K线周期: daily / weekly / monthly")


class ImportBasicInfoRequest(BaseModel):
    """基础信息导入：同步股票列表 + 逐只拉取核心数据"""
    stock_codes: Optional[List[str]] = Field(None, description="要导入核心数据的股票代码列表；为 None 则只同步全量股票列表")
    sync_stock_list: bool = Field(True, description="是否先同步全市场股票代码列表")
    data_source: str = Field("tickflow", description="数据源: tickflow / eastmoney / akshare")


class ImportResult(BaseModel):
    status: str
    total: int = 0
    ok: int = 0
    fail: int = 0
    details: List[dict] = []


# ============================================================
#  行情导入
# ============================================================

@router.post("/quotes", response_model=ImportResult)
def import_quotes(req: ImportQuotesRequest):
    """
    批量导入股票行情数据（K线）

    - 支持选择数据源（tickflow / eastmoney / akshare）
    - 每只股票依次拉取不复权 + 前复权 + 后复权
    - 已存在的日期会被替换为最新价格
    """
    from datetime import date
    from database import SessionLocal
    from data_fetcher import fetch_stock_data_full

    # 临时切换数据源
    original = get_data_source()
    try:
        set_data_source(req.data_source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    end_date = req.end_date or date.today().strftime("%Y%m%d")

    db = SessionLocal()
    result = ImportResult(status="ok")
    try:
        for code in req.stock_codes:
            code = code.strip()
            if not code:
                continue
            detail = {"stock_code": code, "status": "", "msg": ""}
            for attempt in range(3):
                try:
                    r = fetch_stock_data_full(db, code, start_date=req.start_date, end_date=end_date)
                    detail["status"] = r["status"]
                    detail["msg"] = "; ".join(r["details"])
                    detail["rows"] = r["total_rows"]
                    db.commit()
                    if r["status"] in ("ok", "no_new_data"):
                        result.ok += 1
                    else:
                        result.fail += 1
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(5 * (attempt + 1))
                    else:
                        detail["status"] = "error"
                        detail["msg"] = str(e)
                        db.rollback()
                        result.fail += 1
            result.details.append(detail)
            result.total += 1
            time.sleep(1)  # 串行间隔避免限流
    finally:
        db.close()
        set_data_source(original)

    if result.fail > 0 and result.ok == 0:
        result.status = "error"
    elif result.fail > 0:
        result.status = "partial"

    return result


# ============================================================
#  基础信息导入
# ============================================================

@router.post("/basic-info", response_model=ImportResult)
def import_basic_info(req: ImportBasicInfoRequest):
    """
    批量导入基础信息

    包含两步：
    1. 同步全市场股票代码列表（可选）
    2. 为指定股票逐只拉取核心数据（PE、PB、ROE、市值等）
    """
    from database import SessionLocal
    from services import sync_stock_list, sync_stock_core_data

    original = get_data_source()
    try:
        set_data_source(req.data_source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db = SessionLocal()
    result = ImportResult(status="ok")
    try:
        # Step 1: 同步全量股票列表
        if req.sync_stock_list:
            list_result = sync_stock_list(db)
            result.details.append({
                "stock_code": "*",
                "status": list_result.get("status", "ok"),
                "msg": list_result.get("message", ""),
            })
            result.total += 1
            if list_result.get("status") == "ok":
                result.ok += 1
            else:
                result.fail += 1

        # Step 2: 逐只拉取核心数据
        if req.stock_codes:
            for code in req.stock_codes:
                code = code.strip()
                if not code:
                    continue
                detail = {"stock_code": code, "status": "", "msg": ""}
                for attempt in range(2):
                    try:
                        r = sync_stock_core_data(db, code)
                        detail["status"] = r.get("status", "ok")
                        detail["msg"] = r.get("message", "")
                        if r.get("status") != "error":
                            result.ok += 1
                        else:
                            result.fail += 1
                        break
                    except Exception as e:
                        if attempt < 1:
                            time.sleep(3)
                        else:
                            detail["status"] = "error"
                            detail["msg"] = str(e)
                            result.fail += 1
                result.details.append(detail)
                result.total += 1
    finally:
        db.close()
        set_data_source(original)

    if result.fail > 0 and result.ok == 0:
        result.status = "error"
    elif result.fail > 0:
        result.status = "partial"

    return result


# ============================================================
#  数据源信息
# ============================================================

@router.get("/datasource")
def get_current_datasource():
    """获取当前数据源配置"""
    return {"data_source": get_data_source()}
