# -*- coding: utf-8 -*-
"""simulation —— 模拟/测算公共层，web（backend 各路由）与 CLI（analysis/tools 各工具）共用

    dividend_reinvest_engine.py  红利再投/大跌买入/分红目标测算的纯计算引擎（零第三方依赖）
    strategy_runners.py          DB 取数（analysis.data_access）→ 调引擎 → 返回 dict 的统一装配层
    account_service.py           web 账户式模拟（买卖/持仓/费率，原 backend/simulation_service.py）

本包内模块沿用项目扁平导入习惯（from models import ...、from database import ...、
from analysis.xxx import ...），故在包导入时自行把项目根与 backend 目录注入 sys.path
（与 analysis/data_access.py 同款机制）。

边界说明：`from simulation...` 本身要求项目根已可导入——web 侧由 routers 导入链中
backend/services.py 的注入保证（先于 routers/simulation 执行）；CLI 侧由 股票分析.py
所在目录（sys.path[0]）保证；从 backend 目录裸跑 `python -c "from simulation..."`
（无任何先行注入）不在支持范围。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
for _p in (_ROOT, _BACKEND):
    if _p not in sys.path:
        sys.path.insert(0, _p)
