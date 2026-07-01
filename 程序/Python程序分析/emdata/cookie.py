"""
东方财富 Cookie 模拟生成
"""
import random
import secrets
import time


def generate_eastmoney_cookie_str():
    """
    生成模拟的东方财富网 Cookie 字符串。
    返回格式: "key1=value1; key2=value2; ..."
    所有动态值（时间戳、随机ID、会话计数等）都会实时生成。
    """
    # 当前毫秒时间戳
    current_ms = int(time.time() * 1000)
    # 当前时间字符串（用于 st_sp）
    current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 生成 32 位十六进制随机串（模拟浏览器指纹）
    def random_hex(length=32):
        return secrets.token_hex(length // 2)

    # 辅助：生成24位字母数字混合串（含一个短横线）
    def random_alnum(length=24):
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        raw = "".join(secrets.choice(chars) for _ in range(length))
        # 随机插入一个 '-' 使格式更像原始
        pos = random.randint(4, length - 4)
        raw = raw[:pos] + "-" + raw[pos + 1:]
        return raw

    # 辅助：生成 st_psi（时间戳-随机数-随机数）
    def gen_st_psi():
        r1 = str(random.randint(100000000000, 999999999999))
        r2 = str(random.randint(1000000000, 9999999999))
        return f"{current_ms}-{r1}-{r2}"

    # 生成 st_pvi（14位数字）
    st_pvi = str(random.randint(10000000000000, 99999999999999))

    # 生成 st_si（14位数字）
    st_si = str(random.randint(10000000000000, 99999999999999))

    # 构建 Cookie 字典
    cookies = {
        "fullscreengg": "1",
        "fullscreengg2": "1",
        "st_asi": "delete",
        "qgqp_b_id": random_hex(32),
        "nid18": random_hex(32),
        "nid18_create_time": str(current_ms),
        "gviem": random_alnum(24),
        "gviem_create_time": str(current_ms),
        "st_nvi": random_alnum(24),
        "st_pvi": st_pvi,
        "st_si": st_si,
        "st_sn": "1",  # 会话步数，从 1 开始
        "st_sp": current_time_str,
        "st_inirUrl": "https%3A%2F%2Fwww.eastmoney.com%2F",
        "websitepoptg_api_time": str(current_ms),
        "st_psi": gen_st_psi(),
    }

    # 拼接成字符串
    return "; ".join([f"{k}={v}" for k, v in cookies.items()])
