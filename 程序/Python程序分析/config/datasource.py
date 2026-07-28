"""
数据源配置模块

通过环境变量或直接赋值切换数据源:
    export DATA_SOURCE=eastmoney   # 使用东方财富 (默认)
    export DATA_SOURCE=akshare     # 使用 AKShare

或在代码中:
    from config.datasource import set_data_source
    set_data_source("akshare")
"""

import os
from typing import Literal

DataSourceType = Literal["eastmoney", "akshare"]

# 默认数据源，可通过环境变量 DATA_SOURCE 覆盖
DATA_SOURCE: DataSourceType = os.getenv("DATA_SOURCE", "eastmoney").lower()  # type: ignore


def get_data_source() -> DataSourceType:
    """获取当前数据源配置"""
    return DATA_SOURCE


def set_data_source(source: DataSourceType) -> None:
    """
    动态切换数据源

    Args:
        source: "eastmoney" 或 "akshare"

    Raises:
        ValueError: 如果数据源名称无效
    """
    global DATA_SOURCE
    source_lower = source.lower()
    if source_lower not in ("eastmoney", "akshare"):
        raise ValueError(f"不支持的数据源: {source}，可选值: eastmoney, akshare")
    DATA_SOURCE = source_lower  # type: ignore
    print(f"[datasource] 已切换到: {DATA_SOURCE}")


def is_eastmoney() -> bool:
    """是否使用东方财富数据源"""
    return DATA_SOURCE == "eastmoney"


def is_akshare() -> bool:
    """是否使用 AKShare 数据源"""
    return DATA_SOURCE == "akshare"
