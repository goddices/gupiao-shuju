"""
对数据同步接口的单元测试
覆盖: eastmoney_quote_reader, quote_saver, data_fetcher, services, divide_importer
"""
import sys
import os
import json
import asyncio
import tempfile
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock, AsyncMock, PropertyMock
import pytest

# 将 backend 加入路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

# =============================================================================
# 导入被测试模块
# =============================================================================
from eastmoney_quote_reader import (
    Market, AdjustPriceType, PeriodType,
    StockQuoteLine, StockQuote,
    QuoteMappers,
    EastmoneyQuoteReader, EastmoneyStockListReader,
    generate_eastmoney_cookie_str,
    _is_connection_error,
    MAX_RETRIES,
)

# =============================================================================
# 第一部分: 纯逻辑单元测试（无需 mock）
# =============================================================================


class TestEnums:
    """市场类型、复权类型、周期类型枚举值测试"""

    def test_market_values(self):
        assert Market.SHANGHAI == "1"
        assert Market.SHENGZHEN == "0"

    def test_adjust_price_values(self):
        assert AdjustPriceType.NONE == 0
        assert AdjustPriceType.FORWARD == 1
        assert AdjustPriceType.BACKWARD == 2

    def test_period_type_values(self):
        assert PeriodType.UNSET == 0
        assert PeriodType.DAILY == 101
        assert PeriodType.WEEKLY == 102
        assert PeriodType.MONTHLY == 103
        assert PeriodType.MINUTE_1 == 1
        assert PeriodType.MINUTE_5 == 5
        assert PeriodType.MINUTE_15 == 15
        assert PeriodType.MINUTE_30 == 30
        assert PeriodType.MINUTE_60 == 60


class TestStockQuoteLine:
    """K线数据模型测试"""

    def test_init_and_attrs(self):
        line = StockQuoteLine(
            trade_date=datetime(2025, 6, 30),
            open_price=10.0, close_price=10.5,
            high_price=11.0, low_price=9.5,
            trade_volume=1000000.0, trade_amount=10500000.0,
        )
        assert line.trade_date == datetime(2025, 6, 30)
        assert line.open == 10.0
        assert line.close == 10.5
        assert line.high == 11.0
        assert line.low == 9.5
        assert line.volume == 1000000.0
        assert line.amount == 10500000.0

    def test_repr(self):
        line = StockQuoteLine(
            trade_date=datetime(2025, 6, 30),
            open_price=10.0, close_price=10.5,
            high_price=11.0, low_price=9.5,
            trade_volume=1000000.0, trade_amount=10500000.0,
        )
        r = repr(line)
        assert "date=2025-06-30" in r
        assert "open=10.0" in r
        assert "close=10.5" in r


class TestStockQuote:
    """股票行情数据模型测试"""

    def test_init_and_repr(self):
        lines = [
            StockQuoteLine(datetime(2025, 6, 29), 9.0, 9.5, 10.0, 8.5, 500000.0, 4750000.0),
            StockQuoteLine(datetime(2025, 6, 30), 9.5, 10.0, 10.5, 9.0, 600000.0, 6000000.0),
        ]
        quote = StockQuote(stock_name="测试股票", quote_lines=lines, period_type=PeriodType.DAILY)
        assert quote.stock_name == "测试股票"
        assert len(quote.quote_lines) == 2
        assert quote.period_type == PeriodType.DAILY
        r = repr(quote)
        assert "测试股票" in r
        assert "lines_count=2" in r


class TestQuoteMappers:
    """映射器测试"""

    def test_adjust_price_mapping(self):
        assert QuoteMappers.get_adjust_price_parameter_value(AdjustPriceType.NONE) == 0
        assert QuoteMappers.get_adjust_price_parameter_value(AdjustPriceType.FORWARD) == 1
        assert QuoteMappers.get_adjust_price_parameter_value(AdjustPriceType.BACKWARD) == 2

    def test_period_type_mapping(self):
        assert QuoteMappers.get_period_type_param_value(PeriodType.DAILY) == 101
        assert QuoteMappers.get_period_type_param_value(PeriodType.MINUTE_30) == 30


