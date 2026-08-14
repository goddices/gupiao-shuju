#使用这个编程方式获取行情数据
from tickflow import TickFlow

tf = TickFlow(api_key="tk_aef1f7190ff44f32b5226f796a3c38ea")

#使用股票代码.市场代码， 市场代码有
后缀	市场	说明
SH	上海证券交易所	沪市 A 股、ETF、债券等
SZ	深圳证券交易所	深市 A 股、创业板、ETF 等
BJ	北京证券交易所	北交所股票
US	美股	美国证券市场
HK	港股	香港联交所


单次单标的最多获取 10000 根 K 线

# 差值前复权（与东方财富、同花顺等软件一致）
df = tf.klines.get("600000.SH", period="1d", count=1000, adjust="forward_additive", as_dataframe=True)

# 不复权
df = tf.klines.get("600000.SH", period="1d", count=1000, adjust="none", as_dataframe=True)
 
# 差值后复权
df = tf.klines.get("600000.SH", period="1d", count=1000, adjust="backward_additive", as_dataframe=True)

#结果如下
#print(df.tail()) 
#       symbol  name      timestamp  trade_date           trade_time  open  high   low  close  volume       amount
#95  600000.SH  浦发银行  1786032000000  2026-08-07  2026-08-07 00:00:00  9.26  9.29  9.14   9.21  565457  520694700.0
#96  600000.SH  浦发银行  1786291200000  2026-08-10  2026-08-10 00:00:00  9.20  9.38  9.16   9.29  625425  581544471.0
#97  600000.SH  浦发银行  1786377600000  2026-08-11  2026-08-11 00:00:00  9.27  9.34  9.18   9.21  509424  470381696.0
#98  600000.SH  浦发银行  1786464000000  2026-08-12  2026-08-12 00:00:00  9.21  9.22  9.12   9.17  467825  429212224.0
#99  600000.SH  浦发银行  1786550400000  2026-08-13  2026-08-13 00:00:00  9.16  9.20  9.10   9.18  528860  483894215.0


period 我猜有 1d 1w 1m 1q 1y

# 批量获取多只股票的 K 线
symbols = ["600000.SH", "000001.SZ", "600519.SH"]

