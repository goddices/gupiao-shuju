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

from emdata.config import MAX_RETRIES, RETRY_DELAY_MIN, RETRY_DELAY_MAX, _is_connection_error
from emdata.models import StockInfo
from emdata.cookie import generate_eastmoney_cookie_str


class EastmoneyCurrentCoreDataReader:
    """
    东方财富个股核心数据读取器（异步）
    获取 ROE、PE、每股收益、市值等核心财务指标
    """

    BASE_URL = "https://push2.eastmoney.com/api/qt/stock/get"

    # 字段映射表（stock/get 端点专用字段 ID）
    # 注意: stock/get 和 clist/get 的字段 ID 含义不同！
    FIELD_MAP = {
        "f58": "stock_name",       # 股票名称
        "f55": "change_pct",       # 涨跌幅（%）
        "f62": "pb",               # 市净率
        "f186": "gross_margin",    # 毛利率（%）- 已为百分比无需转换
        "f187": "net_margin",      # 净利率（%）- 已为百分比无需转换
        "f188": "debt_ratio",      # 资产负债率（%）- 已为百分比无需转换
        "f173": "roe",             # ROE（%）- 已为百分比无需转换
    }

    # 不需要额外单位转换 —— stock/get 返回的数据已经是展示单位
    DIVIDE_BY_10000 = set()

    # 百分比字段不需要除以 100 —— stock/get 返回的百分比值已经是百分数
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
        # 额外请求 f189（上市日期）用于特殊解析
        extra_fields = ["f189"]
        all_fields = list(self.FIELD_MAP.keys()) + extra_fields
        return {
            "invt": "2",
            "fltt": "1",
            "cb": cb,
            "fields": ",".join(all_fields),
            "secid": f"{market}.{stock_code}",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "wbp2u": "|0|0|0|web",
            "dect": "1",
            "_": str(int(time.time() * 1000)),
        }

    def _convert_value(self, value, field_name: str):
        """将原始值转换为合适的单位，字符串字段原样返回"""
        # 字符串字段（如 stock_name）原样返回
        if isinstance(value, str) and field_name == "stock_name":
            return value
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

            # 特殊处理: 上市日期从 f189 转换 (原始值为 YYYYMMDD 格式整数, 如 20071105)
            raw_date = raw_data.get("f189")
            if raw_date is not None and raw_date != "-":
                try:
                    date_str = str(int(float(str(raw_date))))
                    if len(date_str) == 8:
                        stock_info.list_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                except (ValueError, TypeError):
                    pass

            return stock_info

        except Exception as e:
            print(f"解析响应失败: {e}")
            return None

    async def fetch_stock_info_async(
        self,
        market: str,
        stock_code: str,
    ) -> Optional[StockInfo]:
        """
        异步获取个股核心数据
        :param market: 市场代码（"1"=上海, "0"=深圳，与 Market 枚举一致）
        :param stock_code: 6 位股票代码
        :return: StockInfo 对象，失败返回 None
        """
        params = self._build_params(market, stock_code)

        for attempt in range(MAX_RETRIES + 1):
            try:
                # Cookie 策略: 第一次调用有1/3概率不带Cookie; 重试时换新Cookie
                headers = dict(self.base_headers)
                if attempt == 0:
                    if random.random() < 1 / 3:
                        pass  # 不带 Cookie
                    else:
                        headers["Cookie"] = self.cookie
                else:
                    self.cookie = generate_eastmoney_cookie_str()
                    headers["Cookie"] = self.cookie

                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(self.BASE_URL, params=params) as resp:
                        if resp.status != 200:
                            print(f"HTTP {resp.status} for {stock_code}")
                            if attempt < MAX_RETRIES:
                                continue
                            return None
                        text = await resp.text()
                        return self._parse_response(text, market=market, stock_code=stock_code)

            except aiohttp.ClientError as e:
                if _is_connection_error(e) and attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_MIN + random.random() * (RETRY_DELAY_MAX - RETRY_DELAY_MIN)
                    print(f"连接错误 ({e})，正在重试核心数据 {stock_code} (第{attempt + 1}/{MAX_RETRIES}次)...")
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
    ) -> Optional[StockInfo]:
        """同步获取个股核心数据（包装异步方法）"""
        return asyncio.run(self.fetch_stock_info_async(market, stock_code))
