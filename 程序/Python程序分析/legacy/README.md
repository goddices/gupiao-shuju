# legacy/ —— 旧版归档（2026-09-07）

本目录存放已被新管线取代的旧版脚本与残留数据，**保留备查，不在任何运行链路上**。
归档依据见《项目重构方案.md》P1。

| 文件 | 原位置 | 被取代者 |
|---|---|---|
| `quote_saver.py` | 根目录 | `backend/data_fetcher.py` + `sync_quotes.sh`（三复权、多数据源、异步并行） |
| `divide_importer.py` | 根目录 | `backend/services.py:sync_stock_dividends`（在线拉取，写新表 `stock_dividend_detail`） |
| `temp_601857.json` | 根目录 | divide_importer 的一次性输入（601857 分红 37 期），数据已在库中 |
| `get_adjust_price.py` | 根目录 | 复权价改由 data_fetcher 直接拉取填充（原自算加法复权） |
| `模拟持仓2.py` | 根目录 | `python3 股票分析.py 红利再投`（硬编码 601857 + 内置分红数据的旧版） |
| `insert_000001.py` | backend/ | 一次性脚本（上证指数入库），已执行完毕 |
| `china_holidays_summary_legacy.json` | public_data/cn_holidays/ | 无任何代码引用的假日汇总旧格式文件 |

注意：
- `divide_importer.py`/`get_adjust_price.py` 读写的是**旧表 `stock_dividend_events`**；
  新管线用 `stock_dividend_detail`。旧表唯一活读者是 `GET /api/stocks/{code}/dividends`
  （双轨问题，收敛计划见《项目重构方案.md》P5）。
- 三个数据脚本内联硬编码数据库口令（root/123456），已随归档失效。
- `test_sync_interfaces.py` 第四、六部分（对 quote_saver/divide_importer 的测试）已同步删除。
