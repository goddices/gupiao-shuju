"""数据库导出 API 路由 —— 将全部表导出为 SQL 文件（带进度追踪）"""
import os
import threading
import uuid
from datetime import datetime, date
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text

from database import engine

router = APIRouter(prefix="/api/export", tags=["export"])

EXPORT_DIR = "/tmp/gupiao_exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

# 导出顺序: 小表先导（进度快速推进），最大表 stock_daily_quote 放最后
EXPORT_TABLES = [
    "stock_info",
    "stock_core_data",
    "stock_dividend_events",
    "stock_cookies",
    "simulation_account",
    "simulation_position",
    "simulation_trade",
    "stock_weekday_stats",
    "stock_daily_quote",
]

# 导出任务状态（内存存储，进程重启即失效）
_export_tasks = {}
_export_tasks_lock = threading.Lock()


def _sql_value(v) -> str:
    """将 Python 值转为 SQL 字面量"""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    if isinstance(v, (datetime, date)):
        return f"'{v:%Y-%m-%d %H:%M:%S}'"
    if isinstance(v, bytes):
        return f"X'{v.hex()}'"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def _run_export(task_id: str):
    """后台线程执行导出"""
    task = _export_tasks[task_id]
    file_path = os.path.join(EXPORT_DIR, f"{task_id}.sql")

    def update(**kwargs):
        with _export_tasks_lock:
            task.update(kwargs)

    try:
        # 1. 统计各表行数（总进度基准）
        with engine.connect() as conn:
            total_rows = 0
            table_rows = {}
            for t in EXPORT_TABLES:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
                table_rows[t] = cnt
                total_rows += cnt
            update(total_rows=total_rows)
            for t in EXPORT_TABLES:
                update(tables={**task["tables"], t: {"rows": table_rows[t], "status": "pending"}})

            # 2. 逐表导出
            done_rows = 0
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"-- 股票分析系统数据库导出\n")
                f.write(f"-- 导出时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
                f.write(f"-- 共 {len(EXPORT_TABLES)} 张表, {total_rows} 行数据\n")
                f.write("SET NAMES utf8mb4;\n\n")

                for t in EXPORT_TABLES:
                    update(current_table=t, status="running")
                    with _export_tasks_lock:
                        task["tables"][t]["status"] = "running"

                    # DDL
                    ddl = conn.execute(text(f"SHOW CREATE TABLE `{t}`")).fetchone()[1]
                    f.write(f"DROP TABLE IF EXISTS `{t}`;\n")
                    f.write(ddl.rstrip() + ";\n\n")

                    # 数据（分块写入 INSERT）
                    result = conn.execute(text(f"SELECT * FROM `{t}`"))
                    columns = result.keys()
                    col_str = ", ".join(f"`{c}`" for c in columns)
                    while True:
                        rows = result.fetchmany(500)
                        if not rows:
                            break
                        values = ",\n".join(
                            "(" + ", ".join(_sql_value(v) for v in row) + ")" for row in rows
                        )
                        f.write(f"INSERT INTO `{t}` ({col_str}) VALUES\n{values};\n")
                        done_rows += len(rows)
                        percent = round(done_rows / total_rows * 100, 1) if total_rows else 100.0
                        update(done_rows=done_rows, percent=percent)
                    f.write("\n")
                    with _export_tasks_lock:
                        task["tables"][t]["status"] = "done"

            update(status="done", percent=100.0, file_path=file_path,
                   message=f"导出完成: {len(EXPORT_TABLES)} 张表, {total_rows} 行")
            print(f"[export] {task_id} 导出完成: {file_path}")
    except Exception as e:
        update(status="error", message=f"导出失败: {e}")
        print(f"[export] {task_id} 导出失败: {e}")


@router.post("/sql")
def start_export():
    """启动全库 SQL 导出，返回 task_id"""
    task_id = f"exp_{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:6]}"
    with _export_tasks_lock:
        _export_tasks[task_id] = {
            "task_id": task_id,
            "status": "starting",
            "current_table": "",
            "done_rows": 0,
            "total_rows": 0,
            "percent": 0.0,
            "file_path": None,
            "message": "准备中...",
            "tables": {t: {"rows": 0, "status": "pending"} for t in EXPORT_TABLES},
        }
    threading.Thread(target=_run_export, args=(task_id,), daemon=True,
                     name=f"export-{task_id}").start()
    return {"task_id": task_id}


@router.get("/progress/{task_id}")
def get_progress(task_id: str):
    """查询导出进度"""
    with _export_tasks_lock:
        task = _export_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="导出任务不存在")
    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "current_table": task["current_table"],
        "done_rows": task["done_rows"],
        "total_rows": task["total_rows"],
        "percent": task["percent"],
        "message": task["message"],
        "tables": task["tables"],
    }


@router.get("/download/{task_id}")
def download_export(task_id: str):
    """下载导出的 SQL 文件"""
    with _export_tasks_lock:
        task = _export_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="导出任务不存在")
    if task["status"] != "done" or not task["file_path"]:
        raise HTTPException(status_code=400, detail="导出尚未完成")
    return FileResponse(
        task["file_path"],
        filename=f"deepstock_export_{datetime.now():%Y%m%d%H%M%S}.sql",
        media_type="application/sql",
    )
