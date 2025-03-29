using StockStudy.Models;

namespace StockStudy.Core
{
    /// <summary>
    /// 高抛低吸 
    /// </summary>
    public class HighSellLowBuyStrategy : IRegressionStrategy
    {
        private readonly DefaultTradingEngine _engine;

        public string Code => "hslb";
        public string Name => "高抛低吸";

        public HighSellLowBuyStrategy(DefaultTradingEngine engine)
        {
            _engine = engine;
        }

        public InvestmentSummary Regress(StockQuote quote)
        {
            // 1 先买半仓
            // 2 涨过去三个交易日累计涨3%卖出，跌3%买入

            var pullbackPencentage = 0.03M;
            var volumn = 10000;

            var lines = quote.QuoteLines.ToArray();
            for (int idx = 0; idx < lines.Length; idx++)
            {
                var lineT3 = idx - 3 < 0 ? lines[idx] : lines[idx - 3];
                var lineT = lines[idx];

                var price = lineT.Close;

                if (idx == 0)
                {
                    _engine.Buy(quote.StockName, lineT.TradeDate, price, volumn);
                }

                var longSignal = (lineT3.Close - lineT.Close) / lineT.Close >= pullbackPencentage;
                if (longSignal)
                {
                    _engine.Buy(quote.StockName, lineT.TradeDate, price, volumn);
                    continue;
                }

                var shortSignal = (lineT.Close - lineT3.Close) / lineT.Close >= pullbackPencentage;
                if (shortSignal)
                {
                    _engine.Sell(quote.StockName, lineT.TradeDate, price, volumn);
                    continue;
                }
            }

            return _engine.CreateSummary(Name, quote);
        }
    }
}
