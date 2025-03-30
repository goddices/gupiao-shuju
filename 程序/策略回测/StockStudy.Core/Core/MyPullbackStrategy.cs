using Microsoft.EntityFrameworkCore.Metadata.Internal;
using StockStudy.Models;

namespace StockStudy.Core
{
    /// <summary>
    /// 回调做多
    /// </summary>
    public class MyPullbackStrategy : AbstractStrategy, IRegressionStrategy
    {
        public override string Code => "mpb";
        public override string Name => "回调做多";

        public MyPullbackStrategy(DefaultEngine engine) : base(engine)
        {
        }


        protected override void RegressInternal(StockQuote quote)
        {
            //前三个K线回撤超过P个百分点 买入  （ 收盘价 ）

            var pullbackPencentage = 0.03M;
            var volume = 10000;

            var lines = quote.QuoteLines.ToArray();
            for (int idx = 0; idx < lines.Length; idx++)
            {
                var lineT2 = idx - 2 < 0 ? lines[idx] : lines[idx - 2];
                var lineT = lines[idx];

                var price = lineT.Close;

                if (idx == 0)
                {
                    Engine.Deposit(price, volume);
                    Engine.Buy(quote.StockName, lineT.TradeDate, price, volume);
                }

                var longSignal = (lineT2.Close - lineT.Close) / lineT.Close >= pullbackPencentage;
                if (longSignal)
                {
                    Engine.Deposit(price, volume);
                    Engine.Buy(quote.StockName, lineT.TradeDate, price, volume);
                    continue;
                }

                var shortSignal = (lineT.Close - lineT2.Close) / lineT.Close >= pullbackPencentage;
                if (shortSignal)
                {
                    //Sell(quote.StockName, lineT.TradeDate, price, volumn);
                    continue;
                }
            } 
        }

    }
}