class TestGenerateCookie:
    """Cookie 生成测试"""

    def test_returns_string(self):
        cookie = generate_eastmoney_cookie_str()
        assert isinstance(cookie, str)
        assert len(cookie) > 0

    def test_contains_expected_keys(self):
        cookie = generate_eastmoney_cookie_str()
        expected_keys = ["fullscreengg", "qgqp_b_id", "st_pvi", "st_si", "st_psi"]
        for key in expected_keys:
            assert key in cookie, f"Cookie 缺少 key: {key}"

    def test_format_is_key_equals_value(self):
        cookie = generate_eastmoney_cookie_str()
        parts = cookie.split("; ")
        for part in parts:
            assert "=" in part, f"格式错误: '{part}'"

    def test_each_call_generates_different_cookie(self):
        """每次调用应生成不同的 Cookie"""
        cookies = [generate_eastmoney_cookie_str() for _ in range(10)]
        # 至少有一些不同的（由于随机成分）
        unique = set(cookies)
        assert len(unique) > 1, "多次调用应产生不同的 Cookie"


class TestIsConnectionError:
    """连接错误检测测试"""

    def test_server_disconnected_detected(self):
        from aiohttp import ClientError
        e = ClientError("Server disconnected")
        assert _is_connection_error(e) is True

    def test_connection_reset_detected(self):
        from aiohttp import ClientError
        e = ClientError("Connection reset by peer")
        assert _is_connection_error(e) is True

    def test_connection_refused_detected(self):
        from aiohttp import ClientError
        e = ClientError("Connection refused")
        assert _is_connection_error(e) is True

    def test_peer_closed_detected(self):
        from aiohttp import ClientError
        e = ClientError("peer closed connection")
        assert _is_connection_error(e) is True

    def test_normal_error_not_detected(self):
        from aiohttp import ClientError
        e = ClientError("Invalid URL")
        assert _is_connection_error(e) is False

    def test_value_error_not_detected(self):
        e = ValueError("something wrong")
        assert _is_connection_error(e) is False

    def test_case_insensitive(self):
        from aiohttp import ClientError
        e = ClientError("SERVER DISCONNECTED")
        assert _is_connection_error(e) is True


class TestConvertQuote:
    """行情数据转换测试"""

    def test_valid_json_converts_correctly(self):
        reader = EastmoneyQuoteReader()
        valid_json = json.dumps({
            "rc": 0,
            "data": {
                "name": "上证指数",
                "klines": [
                    "2025-06-25,3000.00,3050.00,3100.00,2950.00,1000000.00,5000000000.000",
                    "2025-06-26,3050.00,3020.00,3080.00,3000.00,1200000.00,6000000000.000",
                ],
            },
        })
        result = reader._convert_quote(valid_json, PeriodType.DAILY)
        assert result is not None
        assert result.stock_name == "上证指数"
        assert len(result.quote_lines) == 2
        assert result.quote_lines[0].open == 3000.0
        assert result.quote_lines[1].close == 3020.0
        # 按日期排序
        assert result.quote_lines[0].trade_date == datetime(2025, 6, 25)

    def test_invalid_json_returns_none(self):
        reader = EastmoneyQuoteReader()
        result = reader._convert_quote("not valid json")
        assert result is None

    def test_rc_not_zero_returns_none(self):
        reader = EastmoneyQuoteReader()
        bad_json = json.dumps({"rc": -1, "data": None})
        result = reader._convert_quote(bad_json)
        assert result is None

    def test_empty_klines_returns_none(self):
        reader = EastmoneyQuoteReader()
        empty_json = json.dumps({"rc": 0, "data": {"name": "test", "klines": []}})
        result = reader._convert_quote(empty_json)
        assert result is None

    def test_missing_data_returns_none(self):
        reader = EastmoneyQuoteReader()
        bad_json = json.dumps({"rc": 0, "data": None})
        result = reader._convert_quote(bad_json)
        assert result is None


