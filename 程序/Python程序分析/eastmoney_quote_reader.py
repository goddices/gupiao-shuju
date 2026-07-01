import asyncio
import aiohttp
import json
import random
import secrets
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterable
from dataclasses import dataclass
from decimal import Decimal

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


class Market:
    """市场类型枚举"""

    SHANGHAI = "1"  # 上海证券交易所
    SHENGZHEN = "0"  # 深圳证券交易所


class AdjustPriceType:
    """复权类型枚举"""

    NONE = 0  # 不复权
    FORWARD = 1  # 前复权
    BACKWARD = 2  # 后复权


class PeriodType:
    """周期类型枚举"""

    UNSET = 0  # 未设置
    DAILY = 101  # 日线
    WEEKLY = 102  # 周线
    MONTHLY = 103  # 月线
    MINUTE_1 = 1  # 1分钟
    MINUTE_5 = 5  # 5分钟
    MINUTE_15 = 15  # 15分钟
    MINUTE_30 = 30  # 30分钟
    MINUTE_60 = 60  # 60分钟


class StockQuoteLine:
    """股票行情K线数据"""

    def __init__(
        self,
        trade_date: datetime,
        open_price: float,
        close_price: float,
        high_price: float,
        low_price: float,
        trade_volume: float,
        trade_amount: float,
    ):
        self.trade_date = trade_date
        self.open = open_price
        self.close = close_price
        self.high = high_price
        self.low = low_price
        self.volume = trade_volume
        self.amount = trade_amount

    def __repr__(self):
        return (
            f"StockQuoteLine(date={self.trade_date}, open={self.open}, close={self.close}, "
            f"high={self.high}, low={self.low}, volume={self.volume}, amount={self.amount})"
        )


class StockQuote:
    """股票行情数据"""

    def __init__(
        self,
        stock_name: str,
        quote_lines: List[StockQuoteLine],
        period_type: PeriodType,
    ):
        self.stock_name = stock_name
        self.quote_lines = quote_lines
        self.period_type = period_type

    def __repr__(self):
        return (
            f"StockQuote(stock_name={self.stock_name}, period_type={self.period_type}, "
            f"lines_count={len(self.quote_lines)})"
        )


class QuoteMappers:
    """行情数据映射器"""

    @staticmethod
    def get_adjust_price_parameter_value(adjust_type: AdjustPriceType) -> int:
        """
        获取复权类型对应的参数值
        :param adjust_type: 复权类型
        :return: 对应的参数值
        """
        return adjust_type

    @staticmethod
    def get_period_type_param_value(period_type: PeriodType) -> int:
        """
        获取周期类型对应的参数值
        :param period_type: 周期类型
        :return: 对应的参数值
        """
        return period_type


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
        raw = raw[:pos] + "-" + raw[pos + 1 :]
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


