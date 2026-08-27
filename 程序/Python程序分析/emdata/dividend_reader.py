"""
东方财富分红明细读取器
数据接口: https://datacenter-web.eastmoney.com/api/data/v1/get (RPT_SHAREBONUS_DET 报表)
"""
import asyncio
import aiohttp
import json
import random
import time
from typing import Optional, List, Dict, Any

from emdata.config import MAX_RETRIES, RETRY_DELAY_MIN, RETRY_DELAY_MAX, _is_connection_error, SEED_COOKIE
from emdata.models import DividendRecord
from emdata.cookie import generate_eastmoney_cookie_str
from emdata.quote_reader import _generate_simple_cookie


class EastmoneyDividendReader:
    """
    东方财富分红明细读取器（异步）
    获取个股历史分红送转明细（每10股派息/送股/转增、除权除息日、分配进度等）
    """

    BASE_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    # 原始字段 → DividendRecord 属性
    FIELD_MAP = {
        "SECURITY_CODE": "stock_code",
        "SECURITY_NAME_ABBR": "stock_name",
        "REPORT_DATE": "report_date",
        "EQUITY_RECORD_DATE": "record_date",
        "EX_DIVIDEND_DATE": "ex_dividend_date",
        "NOTICE_DATE": "notice_date",
        "PLAN_NOTICE_DATE": "plan_notice_date",
        "ASSIGN_PROGRESS": "assign_progress",
        "IMPL_PLAN_PROFILE": "impl_plan_profile",
        "PRETAX_BONUS_RMB": "cash_per_10",
        "BONUS_RATIO": "bonus_per_10",
        "IT_RATIO": "conversion_per_10",
        "BASIC_EPS": "basic_eps",
        "BVPS": "bvps",
        "DIVIDENT_RATIO": "dividend_ratio",
        "TOTAL_SHARES": "total_shares",
        "EX_DIVIDEND_DAYS": "ex_dividend_days",
    }

    # 日期字段（"2026-06-26 00:00:00" → 取前10位）
    DATE_FIELDS = {
        "report_date", "record_date", "ex_dividend_date",
        "notice_date", "plan_notice_date",
    }

    # 字符串字段（原样返回，不做数值转换）
    STR_FIELDS = {"stock_code", "stock_name", "assign_progress", "impl_plan_profile"}

    # 整数字段
    INT_FIELDS = {"ex_dividend_days"}

    def __init__(self, cookie: Optional[str] = None, db_cookies: list = None):
        self.base_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://data.eastmoney.com/",
        }
        self.cookie = cookie or generate_eastmoney_cookie_str()
        self._db_cookies = db_cookies or []

    def _build_params(self, secucode: str, page: int, size: int = 100) -> Dict[str, Any]:
        """构建请求参数"""
        return {
            "reportName": "RPT_SHAREBONUS_DET",
            "columns": "ALL",
            "filter": f'(SECUCODE="{secucode}")',
            "pageNumber": str(page),
            "pageSize": str(size),
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
        }

    @staticmethod
    def _parse_date_value(value: Any) -> Optional[str]:
        """"2026-06-26 00:00:00" → "2026-06-26"，空值返回 None"""
        if not value:
            return None
        s = str(value).strip()
        return s[:10] if len(s) >= 10 else (s or None)

    @staticmethod
    def _parse_number_value(value: Any, is_int: bool = False) -> Optional[float]:
        """数值字段 null 安全转换，"-" 视为 None"""
        if value is None or value == "-" or value == "":
            return None
        try:
            val = float(value)
            return int(val) if is_int else val
        except (ValueError, TypeError):
            return None

    def _parse_item(self, raw: dict) -> Optional[DividendRecord]:
        """解析单条原始记录，缺失除权除息日的记录跳过"""
        kwargs = {}
        for raw_field, attr_name in self.FIELD_MAP.items():
            val = raw.get(raw_field)
            if attr_name in self.DATE_FIELDS:
                val = self._parse_date_value(val)
            elif attr_name in self.INT_FIELDS:
                val = self._parse_number_value(val, is_int=True)
            elif attr_name not in self.STR_FIELDS:
                val = self._parse_number_value(val)
            kwargs[attr_name] = val

        if not kwargs.get("ex_dividend_date"):
            return None

        return DividendRecord(**kwargs)

    async def fetch_page(
        self,
        session: aiohttp.ClientSession,
        secucode: str,
        page: int,
        size: int = 100,
    ) -> Optional[List[dict]]:
        """
        异步获取单页分红记录
        :return: 原始记录列表，失败或无数据返回 None
        """
        params = self._build_params(secucode, page, size)

        # 策略：优先已验证 Cookie（SEED + DB），生成的新 Cookie 最后尝试
        verified_cookies = [SEED_COOKIE]
        verified_cookies.extend(self._db_cookies)
        verified_cookies.extend(getattr(self, '_fallback_cookies', []))

        seen = set()
        all_tries = []
        for c in verified_cookies:
            if c and c not in seen:
                seen.add(c)
                all_tries.append(('verified', c))

        # 生成 Cookie 作为最后尝试
        for i in range(MAX_RETRIES):
            try:
                all_tries.append(('generated', generate_eastmoney_cookie_str()))
            except Exception:
                pass
            try:
                all_tries.append(('generated', _generate_simple_cookie()))
            except Exception:
                pass

        for kind, cookie in all_tries:
            if not cookie:
                continue
            try:
                req_headers = dict(self.base_headers)
                req_headers["Cookie"] = cookie

                async with session.get(self.BASE_URL, params=params, headers=req_headers) as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                    data = json.loads(text)
                    if not data.get("success") or not data.get("result"):
                        continue
                    rows = data["result"].get("data") or []
                    if not rows:
                        continue
                    self.last_used_cookie = cookie
                    return rows
            except aiohttp.ClientError as e:
                if _is_connection_error(e):
                    wait = RETRY_DELAY_MIN + random.random() * (RETRY_DELAY_MAX - RETRY_DELAY_MIN)
                    await asyncio.sleep(wait)
                    continue
            except Exception:
                continue

        return None

    async def fetch_all_dividends(
        self,
        secucode: str,
        fallback_cookies: list = None,
        max_pages: int = 20,
        size: int = 100,
    ) -> Optional[List[DividendRecord]]:
        """
        循环获取个股全部分红记录（翻页直到取完）

        :param secucode: 东财证券代码（如 601857.SH）
        :param fallback_cookies: 备用 Cookie 列表（从 DB 获取，失败时兜底）
        :param max_pages: 最大页数，防止死循环
        :return: DividendRecord 列表，失败返回 None
        """
        if fallback_cookies:
            self._db_cookies = fallback_cookies

        all_records: List[DividendRecord] = []
        page = 1

        async with aiohttp.ClientSession(headers=self.base_headers) as session:
            while page <= max_pages:
                page_data = await self.fetch_page(session, secucode, page, size)
                if not page_data:
                    # 第一页失败视为整体失败；后续页失败视为已取完（避免丢已得数据）
                    if page == 1:
                        return None
                    break
                for raw in page_data:
                    record = self._parse_item(raw)
                    if record:
                        all_records.append(record)
                if len(page_data) < size:
                    break
                page += 1

        return all_records

    def fetch_dividends(
        self,
        secucode: str,
        fallback_cookies: list = None,
        max_pages: int = 20,
    ) -> Optional[List[DividendRecord]]:
        """同步获取分红记录（包装异步方法）"""
        return asyncio.run(self.fetch_all_dividends(secucode, fallback_cookies, max_pages))