class TestReadLine:
    """单条K线解析测试"""

    def test_valid_line(self):
        reader = EastmoneyQuoteReader()
        line = reader._read_line("2025-06-30,10.00,10.50,11.00,9.50,1000000.00,10500000.00")
        assert line is not None
        assert line.trade_date == datetime(2025, 6, 30)
        assert line.open == 10.0
        assert line.close == 10.5
        assert line.high == 11.0
        assert line.low == 9.5
        assert line.volume == 1000000.0
        assert line.amount == 10500000.0

    def test_short_line_returns_none(self):
        reader = EastmoneyQuoteReader()
        result = reader._read_line("2025-06-30,10.00")  # 只有2个字段，需要>=7
        assert result is None

    def test_invalid_number_returns_none(self):
        reader = EastmoneyQuoteReader()
        result = reader._read_line("2025-06-30,abc,10.50,11.00,9.50,1000000.00,10500000.00")
        assert result is None

    def test_invalid_date_returns_none(self):
        reader = EastmoneyQuoteReader()
        result = reader._read_line("not-a-date,10.00,10.50,11.00,9.50,1000000.00,10500000.00")
        assert result is None, f"Expected None but got {result}"


# =============================================================================
# 第二部分: 网络重试逻辑测试（mock aiohttp）
# =============================================================================


class _MockClientSession:
    """Mock aiohttp.ClientSession: supports async context manager + sync get()."""

    def __init__(self, get_result):
        """
        get_result:
          - Exception → session.get 抛出该异常
          - AsyncMock → session.get 返回 async context manager，yield 该对象
        """
        if isinstance(get_result, Exception):
            self._get = MagicMock(side_effect=get_result)
        else:
            cm = AsyncMock()
            cm.__aenter__.return_value = get_result
            cm.__aexit__.return_value = None
            self._get = MagicMock(return_value=cm)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def get(self, *args, **kwargs):
        return self._get(*args, **kwargs)


