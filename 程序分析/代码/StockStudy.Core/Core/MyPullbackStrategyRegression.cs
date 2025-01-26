using StockStudy.Models; 

namespace StockStudy.Core
{
    public class MyPullbackStrategyRegression : IStrategyRegression
    {
        private readonly ITrader _trader;

        public string Code => "mpb";

        public string Name => "我的回调做多策略";

        private List<TradingSnapshot> _tradingSnapshots = new List<TradingSnapshot>();

        private decimal holdings = 0M;
        private decimal investedAmount = 0M;

        public MyPullbackStrategyRegression(ITrader trader)
        {
            _trader = trader;
        }

        public InvestmentSnapshot Regress(StockQuote quote)
        {
            //前三个K线回撤超过P个百分点 买入  （ 收盘价 ）

            var pullbackPencentage = 0.03M;
            var buyVolumn = 10000;

            var lines = quote.QuoteLines.ToArray();
            for (int idx = 0; idx < lines.Length; idx++)
            {
                var lineT2 = idx - 2 < 0 ? lines[idx] : lines[idx - 2];
                var lineT = lines[idx];

                var buyPrice = lineT.Close;

                if (idx == 0)
                { 
                    Buy(quote.StockName, lineT.TradeDate, buyPrice, buyVolumn);
                }

                var longSignal = (lineT2.Close - lineT.Close) / lineT.Close >= pullbackPencentage;
                if (longSignal)
                {
                    Buy(quote.StockName, lineT.TradeDate, buyPrice, buyVolumn);
                }
            } 
            var finalAmount = holdings * quote.QuoteLines.Last().Close;

            return new InvestmentSnapshot(Name, quote, _tradingSnapshots)
            {
                Cost = investedAmount,
                Final = finalAmount,
            };
        }

        private void Buy(string stockName, DateTime tradeDate, decimal buyPrice, int buyVolumn)
        {
            var record = _trader.DoBuy(stockName, tradeDate, buyPrice, buyVolumn);
            investedAmount += record.Amount;
            _tradingSnapshots.Add(new TradingSnapshot
            {
                TradeDate = tradeDate,
                AvailableCash = buyVolumn,
                StockHoldings = new StockHolding[1]
                {
                    new StockHolding
                    {
                        TradePrice = buyPrice,
                        HoldingShares = holdings,
                        StockName = stockName,
                        TradeVolume = record.Volume,
                        TradeDirection = record.Direction,
                    }
                }
            });
            holdings += buyVolumn;
        }
    }
}
