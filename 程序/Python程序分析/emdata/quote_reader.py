"""
东方财富行情K线数据读取器
"""
import asyncio
import aiohttp
import json
import random
from datetime import datetime
from typing import Optional, Any

from emdata.config import MAX_RETRIES, RETRY_DELAY_MIN, RETRY_DELAY_MAX, _is_connection_error
from emdata.enums import AdjustPriceType, PeriodType
from emdata.models import StockQuoteLine, StockQuote, QuoteMappers
from emdata.cookie import generate_eastmoney_cookie_str


class EastmoneyQuoteReader:
    """东方财富行情数据读取器"""

    def __init__(self, mappers: QuoteMappers = None, cookie: str = None):
        """
        初始化行情读取器
        :param mappers: 映射器实例，默认为QuoteMappers()
        :param cookie: 请求Cookie
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
                            if content.startswith(random_str) and content.endswith(");"):
                                json_content = content[len(random_str) + 1 : -2]
                                return self._convert_quote(json_content, period_type)
                        else:
                            print(f"HTTP {response.status}，准备重试...")

            except aiohttp.ClientError as e:
                if _is_connection_error(e) and attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_MIN + random.random() * (RETRY_DELAY_MAX - RETRY_DELAY_MIN)
                    print(f"连接错误 ({e})，正在重试 (第{attempt + 1}/{MAX_RETRIES}次)...")
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
        """
        return asyncio.run(
            self.read_quote_async(
                market, stock_code, adjust_type, period_type, end_date, limit
            )
        )