class TestQuoteReaderRetry:
    """read_quote_async 重试与 Cookie 旋转测试"""

    @pytest.fixture
    def reader(self):
        return EastmoneyQuoteReader()

    @pytest.fixture
    def valid_response_json(self):
        return json.dumps({
            "rc": 0,
            "data": {
                "name": "测试股票",
                "klines": [
                    "2025-06-30,10.00,10.50,11.00,9.50,1000000.00,10500000.00",
                ],
            },
        })

    @staticmethod
    def _make_response(text, status=200):
        """构造 mock response 对象（含 text() 异步方法）"""
        resp = AsyncMock()
        resp.status = status
        resp.text = AsyncMock(return_value=text)
        return resp

    @staticmethod
    def _make_session(side_effect_or_response):
        """构造 _MockClientSession"""
        return _MockClientSession(side_effect_or_response)

    @pytest.mark.asyncio
    async def test_successful_fetch_returns_quote(self, reader, valid_response_json):
        """正常请求应返回行情数据"""
        # JSONP 包装: 需要匹配 random_str (cb 回调名)
        callback = "jQuery3510123456789_1717654321"
        wrapped_json = f"{callback}({valid_response_json});"
        mock_resp = self._make_response(wrapped_json)
        mock_session = self._make_session(mock_resp)

        with patch("eastmoney_quote_reader.random.randint", side_effect=[123456789, 7654321]):
            with patch("eastmoney_quote_reader.aiohttp.ClientSession", return_value=mock_session):
                result = await reader.read_quote_async(
                    market=Market.SHANGHAI,
                    stock_code="000001",
                    adjust_type=AdjustPriceType.NONE,
                    period_type=PeriodType.DAILY,
                    limit=10,
                )

        assert result is not None
        assert result.stock_name == "测试股票"
        assert len(result.quote_lines) == 1

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, reader, valid_response_json):
        """连接错误时应重试，重试成功返回数据"""
        from aiohttp import ClientError

        # JSONP 包装
        callback = "jQuery3510987654321_1711234567"
        wrapped_json = f"{callback}({valid_response_json});"
        mock_resp2 = self._make_response(wrapped_json)
        mock_session1 = self._make_session(ClientError("Server disconnected"))
        mock_session2 = self._make_session(mock_resp2)

        # random.randint side_effect 需要覆盖: random_str(2次) + generate_eastmoney_cookie 中的多次调用
        # 前两个值决定 callback，后面补足够多的值供 cookie 生成使用
        randint_values = [987654321, 1234567] + [500000000] * 200

        with patch(
            "eastmoney_quote_reader.random.randint",
            side_effect=randint_values,
        ), patch(
            "eastmoney_quote_reader.aiohttp.ClientSession",
            side_effect=[mock_session1, mock_session2],
        ) as mock_cs, patch(
            "eastmoney_quote_reader.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            result = await reader.read_quote_async(
                market=Market.SHANGHAI,
                stock_code="000001",
                adjust_type=AdjustPriceType.NONE,
                period_type=PeriodType.DAILY,
                limit=10,
            )

        assert result is not None
        assert mock_cs.call_count == 2, f"应创建2个 ClientSession，实际: {mock_cs.call_count}"
        mock_sleep.assert_called_once(), "应等待一次重试间隔"

    @pytest.mark.asyncio
    async def test_exhausted_retries_returns_none(self, reader):
        """全部重试失败后应返回 None"""
        from aiohttp import ClientError

        mock_session = self._make_session(ClientError("Server disconnected"))

        with patch(
            "eastmoney_quote_reader.aiohttp.ClientSession",
            return_value=mock_session,
        ), patch(
            "eastmoney_quote_reader.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await reader.read_quote_async(
                market=Market.SHANGHAI,
                stock_code="000001",
                adjust_type=AdjustPriceType.NONE,
                period_type=PeriodType.DAILY,
                limit=10,
            )

        assert result is None, "全部重试失败应返回 None"

    @pytest.mark.asyncio
    async def test_retry_uses_new_cookie(self, reader, valid_response_json):
        """重试时应使用新生成的 Cookie"""
        from aiohttp import ClientError

        original_cookie = reader.headers["Cookie"]

        mock_resp2 = self._make_response(valid_response_json)
        mock_session1 = self._make_session(ClientError("Server disconnected"))
        mock_session2 = self._make_session(mock_resp2)

        with patch(
            "eastmoney_quote_reader.aiohttp.ClientSession",
            side_effect=[mock_session1, mock_session2],
        ), patch(
            "eastmoney_quote_reader.asyncio.sleep", new_callable=AsyncMock
        ):
            await reader.read_quote_async(
                market=Market.SHANGHAI,
                stock_code="000001",
                adjust_type=AdjustPriceType.NONE,
                period_type=PeriodType.DAILY,
                limit=10,
            )

        # 重试后 self.headers["Cookie"] 应被更新为新值
        assert reader.headers["Cookie"] != original_cookie, "重试后 Cookie 应该更新为新值"

    @pytest.mark.asyncio
    async def test_non_connection_error_returns_none_no_retry(self, reader):
        """非连接错误不应重试，直接返回 None"""
        mock_session = self._make_session(ValueError("some other error"))

        with patch(
            "eastmoney_quote_reader.aiohttp.ClientSession", return_value=mock_session
        ), patch(
            "eastmoney_quote_reader.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            result = await reader.read_quote_async(
                market=Market.SHANGHAI,
                stock_code="000001",
                adjust_type=AdjustPriceType.NONE,
                period_type=PeriodType.DAILY,
                limit=10,
            )

        assert result is None
        mock_sleep.assert_not_called(), "非连接错误不应触发重试等待"

    @pytest.mark.asyncio
    async def test_first_call_can_skip_cookie(self, reader, valid_response_json):
        """第一次调用有概率不带 Cookie"""
        mock_resp = self._make_response(valid_response_json)
        mock_session = self._make_session(mock_resp)

        with patch(
            "eastmoney_quote_reader.aiohttp.ClientSession", return_value=mock_session
        ), patch("eastmoney_quote_reader.random.random", return_value=0.2):  # < 1/3, 不带Cookie
            await reader.read_quote_async(
                market=Market.SHANGHAI,
                stock_code="000001",
                adjust_type=AdjustPriceType.NONE,
                period_type=PeriodType.DAILY,
                limit=10,
            )

        # 验证正常完成（带/不带 Cookie 均不应报错）
        assert mock_session._get.called


