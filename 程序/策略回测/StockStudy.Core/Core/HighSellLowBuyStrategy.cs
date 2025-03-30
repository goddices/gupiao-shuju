using StockStudy.Models;

namespace StockStudy.Core
{
    /// <summary>
    /// 高抛低吸 
    /// </summary>
    public class HighSellLowBuyStrategy : AbstractStrategy, IRegressionStrategy
    {
        public override string Code => "hslb";
        public override string Name => "高抛低吸";

        public HighSellLowBuyStrategy(DefaultEngine engine) : base(engine)
        {
        }

        protected override void RegressInternal(StockQuote quote)
        {
            Engine.Deposit(1_000_000M);

            // 1 先买半仓
            // 2 涨过去三个交易日累计涨3%卖出，跌3%买入

            var pullbackPencentage = 0.03M;
            var volumn = 2000;

            var lines = quote.QuoteLines.ToArray();
            for (int idx = 0; idx < lines.Length; idx++)
            {
                var lineT3 = idx - 3 < 0 ? lines[idx] : lines[idx - 3];
                var lineT = lines[idx];

                var price = lineT.Close;

                if (idx == 0)
                {
                    Engine.Buy(quote.StockName, lineT.TradeDate, price, volumn);
                }

                var longSignal = (lineT3.Close - lineT.Close) / lineT.Close >= pullbackPencentage;
                if (longSignal)
                {
                    Engine.Buy(quote.StockName, lineT.TradeDate, price, volumn);
                    continue;
                }

                var shortSignal = (lineT.Close - lineT3.Close) / lineT.Close >= pullbackPencentage;
                if (shortSignal)
                {
                    Engine.Sell(quote.StockName, lineT.TradeDate, price, volumn);
                    continue;
                }
            }
        }
    }
}
