using StockStudy.Models;
using System.Diagnostics;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace StockStudy.Core
{
    /// <summary>
    /// 随便测测
    /// </summary>
    public class AnyTestStrategyRegression : IStrategyRegression
    {
        private decimal initialCash = 50_0000M;
        private decimal cash = 50_0000M;
        private decimal holdings = 0M;
        private readonly ITrader _trader;
        private decimal threshold = 0.02M;

        public string Code => "any";

        public string Name => "随便玩玩策略";

        public AnyTestStrategyRegression(ITrader trader)
        {
            _trader = trader;
        }

        public InvestmentSnapshot Regress(string strategyName, StockQuote quote)
        {
            //在前4个K线 从最高价 下跌 对比收盘价 超过 10%  全部资金买入 收盘价
            //在前4个K线 从最低价 上涨 对比收盘价 超过 10%  全部持仓卖出 收盘价
            //其他情况不动
            //买入 卖出后 等4个交易日
            var highest = 0M;
            var lowest = 0M;
            var counter = 0;
            var _tradingSnapshotList = new List<TradingSnapshot>();
            foreach (var line in quote.QuoteLines)
            {
                TransactionRecord? record = null;
                counter++;
                if (line.High > highest) highest = line.High;
                if (line.Low < lowest) lowest = line.Low;
                if (counter == 4)
                {
                    if (highest != 0 && ((line.Close - highest) / highest) >= -1 * threshold)
                    {
                        record = TryBuy(quote.StockName, line.TradeDate, line.Close);
                        counter = 0;
                    }
                    else if (lowest != 0 && ((line.Close - lowest) / lowest) >= threshold)
                    {
                        record = TrySell(quote.StockName, line.TradeDate, line.Close);
                        counter = 0;
                    }

                    if (record != null)
                    {
                        _tradingSnapshotList.Add(new TradingSnapshot
                        {
                            AvailableCash = cash,
                            TradeDate = line.TradeDate,
                            StockHoldings = new StockHolding[1]
                            {
                                new StockHolding
                                {
                                    TradePrice = line.Close,
                                    HoldingShares = holdings,
                                    StockName = quote.StockName,
                                    TradeVolume = record.Volume,
                                    TradeDirection = record.Direction
                                }
                            }
                        });
                    }
                }
            }

            return new InvestmentSnapshot(strategyName, quote, _tradingSnapshotList)
            {
                CostAmount = initialCash,
                FinalAmount = cash + holdings * quote.QuoteLines.Last().Close,

            };
        }

        private TransactionRecord? TryBuy(string name, DateTime date, decimal price)
        {
            if (price <= 0) return null;

            var record = _trader.TryBuy(name, date, cash, price);
            if (record != null)
            {
                cash -= record.Amount;
                holdings += record.Volume;
                return record;
            }
            return null;
        }

        private TransactionRecord? TrySell(string name, DateTime date, decimal price)
        {
            if (price <= 0) return null;
            var record = _trader.TrySell(name, date, holdings, price);
            if (record != null)
            {
                cash += record.Amount;
                holdings -= record.Volume;
                return record;
            }
            return null;
        }
    }
}