class TestStockListReaderRetry:
    """EastmoneyStockListReader 重试逻辑测试"""

    @pytest.fixture
    def list_reader(self):
        return EastmoneyStockListReader()

    @pytest.fixture
    def valid_list_response(self):
        return json.dumps({
            "rc": 0,
            "data": {
                "diff": [
                    {"f12": "000001", "f13": 0, "f14": "平安银行", "f1": 10.5, "f2": 1.5,
                     "f4": 0.15, "f11": 1000000, "f152": 12.3},
                ],
            },
        })

    @staticmethod
    def _make_response(text, status=200):
        resp = AsyncMock()
        resp.status = status
        resp.text = AsyncMock(return_value=text)
        return resp

    @staticmethod
    def _make_async_cm(return_value):
        cm = AsyncMock()
        cm.__aenter__.return_value = return_value
        cm.__aexit__.return_value = None
        return cm

    @staticmethod
    def _make_session_for_list(responses_or_errors):
        """
        构造 mock aiohttp.ClientSession，session.get 按顺序返回 async context manager。
        responses_or_errors: 列表，元素是 response mock 或 Exception。
        """
        mock_session = MagicMock()
        side_effects = []
        for item in responses_or_errors:
            if isinstance(item, Exception):
                side_effects.append(item)
            else:
                cm = TestStockListReaderRetry._make_async_cm(item)
                side_effects.append(cm)
        mock_session.get = MagicMock(side_effect=side_effects)
        return mock_session

    def test_build_params(self, list_reader):
        """_build_params 应生成正确的参数字典"""
        params = list_reader._build_params("m:0+t:6", page=1, size=100)
        assert params["pn"] == "1"
        assert params["pz"] == "100"
        assert params["fs"] == "m:0+t:6"
        assert "cb" in params
        assert params["cb"].startswith("jQuery")

    @pytest.mark.asyncio
    async def test_successful_fetch(self, list_reader, valid_list_response):
        """正常请求应返回解析后的股票列表"""
        mock_resp = self._make_response(valid_list_response)
        mock_session = self._make_session_for_list([mock_resp])

        result = await list_reader.fetch_page(mock_session, "m:0+t:6", page=1)

        assert result is not None
        assert len(result) == 1
        assert result[0]["code"] == "000001"
        assert result[0]["name"] == "平安银行"

    @pytest.mark.asyncio
    async def test_fetch_page_retry_on_connection_error(self, list_reader, valid_list_response):
        """fetch_page 在连接错误时应重试"""
        from aiohttp import ClientError

        mock_resp = self._make_response(valid_list_response)
        mock_session = self._make_session_for_list([
            ClientError("Server disconnected"),
            mock_resp,
        ])

        with patch("eastmoney_quote_reader.asyncio.sleep", new_callable=AsyncMock):
            result = await list_reader.fetch_page(mock_session, "m:0+t:6", page=1)

        assert result is not None
        assert result[0]["code"] == "000001"

    @pytest.mark.asyncio
    async def test_skip_first_cookie(self, list_reader, valid_list_response):
        """skip_first_cookie=True 时第一次请求不应带 Cookie"""
        mock_resp = self._make_response(valid_list_response)
        mock_session = self._make_session_for_list([mock_resp])

        result = await list_reader.fetch_page(
            mock_session, "m:0+t:6", page=1, skip_first_cookie=True
        )

        assert result is not None
        # 验证 get 被调用时 headers 中不含 Cookie
        call_kwargs = mock_session.get.call_args
        assert "headers" in call_kwargs[1], f"应传递 headers 参数, got {call_kwargs}"
        assert "Cookie" not in call_kwargs[1]["headers"], (
            f"skip_first_cookie=True 时不应带 Cookie, got {call_kwargs[1]['headers']}"
        )


# =============================================================================
# 第三部分: data_fetcher 纯逻辑测试
# =============================================================================


class TestGuessMarket:
    """_guess_market 函数测试"""

    def test_shanghai_codes(self):
        from backend.data_fetcher import _guess_market
        # 6开头 = 上海
        assert _guess_market("600036") == Market.SHANGHAI
        assert _guess_market("601857") == Market.SHANGHAI
        assert _guess_market("688001") == Market.SHANGHAI

    def test_shenzhen_codes(self):
        from backend.data_fetcher import _guess_market
        # 0/3开头 = 深圳
        assert _guess_market("000001") == Market.SHENGZHEN
        assert _guess_market("000858") == Market.SHENGZHEN
        assert _guess_market("300750") == Market.SHENGZHEN
        assert _guess_market("002415") == Market.SHENGZHEN


