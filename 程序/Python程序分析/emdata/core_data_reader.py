"""
东方财富个股核心数据读取器
获取 ROE、PE、PB、毛利率等核心财务指标
"""
import asyncio
import aiohttp
import json
import random
import time
from typing import Optional, Dict, Any

from emdata.config import MAX_RETRIES, RETRY_DELAY_MIN, RETRY_DELAY_MAX, _is_connection_error, SEED_COOKIE
from emdata.models import StockInfo
from emdata.cookie import generate_eastmoney_cookie_str
from emdata.quote_reader import _generate_simple_cookie


class EastmoneyCurrentCoreDataReader:
    """
    东方财富个股核心数据读取器（异步）
    获取 ROE、PE、每股收益、市值等核心财务指标
    """

    BASE_URL = "https://push2.eastmoney.com/api/qt/stock/get"

    # 字段映射表（stock/get 端点 —— 已验证的字段）
    # 注意: stock/get 返回值已经是最终展示单位，无需额外转换
    FIELD_MAP = {
        "f58": "stock_name",       # 股票名称
        "f55": "change_pct",       # 涨跌幅（%）— 已经是百分数
        "f62": "pb",               # 市净率
        "f186": "gross_margin",    # 毛利率（%）— 已经是百分数
        "f187": "net_margin",      # 净利率（%）— 已经是百分数
        "f188": "debt_ratio",      # 资产负债率（%）— 已经是百分数
        "f173": "roe",             # ROE（%）— 已经是百分数
        "f184": "revenue",         # 营业总收入（原始单位）
        "f185": "net_profit",      # 净利润（原始单位）
        "f92": "total_shares",     # 总股本（原始单位）
        "f105": "float_shares",    # 流通股本（原始单位）
        "f162": "eps",             # 每股收益
        "f59": "navps",            # 每股净资产
        "f183": "pe_dynamic",      # PE(动)
        "f116": "retained_eps",    # 每股未分配利润
        "f189": "list_date",       # 上市日期（YYYYMMDD 整数，如 20210820）
        "f57": "total_market_cap", # 总市值（原始单位）
        "f107": "float_market_cap",# 流通市值（原始单位）
        "f85": "revenue_yoy",      # 营收同比（原始单位）
        "f117": "profit_yoy",      # 净利润同比（原始单位）
    }

    # stock/get 返回值已为展示单位，不做转换
    DIVIDE_BY_10000 = set()
    PERCENT_FIELDS = set()

    def __init__(self, cookie: Optional[str] = None):
        self.base_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://quote.eastmoney.com/",
        }
        self.cookie = cookie or generate_eastmoney_cookie_str()

    def _build_params(self, market: str, stock_code: str) -> Dict[str, Any]:
        """构建请求参数"""
        cb = f"jQuery{random.randint(1000000000, 9999999999)}_{int(time.time()*1000)}"
        return {
            "invt": "2",
            "fltt": "1",
            "cb": cb,
            "fields": ",".join(self.FIELD_MAP.keys()),
            "secid": f"{market}.{stock_code}",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "wbp2u": "|0|0|0|web",
            "dect": "1",
            "_": str(int(time.time() * 1000)),
        }

    def _convert_value(self, value, field_name: str):
        """将原始值转换为合适的单位，字符串字段原样返回"""
        # 字符串字段原样返回
        if isinstance(value, str) and field_name == "stock_name":
            return value

        # list_date: f189 是 YYYYMMDD 整数，转为日期字符串
        if field_name == "list_date":
            try:
                ds = str(int(float(str(value))))
                if len(ds) == 8:
                    return f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}"
            except (ValueError, TypeError):
                pass
            return str(value)
        if value is None:
            return None
        try:
            val = float(value)
        except (ValueError, TypeError):
            return value  # 非数值字段原样返回

        # 市值/营收/净利润：东财返回的是"万元"，转为"亿元"
        if field_name in self.DIVIDE_BY_10000:
            return val / 10000.0

        # 百分比字段：东财返回的是"万分之一"，转为"%"（除以 100）
        if field_name in self.PERCENT_FIELDS:
            return val / 100.0

        return val

    def _parse_response(self, content: str, market: str = "", stock_code: str = "") -> Optional[StockInfo]:
        """解析 JSONP 响应，返回 StockInfo 对象"""
        try:
            # 去除 JSONP 回调包装
            if content.startswith("jQuery") and content.endswith(");"):
                json_str = content[content.index("(") + 1 : content.rindex(")")]
            else:
                json_str = content

            data = json.loads(json_str)

            if data.get("rc") != 0:
                print(f"API 返回错误: rc={data.get('rc')}, msg={data.get('msg')}")
                return None

            # 获取数据对象
            raw_data = data.get("data", {})
            if not raw_data:
                return None

            # 解析字段（stock_code 和 market 由调用方传入，不从响应获取）
            stock_info = StockInfo(
                stock_code=stock_code,
                market=market,
            )

            # 映射各字段
            for field_id, attr_name in self.FIELD_MAP.items():
                raw_val = raw_data.get(field_id)
                if raw_val is not None and raw_val != "-":
                    converted = self._convert_value(raw_val, attr_name)
                    if converted is not None:
                        setattr(stock_info, attr_name, converted)

            return stock_info

        except Exception as e:
            print(f"解析响应失败: {e}")
            return None

    async def fetch_stock_info_async(
        self,
        market: str,
        stock_code: str,
        fallback_cookies: list = None,
    ) -> Optional[StockInfo]:
        """
        异步获取个股核心数据
        :param market: 市场代码
        :param stock_code: 6 位股票代码
        :param fallback_cookies: 备用 Cookie 列表（从 DB 获取，失败时兜底）
        :return: StockInfo 对象，失败返回 None
        """
        if fallback_cookies is None:
            fallback_cookies = []
        params = self._build_params(market, stock_code)
        self.last_used_cookie = None

        async def _try_once(cookie: str = None):
            """单次请求，成功返回 StockInfo，网络异常直接抛出，其他失败返回 None"""
            headers = dict(self.base_headers)
            if cookie:
                headers["Cookie"] = cookie
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        return self._parse_response(text, market=market, stock_code=stock_code)
                    else:
                        print(f"HTTP {resp.status}")
            return None

        # 单数次 (第1,3,5...次) = 完整 Cookie，双数次 (第2,4,6...次) = 简化 + 兜底
        all_fallback = fallback_cookies + [SEED_COOKIE]
        total_attempts = (MAX_RETRIES + 1) + len(all_fallback)
        fallback_idx = 0

        for attempt in range(total_attempts):
            cookie = None
            if attempt % 2 == 0:
                # 单数次: 完整 Cookie — qgqp_b_id 用 20 位数字
                try:
                    self.cookie = generate_eastmoney_cookie_str()
                except Exception:
                    self.cookie = f"retry_{attempt}"
                cookie = self.cookie
            else:
                # 双数次: 简化 Cookie — qgqp_b_id 用 hex
                try:
                    cookie = _generate_simple_cookie()
                except Exception:
                    cookie = None
                if not cookie and fallback_idx < len(all_fallback):
                    cookie = all_fallback[fallback_idx]
                    fallback_idx += 1

            try:
                result = await _try_once(cookie)
                if result is not None:
                    self.last_used_cookie = cookie
                    return result
            except aiohttp.ClientError as e:
                if _is_connection_error(e) and attempt < total_attempts - 1:
                    wait = RETRY_DELAY_MIN + random.random() * (RETRY_DELAY_MAX - RETRY_DELAY_MIN)
                    print(f"连接错误 ({e})，重试 {stock_code} ({attempt + 1}/{total_attempts})...")
                    await asyncio.sleep(wait)
                    continue
                print(f"请求核心数据失败 {stock_code}: {e}")
            except Exception as e:
                print(f"请求核心数据失败 {stock_code}: {e}")

        return None

    def fetch_stock_info(
        self,
        market: str,
        stock_code: str,
        fallback_cookies: list = None,
    ) -> Optional[StockInfo]:
        """同步获取个股核心数据（包装异步方法）"""
        return asyncio.run(self.fetch_stock_info_async(market, stock_code, fallback_cookies))
