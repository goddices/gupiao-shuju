using StockStudy.Models;

namespace StockStudy.Core
{
    /// <summary>
    ///  定投策略回归
    /// </summary>
    public class DollarCostAveragingStrategyRegression : IStrategyRegression
    {
        private readonly ITrader _trader;

        public string Code => "dca";

        public string Name => " 定投策略";

        public DollarCostAveragingStrategyRegression(ITrader trader)
        {
            _trader = trader;
        }

        public InvestmentSnapshot Regress(string strategyName, StockQuote quote)
        {
            var fixedAmount = 1_000M;
            var investedAmount = 0M;
            var holdings = 0M;
            var tradingSnapshots = new List<TradingSnapshot>();

            foreach (var line in quote.QuoteLines)
            {
                var buyPrice = 0.5M * (line.High + line.Low);
                if (buyPrice == 0) continue;

                var fixedVolume = fixedAmount / buyPrice;
                var record = _trader.DoBuy(quote.StockName, line.TradeDate, buyPrice, fixedVolume);
                investedAmount += fixedAmount;
                holdings += fixedVolume;
                tradingSnapshots.Add(new TradingSnapshot
                {
                    TradeDate = line.TradeDate,
                    AvailableCash = investedAmount,
                    StockHoldings = new StockHolding[1]
                    {
                        new StockHolding
                        {
                             TradePrice = buyPrice,
                             HoldingShares = holdings,
                             StockName = quote.StockName,
                             TradeVolume = record.Volume,
                             TradeDirection = record.Direction,
                        }
                    }
                });
            }
            var finalAmount = holdings * quote.QuoteLines.Last().Close;

            return new InvestmentSnapshot(strategyName, quote, tradingSnapshots)
            {
                CostAmount = investedAmount,
                FinalAmount = finalAmount,
            };
        }
    }
}