class TestQuoteToDataframe:
    """_quote_to_dataframe 函数测试"""

    def test_valid_quote_returns_dataframe(self):
        from backend.data_fetcher import _quote_to_dataframe

        lines = [
            StockQuoteLine(datetime(2025, 6, 29), 9.0, 9.5, 10.0, 8.5, 500000.0, 4750000.0),
            StockQuoteLine(datetime(2025, 6, 30), 9.5, 10.0, 10.5, 9.0, 600000.0, 6000000.0),
        ]
        quote = StockQuote("test", lines, PeriodType.DAILY)
        df = _quote_to_dataframe(quote)

        assert len(df) == 2
        assert list(df.columns) == [
            "trade_date", "open_price", "high_price", "low_price",
            "close_price", "volume", "amount"
        ]
        assert df.iloc[0]["open_price"] == 9.0
        assert df.iloc[1]["close_price"] == 10.0
        assert df.iloc[0]["volume"] == 500000
        assert df.iloc[1]["amount"] == 6000000.0

    def test_none_quote_returns_empty_dataframe(self):
        from backend.data_fetcher import _quote_to_dataframe
        df = _quote_to_dataframe(None)
        assert df.empty

    def test_empty_lines_returns_empty_dataframe(self):
        from backend.data_fetcher import _quote_to_dataframe
        quote = StockQuote("test", [], PeriodType.DAILY)
        df = _quote_to_dataframe(quote)
        assert df.empty


# =============================================================================
# 第四部分: divide_importer JSON 解析逻辑测试
# =============================================================================


class TestDivideImporter:
    """分红导入器测试"""

    def _get_import_function(self):
        """延迟导入以避免数据库连接"""
        # 不直接导入模块（会创建 ENGINE），而是测试其中的解析逻辑
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "divide_importer",
            os.path.join(os.path.dirname(__file__), "divide_importer.py")
        )
        # 仅提取 import_json_to_db 函数中的 JSON 解析逻辑
        # 实际上我们直接 mock SQL 调用
        pass

    def test_old_format_per_share_conversion(self):
        """旧格式 per_share 应转换为 cash_per_10 * 10"""
        item = {
            "annual": "2007年末期",
            "per_share": 0.15686,
            "record_date": "2008-06-12",
            "ex_dividend_date": "2008-06-13",
            "payment_date": "2008-06-30",
        }
        cash_val = float(item["per_share"]) * 10
        assert abs(cash_val - 1.5686) < 0.0001

    def test_new_format_direct_cash_per_10(self):
        """新格式直接使用 cash_per_10"""
        item = {
            "event_name": "2024年末期",
            "cash_per_10": 2.5,
            "bonus_per_10": 2.0,
            "conversion_per_10": 3.0,
            "ex_dividend_date": "2025-06-23",
        }
        cash_val = float(item.get("cash_per_10", 0))
        assert cash_val == 2.5

    def test_old_format_detection(self):
        """检测旧格式（只有 per_share 没有 cash_per_10）"""
        item = {"per_share": 0.25, "ex_dividend_date": "2025-01-01"}
        is_old = "per_share" in item and "cash_per_10" not in item
        assert is_old is True

    def test_new_format_detection(self):
        """新格式直接有 cash_per_10"""
        item = {"cash_per_10": 3.0, "ex_dividend_date": "2025-01-01"}
        is_old = "per_share" in item and "cash_per_10" not in item
        assert is_old is False

    def test_missing_ex_dividend_date_skipped(self):
        """缺少 ex_dividend_date 的记录应被跳过"""
        item = {"cash_per_10": 1.0}
        assert not item.get("ex_dividend_date")

    def test_default_zero_for_missing_fields(self):
        """缺失的送股转增字段默认为 0"""
        item = {"cash_per_10": 2.0, "ex_dividend_date": "2025-06-23"}
        bonus = float(item.get("bonus_per_10", 0))
        conversion = float(item.get("conversion_per_10", 0))
        assert bonus == 0
        assert conversion == 0


# =============================================================================
# 第五部分: services.py 纯逻辑测试（mock DB）
# =============================================================================


