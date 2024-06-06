using StockStudy.Models;

namespace StockStudy.Core
{
    /// <summary>
    ///  定投策略回归
    /// </summary>
    public class DollarCostAveragingStrategyRegression : IStrategyRegression
    {
        public string Code => "dca";

        public string Name => " 定投策略";
        public InvestmentSnapshot Regress(string strategyName, StockQuote quote)
        {
            var fixedAmount = 1_000M;
            var investedAmount = 0M;
            var totalStocks = 0M;

            foreach (var line in quote.QuoteLines)
            {
                var buyPrice = 0.5M * (line.High + line.Low);
                if (buyPrice == 0) continue;
                totalStocks += fixedAmount / buyPrice;
                investedAmount += fixedAmount;
            }
            var finalAmount = totalStocks * quote.QuoteLines.Last().Close;

            return new InvestmentSnapshot(strategyName, quote)
            {
                CostAmount = investedAmount,
                FinalAmount = finalAmount,
            };
        }
    }
}
