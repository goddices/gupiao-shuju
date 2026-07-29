import random
import secrets
import time
import hashlib


# ---- 浏览器指纹模拟 ----
# qgqp_b_id 是东财前端 JS 通过浏览器指纹技术生成的 32 位 hex。
# 例如: f4748f77325434072983eb6c8d3b1787
# 指纹 = 浏览器属性 + Canvas + WebGL + 音频 → MD5

# 常见显示器分辨率池
_SCREEN_RESOLUTIONS = [
    "1920x1080x24", "2560x1440x24", "1680x1050x24",
    "1440x900x24", "1536x864x24", "1366x768x24",
]

# 常见时区
_TIMEZONES = ["Asia/Shanghai", "Asia/Shanghai", "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Tokyo"]

# WebGL 渲染器变体 (macOS)
_WEBGL_RENDERERS = [
    "ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)",
    "ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)",
    "ANGLE (Apple, ANGLE Metal Renderer: Apple M3, Unspecified Version)",
]

# Canvas 噪声 (模拟不同渲染)
_CANVAS_NOISE = [
    "a3f8c2e1", "b7d4f9a2", "c1e5b8d3", "d9f2a6c4",
    "e4b7c8f1", "f2a5d7e3", "a8c3f6b2", "b1d9e4f7",
]


def _generate_qgqp_b_id() -> str:
    """
    模拟浏览器指纹生成 qgqp_b_id

    JS 端基于以下属性组合后 MD5:
      navigator.userAgent + screen.width/height/colorDepth
      + timezone + language + platform + hardwareConcurrency
      + WebGL renderer + canvas fingerprint + audio fingerprint
    """
    import random as _r

    # 模拟浏览器属性
    screen = _r.choice(_SCREEN_RESOLUTIONS)
    tz = _r.choice(_TIMEZONES)
    webgl = _r.choice(_WEBGL_RENDERERS)
    canvas = _r.choice(_CANVAS_NOISE)

    # platform / hardware 保持稳定以模拟同一设备
    platform = "MacIntel"
    cores = _r.choice([8, 10, 12])
    language = "zh-CN"

    fingerprint = (
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36|"
        f"{screen}|{tz}|{language}|{platform}|{cores}|"
        f"{webgl}|canvas_{canvas}|audio_{secrets.token_hex(4)}"
    )

    return hashlib.md5(fingerprint.encode()).hexdigest()


def generate_random20_qgqp_b_id() -> str:
    """20位随机数字 qgqp_b_id（双数次重试用，与指纹版本格式不同）"""
    first = str(random.randint(1, 9))
    rest = "".join(str(random.randint(0, 9)) for _ in range(19))
    return first + rest


def generate_eastmoney_cookie_str():
    current_ms = int(time.time() * 1000)
    current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def random_hex(length=32):
        return secrets.token_hex(length // 2)

    def random_alnum(length=24):
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        raw = "".join(secrets.choice(chars) for _ in range(length))
        pos = random.randint(4, length - 4)
        return raw[:pos] + "-" + raw[pos + 1 :]

    def gen_st_psi():
        r1 = str(random.randint(100000000000, 999999999999))
        r2 = str(random.randint(1000000000, 9999999999))
        return f"{current_ms}-{r1}-{r2}"

    st_pvi = str(random.randint(10000000000000, 99999999999999))
    st_si = str(random.randint(10000000000000, 99999999999999))
    st_sn = str(random.randint(1, 10))

    cookies = {
        "fullscreengg": "1",
        "fullscreengg2": "1",
        "st_asi": "delete",
        "qgqp_b_id": _generate_qgqp_b_id(),
        "nid18": random_hex(32),
        "nid18_create_time": str(current_ms),
        "gviem": random_alnum(24),
        "gviem_create_time": str(current_ms),
        "st_nvi": random_alnum(24),
        "st_pvi": st_pvi,
        "st_si": st_si,
        "st_sn": st_sn,
        "st_sp": current_time_str,
        "st_inirUrl": "https%3A%2F%2Fwww.eastmoney.com%2F",
        "websitepoptg_api_time": str(current_ms),
        "st_psi": gen_st_psi(),
    }
    return "; ".join([f"{k}={v}" for k, v in cookies.items()])
