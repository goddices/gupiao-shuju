"""FastAPI 应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import engine
from models import Base
from routers import stocks, data, holiday, import_data
from config.datasource import get_data_source


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动创建数据库表（如不存在）"""
    Base.metadata.create_all(bind=engine)
    print(f"[启动] 数据源: {get_data_source()}")
    yield


app = FastAPI(
    title="股票分析 API",
    description="A股历史行情数据查询服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置（允许前端开发服务器跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理：返回友好的 JSON 错误信息"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"},
    )


# 注册路由
app.include_router(stocks.router)
app.include_router(data.router)
app.include_router(holiday.router)
app.include_router(import_data.router)


@app.get("/api/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "message": "股票分析 API 运行中",
        "data_source": get_data_source(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)