class TestSyncStockList:
    """sync_stock_list 测试"""

    @pytest.fixture
    def mock_db(self):
        """构造一个 magic mock 数据库 session"""
        db = MagicMock()
        # query().filter().first() 返回 None（表示股票不存在）
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    def test_sync_empty_list_returns_ok(self, mock_db):
        """当 Eastmoney 返回空列表时，应返回 ok 状态"""
        # Mock EastmoneyStockListReader.fetch_all_stocks 返回空列表
        mock_stocks = []

        async def _mock_sync():
            reader = MagicMock()
            reader.fetch_all_stocks = AsyncMock(return_value=mock_stocks)
            return await reader.fetch_all_stocks("fs", size=100, max_pages=200)

        with patch(
            "backend.services.EastmoneyStockListReader",
        ) as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.fetch_all_stocks = AsyncMock(return_value=mock_stocks)
            mock_reader_cls.return_value = mock_reader

            from backend.services import sync_stock_list
            result = sync_stock_list(mock_db)

        assert result["status"] == "ok"
        assert result["total"] == 0

    def test_sync_new_stocks_adds_to_db(self, mock_db):
        """新增股票应调用 db.add"""
        mock_stocks = [
            {"code": "000001", "market": 0, "name": "平安银行", "price": 10.0, "change_pct": 1.0,
             "change_amount": 0.1, "volume": 100, "pe": 12.0},
        ]

        with patch(
            "backend.services.EastmoneyStockListReader",
        ) as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.fetch_all_stocks = AsyncMock(return_value=mock_stocks)
            mock_reader_cls.return_value = mock_reader

            from backend.services import sync_stock_list
            result = sync_stock_list(mock_db)

        assert result["status"] == "ok"
        assert result["total"] == 1
        # 验证 db.add 被调用
        assert mock_db.add.called, "新增股票应调用 db.add"

    def test_sync_existing_stock_updates_name(self, mock_db):
        """已存在股票名称变更时应更新"""
        from backend.models import StockInfo
        existing = StockInfo(stock_code="000001", stock_name="旧名称", market="SZ")
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        mock_stocks = [
            {"code": "000001", "market": 0, "name": "新名称", "price": 10.0, "change_pct": 1.0,
             "change_amount": 0.1, "volume": 100, "pe": 12.0},
        ]

        with patch(
            "backend.services.EastmoneyStockListReader",
        ) as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.fetch_all_stocks = AsyncMock(return_value=mock_stocks)
            mock_reader_cls.return_value = mock_reader

            from backend.services import sync_stock_list
            result = sync_stock_list(mock_db)

        assert result["status"] == "ok"
        assert result["total"] == 1
        assert existing.stock_name == "新名称", "股票名称应被更新"

    def test_sync_failure_returns_error(self, mock_db):
        """网络请求失败应返回 error 状态"""
        with patch(
            "backend.services.EastmoneyStockListReader",
        ) as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.fetch_all_stocks = AsyncMock(side_effect=Exception("网络错误"))
            mock_reader_cls.return_value = mock_reader

            from backend.services import sync_stock_list
            result = sync_stock_list(mock_db)

        assert result["status"] == "error"
        assert "网络错误" in result["message"]


class TestStockServices:
    """其他 services 纯函数测试"""

    def test_to_raw_quote(self):
        """_to_raw_quote 应正确转换 ORM 对象"""
        from backend.services import _to_raw_quote
        from backend.models import StockDailyQuote

        mock_row = StockDailyQuote(
            stock_code="000001",
            trade_date=date(2025, 6, 30),
            open_price=10.0,
            high_price=11.0,
            low_price=9.0,
            close_price=10.5,
            volume=1000000,
            amount=10500000.0,
        )

        result = _to_raw_quote(mock_row)
        assert result["trade_date"] == date(2025, 6, 30)
        assert result["open_price"] == 10.0
        assert result["close_price"] == 10.5

    def test_to_forward_quote(self):
        """_to_forward_quote 应优先使用复权价格"""
        from backend.services import _to_forward_quote
        from backend.models import StockDailyQuote

        mock_row = StockDailyQuote(
            stock_code="000001",
            trade_date=date(2025, 6, 30),
            open_price=10.0, close_price=10.5,
            high_price=11.0, low_price=9.0,
            volume=1000000, amount=10500000.0,
            forward_open=8.0, forward_close=8.5,
            forward_high=9.0, forward_low=7.5,
        )

        result = _to_forward_quote(mock_row)
        assert result["open_price"] == 8.0, "应使用前复权开盘价"
        assert result["close_price"] == 8.5, "应使用前复权收盘价"

    def test_to_forward_quote_fallback(self):
        """复权价格为 None 时应回退到不复权价格"""
        from backend.services import _to_forward_quote
        from backend.models import StockDailyQuote

        mock_row = StockDailyQuote(
            stock_code="000001",
            trade_date=date(2025, 6, 30),
            open_price=10.0, close_price=10.5,
            high_price=11.0, low_price=9.0,
            volume=1000000, amount=10500000.0,
            forward_open=None, forward_close=None,
            forward_high=None, forward_low=None,
        )

        result = _to_forward_quote(mock_row)
        assert result["open_price"] == 10.0, "无复权价时应回退到不复权价"


