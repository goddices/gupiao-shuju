using StockStudy.Models;

namespace StockStudy.Core
{
    /// <summary>
    ///  定投（直译：美元成本平均） 
    /// </summary>
    public class DollarCostAveragingStrategy : IRegressionStrategy
    {
        private readonly DefaultTradingEngine _engine;
        public string Code => "dca";
        public string Name => " 定投策略";

        public DollarCostAveragingStrategy(DefaultTradingEngine engine)
        {
            _engine = engine;
        }

        /// <summary>
        /// 固定金额买入标的
        /// </summary>
        private decimal fixedAmount = 1_000M;

        public InvestmentSummary Regress(StockQuote quote)
        {
            foreach (var line in quote.QuoteLines)
            {
                var price = 0.5M * (line.High + line.Low);
                if (price == 0) continue;
                var volume = fixedAmount / price;
                _engine.Deposit(price, volume);
                _engine.Buy(quote.StockName, line.TradeDate, price, volume);
            }
            return _engine.CreateSummary(Name, quote);
        }
    }
}
