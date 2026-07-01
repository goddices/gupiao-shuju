"""
东方财富股票列表读取器
"""
import asyncio
import aiohttp
import json
import random
import time
from typing import Optional, List, Dict, Any

from emdata.config import MAX_RETRIES, RETRY_DELAY_MIN, RETRY_DELAY_MAX, _is_connection_error, SEED_COOKIE
from emdata.cookie import generate_eastmoney_cookie_str


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

        # Phase 1: 随机 Cookie
        for attempt in range(MAX_RETRIES + 1):
            try:
                req_headers = dict(self.base_headers)
                if attempt == 0:
                    if not skip_first_cookie:
                        req_headers["Cookie"] = self.cookie
                else:
                    self.cookie = generate_eastmoney_cookie_str()
                    req_headers["Cookie"] = self.cookie

                async with session.get(self.BASE_URL, params=params, headers=req_headers) as resp:
                    if resp.status != 200:
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
                        return None
                    diff = data.get("data", {}).get("diff", [])
                    if not diff:
                        return None
                    return [
                        {"code": i.get("f12"), "market": i.get("f13"), "name": i.get("f14"),
                         "price": i.get("f1"), "change_pct": i.get("f2"), "change_amount": i.get("f4"),
                         "volume": i.get("f11"), "pe": i.get("f152")}
                        for i in diff
                    ]
            except aiohttp.ClientError as e:
                if _is_connection_error(e) and attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_MIN + random.random() * (RETRY_DELAY_MAX - RETRY_DELAY_MIN)
                    await asyncio.sleep(wait)
                    continue
                return None
            except Exception:
                return None

        # Phase 2: 备用 Cookie 兜底
        fallback = getattr(self, '_fallback_cookies', []) + [SEED_COOKIE]
        seen = set()
        for cookie in fallback:
            if not cookie or cookie in seen:
                continue
            seen.add(cookie)
            try:
                req_headers = dict(self.base_headers)
                req_headers["Cookie"] = cookie
                async with session.get(self.BASE_URL, params=params, headers=req_headers) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if text.startswith(cb) and text.endswith(");"):
                            json_str = text[len(cb) + 1 : -2]
                        else:
                            json_str = text
                        data = json.loads(json_str)
                        if data.get("rc") == 0:
                            diff = data.get("data", {}).get("diff", [])
                            if diff:
                                self.last_used_cookie = cookie
                                return [
                                    {"code": i.get("f12"), "market": i.get("f13"), "name": i.get("f14"),
                                     "price": i.get("f1"), "change_pct": i.get("f2"), "change_amount": i.get("f4"),
                                     "volume": i.get("f11"), "pe": i.get("f152")}
                                    for i in diff
                                ]
            except Exception:
                continue

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
