import random
import secrets
import time


def generate_eastmoney_cookie_str():
    current_ms = int(time.time() * 1000)
    current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def random_hex(length=32):
        return secrets.token_hex(length // 2)

    def random_alnum(length=24):
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        raw = "".join(secrets.choice(chars) for _ in range(length))
        pos = random.randint(4, length - 4)
        raw = raw[:pos] + "-" + raw[pos + 1 :]
        return raw

    def gen_st_psi():
        r1 = str(random.randint(100000000000, 999999999999))
        r2 = str(random.randint(1000000000, 9999999999))
        return f"{current_ms}-{r1}-{r2}"

    st_pvi = str(random.randint(10000000000000, 99999999999999))
    st_si = str(random.randint(10000000000000, 99999999999999))
    st_sn = str(random.randint(1, 10))  # 随机步数

    def generate_random20_qgqp_b_id() -> str:
        # 首位：1-9
        first = str(random.randint(1, 9))
        # 后19位：0-9
        rest = "".join(str(random.randint(0, 9)) for _ in range(19))
        return first + rest

    cookies = {
        "fullscreengg": "1",
        "fullscreengg2": "1",
        "st_asi": "delete",
        "qgqp_b_id": generate_random20_qgqp_b_id(),  # "f4748f77325434072983eb6c8d3b1787",
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
