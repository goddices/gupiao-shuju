using StockStudy.Models;

namespace StockStudy.Core
{
    /// <summary>
    /// 随便测测
    /// </summary>
    public class AnyTestStrategyRegression : IStrategyRegression
    {
        private decimal initialAmount = 50_0000M;
        private decimal currentAmount = 50_0000M;
        private decimal holdings = 0M;

        public string Code => "any";

        public string Name => "随便玩玩策略";

        public InvestmentSnapshot Regress(string strategyName, StockQuote quote)
        {
            //在前4个K线 从最高价 下跌 对比收盘价 超过 10%  全部资金买入 收盘价
            //在前4个K线 从最低价 上涨 对比收盘价 超过 10%  全部持仓卖出 收盘价
            //其他情况不动
            //买入 卖出后 等4个交易日
            var highest = 0M;
            var lowest = 0M;
            var counter = 0;
            foreach (var line in quote.QuoteLines)
            {
                counter++;
                if (line.High > highest) highest = line.High;
                if (line.Low < lowest) lowest = line.Low;
                if (counter == 4)
                {
                    if (highest != 0 && ((line.Close - highest) / highest) >= -0.1M)
                    {
                        BuyIfAvailable(line);
                        counter = 0;
                        continue;
                    }
                    if (lowest != 0 && ((line.Close - lowest) / lowest) >= 0.1M)
                    {
                        SellIfAvailable(line);
                        counter = 0;
                        continue;
                    }
                }

            }

            return new InvestmentSnapshot(strategyName, quote)
            {
                CostAmount = initialAmount,
                FinalAmount = holdings * quote.QuoteLines.Last().Close
            };
        }

        private void BuyIfAvailable(StockQuoteLine line)
        {
            if (line.Close == 0) return;
            if (currentAmount / line.Close > 0)
            {
                holdings = currentAmount / line.Close;
                currentAmount = 0;
            }
        }
        private void SellIfAvailable(StockQuoteLine line)
        {
            if (line.Close == 0) return;
            if (holdings > 0)
            {
                holdings = 0;
                currentAmount = holdings * line.Close;
            }
        }
    }
}
