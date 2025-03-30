using StockStudy.Models;

namespace StockStudy.Core
{
    /// <summary>
    ///  定投（直译：美元成本平均） 
    /// </summary>
    public class DollarCostAveragingStrategy : AbstractStrategy, IRegressionStrategy
    {
        public override string Code => "dca";
        public override string Name => " 定投策略";

        public DollarCostAveragingStrategy(DefaultEngine engine) : base(engine)
        {
        }

        /// <summary>
        /// 固定金额买入标的
        /// </summary>
        private decimal fixedAmount = 10_000M;

        protected override void RegressInternal(StockQuote quote)
        {
            foreach (var line in quote.QuoteLines)
            {
                //用最高最低的平均值
                var price = 0.5M * (line.High + line.Low);
                if (price == 0) continue;
                var volume = fixedAmount / price;
                Engine.Deposit(price, volume);
                Engine.Buy(quote.StockName, line.TradeDate, price, volume);
            }
        }
    }
}
