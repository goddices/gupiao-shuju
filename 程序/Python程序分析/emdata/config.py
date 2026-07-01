"""
重试配置和连接错误检测
"""
import aiohttp

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY_MIN = 1.0  # 最小重试等待(秒)
RETRY_DELAY_MAX = 2.0  # 最大重试等待(秒)


def _is_connection_error(error: Exception) -> bool:
    """判断是否为连接错误，需要重试"""
    error_str = str(error).lower()
    keywords = (
        "server disconnected",
        "connection reset",
        "connection refused",
        "peer closed",
        "connection error",
    )
    return any(kw in error_str for kw in keywords)