class EastmoneyQuoteReader:
    """东方财富行情数据读取器"""

    def __init__(self, mappers: QuoteMappers = None, cookie: str = None):
        """
        初始化行情读取器
        :param mappers: 映射器实例，默认为QuoteMappers()
        :param cookie: 请求Cookie，默认为DEFAULT_COOKIE
        """
        self.mappers = mappers or QuoteMappers()
        self.base_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        self.cookie = cookie or generate_eastmoney_cookie_str()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://quote.eastmoney.com/",
            "Cookie": self.cookie,
        }

    async def read_quote_async(
        self,
        market: str,
        stock_code: str,
        adjust_type: AdjustPriceType,
        period_type: PeriodType,
        end_date: str = "20500101",
        limit: int = 744,
        token: Any = None,
    ) -> Optional[StockQuote]:
        """
        异步获取股票行情数据

        :param market: 市场代码，使用Market类枚举
        :param stock_code: 股票代码
        :param adjust_type: 复权类型，使用AdjustPriceType类枚举
        :param period_type: 周期类型，使用PeriodType类枚举
        :param end_date: 结束日期，格式：YYYYMMDD，默认为20500101
        :param limit: 数据条数限制，默认为744
        :param token: 取消令牌，目前未实现
        :return: 股票行情数据，获取失败返回None
        """
        # 生成随机字符串
        random_str = f"jQuery3510{random.randint(100000000, 999999999)}_171{random.randint(1000000, 9999999)}"

        # 获取映射参数
        fqt = self.mappers.get_adjust_price_parameter_value(adjust_type)
        klt = self.mappers.get_period_type_param_value(period_type)

        # 构建请求URL
        params = {
            "cb": random_str,
            "secid": f"{market}.{stock_code}",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": fqt,
            "end": end_date,
            "lmt": limit,
            "_": str(int(datetime.now().timestamp() * 1000)),
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                # Cookie 策略: 第一次调用有1/3概率不带Cookie; 重试时换新Cookie
                headers = dict(self.headers)
                if attempt == 0:
                    if random.random() < 1 / 3:
                        headers.pop("Cookie", None)
                else:
                    new_cookie = generate_eastmoney_cookie_str()
                    headers["Cookie"] = new_cookie
                    self.headers["Cookie"] = new_cookie  # 更新实例headers以便后续复用

                # 发送HTTP请求
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            content = await response.text()

                            # 处理响应内容，移除JSONP包装
                            if content.startswith(random_str) and content.endswith(
                                ");"
                            ):
                                json_content = content[len(random_str) + 1 : -2]
                                return self._convert_quote(json_content, period_type)
                        else:
                            print(f"HTTP {response.status}，准备重试...")

            except aiohttp.ClientError as e:
                if _is_connection_error(e) and attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_MIN + random.random() * (
                        RETRY_DELAY_MAX - RETRY_DELAY_MIN
                    )
                    print(
                        f"连接错误 ({e})，正在重试 (第{attempt + 1}/{MAX_RETRIES}次)..."
                    )
                    await asyncio.sleep(wait)
                    continue
                print(f"获取行情数据失败: {e}")
            except Exception as e:
                print(f"获取行情数据失败: {e}")

        return None

    async def read_quote_from_stream_async(
        self, stream: Any, token: Any = None
    ) -> Optional[StockQuote]:
        """
        从流中读取行情数据（模拟C#方法，实际使用较少）

        :param stream: 数据流对象
        :param token: 取消令牌，目前未实现
        :return: 股票行情数据，获取失败返回None
        """
        try:
            content = await stream.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            return self._convert_quote(content)
        except Exception as e:
            print(f"从流中读取行情数据失败: {e}")

        return None

    def _convert_quote(
        self, content: str, period_type: PeriodType = PeriodType.UNSET
    ) -> Optional[StockQuote]:
        """
        转换行情数据格式

        :param content: JSON格式的行情数据
        :param period_type: 周期类型
        :return: 转换后的股票行情数据，转换失败返回None
        """
        try:
            # 解析JSON
            data = json.loads(content)

            if data.get("rc") == 0 and data.get("data") and data["data"].get("klines"):
                # 获取股票名称
                stock_name = data["data"].get("name", "未知股票")

                # 解析K线数据
                klines = data["data"]["klines"]
                quote_lines = []

                for line in klines:
                    quote_line = self._read_line(line)
                    if quote_line:
                        quote_lines.append(quote_line)

                # 按交易日排序
                quote_lines.sort(key=lambda x: x.trade_date)

                return StockQuote(
                    stock_name=stock_name,
                    quote_lines=quote_lines,
                    period_type=period_type,
                )
        except Exception as e:
            print(f"转换行情数据失败: {e}")

        return None

    def _read_line(self, content: str) -> Optional[StockQuoteLine]:
        """
        解析单条K线数据

        :param content: 单条K线数据字符串，格式：日期,开盘价,收盘价,最高价,最低价,成交量,成交额
        :return: 解析后的K线数据，解析失败返回None
        """
        try:
            data = content.split(",")
            if len(data) < 7:
                return None

            return StockQuoteLine(
                trade_date=datetime.strptime(data[0], "%Y-%m-%d"),
                open_price=float(data[1]),
                close_price=float(data[2]),
                high_price=float(data[3]),
                low_price=float(data[4]),
                trade_volume=float(data[5]),
                trade_amount=float(data[6]),
            )
        except Exception as e:
            print(f"解析K线数据失败: {e}")

        return None

    def read_quote(
        self,
        market: str,
        stock_code: str,
        adjust_type: AdjustPriceType,
        period_type: PeriodType,
        end_date: str = "20500101",
        limit: int = 744,
    ) -> Optional[StockQuote]:
        """
        同步获取股票行情数据（包装异步方法）

        :param market: 市场代码，使用Market类枚举
        :param stock_code: 股票代码
        :param adjust_type: 复权类型，使用AdjustPriceType类枚举
        :param period_type: 周期类型，使用PeriodType类枚举
        :param end_date: 结束日期，格式：YYYYMMDD，默认为20500101
        :param limit: 数据条数限制，默认为744
        :return: 股票行情数据，获取失败返回None
        """
        return asyncio.run(
            self.read_quote_async(
                market, stock_code, adjust_type, period_type, end_date, limit
            )
        )


class EastmoneyStockListReader:
    """
    东方财富股票列表读取器（异步）
    用于获取全市场股票基本信息（代码、名称、价格、涨跌幅等）
    """

    BASE_URL = "https://push2.eastmoney.com/api/qt/clist/get"

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

    def _build_params(self, fs: str, page: int, size: int = 100) -> Dict[str, Any]:
        """
        构建请求参数
        :param fs: 板块过滤条件（如 'm:0+t:6,m:0+t:80,...'）
        :param page: 页码（从1开始）
        :param size: 每页数量（最大通常为100）
        """
        cb = f"jQuery{random.randint(1000000000, 9999999999)}_{int(time.time()*1000)}"
        return {
            "fltt": "1",
            "invt": "2",
            "wbp2u": "|0|0|0|web",
            "cb": cb,
            "fields": "f12,f13,f14,f1,f2,f4,f11,f152",  # 代码,市场,名称,最新价,涨跌幅,涨跌额,成交量,市盈率
            "fs": fs,
            "ut": "433fd2d0e98eaf36ad3d5001f088614d",
            "fid": "f11",
            "po": "1",
            "pn": str(page),
            "np": "1",
            "pz": str(size),
            "dect": "1",
            "_": str(int(time.time() * 1000)),
        }

    async def fetch_page(
        self,
        session: aiohttp.ClientSession,
        fs: str,
        page: int,
        size: int = 100,
        skip_first_cookie: bool = False,
    ) -> Optional[List[Dict]]:
        """
        异步获取单页股票列表
        :param skip_first_cookie: 第一次尝试是否跳过Cookie
        :return: 解析后的列表（每个元素为 dict），若失败或无数据返回 None
        """
        params = self._build_params(fs, page, size)
        cb = params["cb"]

        for attempt in range(MAX_RETRIES + 1):
            try:
                # Cookie 策略: 第一次调用有1/3概率不带Cookie; 重试时换新Cookie
                req_headers = dict(self.base_headers)
                if attempt == 0:
                    if not skip_first_cookie:
                        req_headers["Cookie"] = self.cookie
                else:
                    self.cookie = generate_eastmoney_cookie_str()
                    req_headers["Cookie"] = self.cookie

                async with session.get(
                    self.BASE_URL, params=params, headers=req_headers
                ) as resp:
                    if resp.status != 200:
                        print(f"HTTP {resp.status} on page {page}")
                        if attempt < MAX_RETRIES:
                            continue
                        return None
                    text = await resp.text()

                    if text.startswith(cb) and text.endswith(");"):
                        json_str = text[len(cb) + 1 : -2]
                    else:
                        json_str = text

                    data = json.loads(json_str)
                    if data.get("rc") != 0:
                        print(
                            f"API 返回错误 rc={data.get('rc')}, msg={data.get('msg')}"
                        )
                        return None

                    diff = data.get("data", {}).get("diff", [])
                    if not diff:
                        return None

                    parsed = []
                    for item in diff:
                        parsed.append(
                            {
                                "code": item.get("f12"),
                                "market": item.get("f13"),
                                "name": item.get("f14"),
                                "price": item.get("f1"),
                                "change_pct": item.get("f2"),
                                "change_amount": item.get("f4"),
                                "volume": item.get("f11"),
                                "pe": item.get("f152"),
                            }
                        )
                    return parsed

            except aiohttp.ClientError as e:
                if _is_connection_error(e) and attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_MIN + random.random() * (
                        RETRY_DELAY_MAX - RETRY_DELAY_MIN
                    )
                    print(
                        f"连接错误 ({e})，正在重试页面{page} (第{attempt + 1}/{MAX_RETRIES}次)..."
                    )
                    await asyncio.sleep(wait)
                    continue
                print(f"Error fetching page {page}: {e}")
                return None
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                return None

        return None

    async def fetch_all_stocks(
        self, fs: str, size: int = 100, max_pages: int = 200
    ) -> List[Dict]:
        """
        循环获取所有股票（直到某页无数据或达到最大页数）
        :param fs: 板块过滤条件
        :param size: 每页大小（默认100，东方财富最大通常为100）
        :param max_pages: 最大页数，防止死循环
        :return: 所有股票的列表
        """
        all_stocks = []
        page = 1

        async with aiohttp.ClientSession(headers=self.base_headers) as session:
            while page <= max_pages:
                print(f"正在获取第 {page} 页...")
                # 第一页第一次调用有1/3概率不带Cookie
                skip_cookie = page == 1 and random.random() < 1 / 3
                page_data = await self.fetch_page(
                    session, fs, page, size, skip_first_cookie=skip_cookie
                )
                if not page_data:
                    print("无数据，停止翻页")
                    break
                all_stocks.extend(page_data)
                if len(page_data) < size:
                    print("已获取最后一页")
                    break
                page += 1

        print(f"共获取 {len(all_stocks)} 条股票记录")
        return all_stocks


@dataclass
class StockInfo:
    """个股核心数据"""

    stock_code: str
    market: str
    stock_name: Optional[str] = None  # f58: 股票名称
    # 基础数据
    total_market_cap: Optional[float] = None  # f190: 总市值
    float_market_cap: Optional[float] = None  # f189: 流通市值
    eps: Optional[float] = None  # f162: 每股收益
    pe_static: Optional[float] = None  # f152: 静态市盈率
    pb_old: Optional[float] = None  # f167: 市净率（旧）
    total_shares: Optional[float] = None  # f92: 总股本
    navps: Optional[float] = None  # f59: 每股净资产
    pe_dynamic_raw: Optional[float] = None  # f183: 动态市盈率原始值
    revenue_raw: Optional[float] = None  # f184: 营业总收入原始值
    float_shares: Optional[float] = None  # f105: 流通股本
    net_profit_raw: Optional[float] = None  # f185: 净利润原始值
    gross_margin: Optional[float] = None  # f186: 毛利率（%）
    net_margin: Optional[float] = None  # f187: 净利率（%）
    roe: Optional[float] = None  # f173: ROE（%）
    debt_ratio: Optional[float] = None  # f188: 资产负债率（%）
    list_date: Optional[str] = None  # f189: 上市日期（从原始时间戳转换）
    retained_eps_raw: Optional[float] = None  # f116: 每股未分配利润原始值
    revenue_yoy_raw: Optional[float] = None  # f85: 营收同比增长原始值
    profit_yoy_raw: Optional[float] = None  # f117: 净利润同比增长原始值
    pb: Optional[float] = None  # f62: 市净率（新版）
    change_pct: Optional[float] = None  # f55: 涨跌幅（%）


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


# 示例用法
if __name__ == "__main__":
    # 创建行情读取器实例
    reader = EastmoneyQuoteReader()

    # 示例1：同步获取上证指数日线数据
    print("正在获取上证指数日线数据...")
    quote = reader.read_quote(
        market=Market.SHANGHAI,
        stock_code="000001",
        adjust_type=AdjustPriceType.FORWARD,
        period_type=PeriodType.DAILY,
        limit=100,
    )

    if quote:
        print(f"获取成功：{quote}")
        print(f"第一条数据：{quote.quote_lines[0]}")
        print(f"最后一条数据：{quote.quote_lines[-1]}")
    else:
        print("获取失败")

    # 示例2：异步获取中国石油周线数据
    async def async_example():
        print("\n正在异步获取中国石油周线数据...")
        quote = await reader.read_quote_async(
            market=Market.SHANGHAI,
            stock_code="601857",
            adjust_type=AdjustPriceType.FORWARD,
            period_type=PeriodType.WEEKLY,
            limit=50,
        )

        if quote:
            print(f"获取成功：{quote}")
            print(f"第一条数据：{quote.quote_lines[0]}")
            print(f"最后一条数据：{quote.quote_lines[-1]}")
        else:
            print("获取失败")

    asyncio.run(async_example())
