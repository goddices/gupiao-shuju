"""
重试配置和连接错误检测
"""
import aiohttp

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY_MIN = 0.01  # 最小重试等待(秒) = 10ms
RETRY_DELAY_MAX = 0.05  # 最大重试等待(秒) = 50ms

# 初始固定 Cookie —— DB 为空时的兜底种子
SEED_COOKIE = (
    "qgqp_b_id=f4748f77325434072983eb6c8d3b1787; "
    "st_nvi=l1ttKvvz-KFC4SHyE5XkX2b32; "
    "nid18=03c6d02868a9633902b24e9d0c2bf5a5; "
    "nid18_create_time=1779672782320; "
    "gviem=YQiok4IwaN9QhfQ49tnGg622f; "
    "gviem_create_time=1779672782320; "
    "st_si=61139111807372; "
    "st_asi=delete; "
    "websitepoptg_api_time=1781595449901; "
    "fullscreengg=1; "
    "fullscreengg2=1; "
    "st_pvi=98259179438234; "
    "st_sp=2026-02-13%2014%3A32%3A39; "
    "st_inirUrl=https%3A%2F%2Fwww.eastmoney.com%2F; "
    "st_sn=8; "
    "st_psi=20260616155130641-111000300841-4604397663"
)


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