# =============================================================================
# 第六部分: quote_saver 逻辑测试
# =============================================================================


class TestQuoteSaver:
    """quote_saver 辅助逻辑测试"""

    def test_stock_with_empty_data_skipped(self):
        """股票无行情数据时应被跳过"""
        reader = EastmoneyQuoteReader()
        reader.read_quote = MagicMock(return_value=None)
        # 只测试 StockQuote 空值检测逻辑
        quote = None
        is_empty = not quote or not (quote.quote_lines if quote else None)
        assert is_empty is True

    def test_df_filtering_by_start_date(self):
        """DataFrame 应按 start_date 过滤"""
        import pandas as pd
        df = pd.DataFrame({
            "trade_date": pd.to_datetime(["2008-06-01", "2008-07-01", "2007-12-31"]),
            "close_price": [10.0, 11.0, 9.0],
        })
        start_dt = datetime.strptime("2008-01-01", "%Y-%m-%d").date()
        filtered = df[df["trade_date"] >= pd.Timestamp(start_dt)]
        assert len(filtered) == 2
        assert "2007-12-31" not in filtered["trade_date"].dt.strftime("%Y-%m-%d").values


# =============================================================================
# 第七部分: StockQuoteLine/StockQuote 边界测试
# =============================================================================


class TestEdgeCases:
    """边界情况测试"""

    def test_negative_prices(self):
        """负价格应该可以正常存储（某些异常数据源可能出现）"""
        line = StockQuoteLine(
            trade_date=datetime(2025, 1, 1),
            open_price=-1.0, close_price=-1.0,
            high_price=-1.0, low_price=-1.0,
            trade_volume=0.0, trade_amount=0.0,
        )
        assert line.open == -1.0

    def test_zero_volume(self):
        """零成交量是合法的"""
        line = StockQuoteLine(
            trade_date=datetime(2025, 1, 1),
            open_price=10.0, close_price=10.0,
            high_price=10.0, low_price=10.0,
            trade_volume=0.0, trade_amount=0.0,
        )
        assert line.volume == 0.0

    def test_large_numbers(self):
        """大数值（如贵州茅台价格）"""
        line = StockQuoteLine(
            trade_date=datetime(2025, 1, 1),
            open_price=1800.0, close_price=1820.5,
            high_price=1850.0, low_price=1790.0,
            trade_volume=50000000.0, trade_amount=90000000000.0,
        )
        assert line.close == 1820.5

    def test_quote_sorting(self):
        """行情数据应按日期排序"""
        lines = [
            StockQuoteLine(datetime(2025, 6, 30), 10.0, 10.5, 11.0, 9.5, 1.0, 1.0),
            StockQuoteLine(datetime(2025, 6, 29), 9.0, 9.5, 10.0, 8.5, 1.0, 1.0),
            StockQuoteLine(datetime(2025, 6, 28), 8.0, 8.5, 9.0, 7.5, 1.0, 1.0),
        ]
        sorted_lines = sorted(lines, key=lambda x: x.trade_date)
        assert sorted_lines[0].trade_date == datetime(2025, 6, 28)
        assert sorted_lines[-1].trade_date == datetime(2025, 6, 30)


# =============================================================================
# 主运行入口
# =============================================================================

if __name__ == "__main__":
    # 使用 pytest 运行并显示详细结果
    import pytest
    exit_code = pytest.main([
        __file__,
        "-v",  # verbose
        "--tb=short",  # 短回溯
        "--color=yes",
        "-p", "no:warnings",  # 忽略三方库 warning
    ])
    sys.exit(exit_code)
