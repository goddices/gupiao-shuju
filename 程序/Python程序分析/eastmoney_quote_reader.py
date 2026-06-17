import asyncio
import aiohttp
import json
import random
import secrets
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterable


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
    def __init__(self, trade_date: datetime, open_price: float, close_price: float, 
                 high_price: float, low_price: float, trade_volume: float, trade_amount: float):
        self.trade_date = trade_date
        self.open = open_price
        self.close = close_price
        self.high = high_price
        self.low = low_price
        self.volume = trade_volume
        self.amount = trade_amount
    
    def __repr__(self):
        return f"StockQuoteLine(date={self.trade_date}, open={self.open}, close={self.close}, " \
               f"high={self.high}, low={self.low}, volume={self.volume}, amount={self.amount})"


class StockQuote:
    """股票行情数据"""
    def __init__(self, stock_name: str, quote_lines: List[StockQuoteLine], period_type: PeriodType):
        self.stock_name = stock_name
        self.quote_lines = quote_lines
        self.period_type = period_type
    
    def __repr__(self):
        return f"StockQuote(stock_name={self.stock_name}, period_type={self.period_type}, " \
               f"lines_count={len(self.quote_lines)})"


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

    # 辅助：生成32位十六进制随机串
    def random_hex32():
        return secrets.token_hex(16)

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

    # 构建 Cookie 字典
    cookies = {
        # 固定值
        "fullscreengg": "1",
        "fullscreengg2": "1",
        "st_asi": "delete",
        # 随机ID（每次不同）
        "qgqp_b_id": random_hex32(),
        "nid18": random_hex32(),
        "st_nvi": random_alnum(24),
        "gviem": random_alnum(24),
        # 时间戳
        "nid18_create_time": str(current_ms),
        "gviem_create_time": str(current_ms),
        "websitepoptg_api_time": str(current_ms),
        "st_sp": current_time_str,
        # 会话信息
        "st_psi": gen_st_psi(),
        "st_pvi": str(random.randint(10000000000000, 99999999999999)),
        "st_si": str(random.randint(10000000000000, 99999999999999)),
        "st_sn": "1",  # 初始步数
        "st_inirUrl": "https%3A%2F%2Fwww.eastmoney.com%2F",
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
    
    async def read_quote_async(self, market: str, stock_code: str, adjust_type: AdjustPriceType, 
                               period_type: PeriodType, end_date: str = "20500101", 
                               limit: int = 744, token: Any = None) -> Optional[StockQuote]:
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
        try:
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
                "_": str(int(datetime.now().timestamp() * 1000))
            }
            
            # 发送HTTP请求
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # 处理响应内容，移除JSONP包装
                        if content.startswith(random_str) and content.endswith(");"):
                            json_content = content[len(random_str) + 1:-2]
                            return self._convert_quote(json_content, period_type)
        except Exception as e:
            print(f"获取行情数据失败: {e}")
        
        return None
    
    async def read_quote_from_stream_async(self, stream: Any, token: Any = None) -> Optional[StockQuote]:
        """
        从流中读取行情数据（模拟C#方法，实际使用较少）
        
        :param stream: 数据流对象
        :param token: 取消令牌，目前未实现
        :return: 股票行情数据，获取失败返回None
        """
        try:
            content = await stream.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            return self._convert_quote(content)
        except Exception as e:
            print(f"从流中读取行情数据失败: {e}")
        
        return None
    
    def _convert_quote(self, content: str, period_type: PeriodType = PeriodType.UNSET) -> Optional[StockQuote]:
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
                    period_type=period_type
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
            data = content.split(',')
            if len(data) < 7:
                return None
            
            return StockQuoteLine(
                trade_date=datetime.strptime(data[0], "%Y-%m-%d"),
                open_price=float(data[1]),
                close_price=float(data[2]),
                high_price=float(data[3]),
                low_price=float(data[4]),
                trade_volume=float(data[5]),
                trade_amount=float(data[6])
            )
        except Exception as e:
            print(f"解析K线数据失败: {e}")
        
        return None
    
    def read_quote(self, market: str, stock_code: str, adjust_type: AdjustPriceType, 
                   period_type: PeriodType, end_date: str = "20500101", 
                   limit: int = 744) -> Optional[StockQuote]:
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
        return asyncio.run(self.read_quote_async(market, stock_code, adjust_type, 
                                                period_type, end_date, limit))


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
        limit=100
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
            limit=50
        )
        
        if quote:
            print(f"获取成功：{quote}")
            print(f"第一条数据：{quote.quote_lines[0]}")
            print(f"最后一条数据：{quote.quote_lines[-1]}")
        else:
            print("获取失败")
    
    asyncio.run(async_example())
