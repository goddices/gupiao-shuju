using StockStudy.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Core
{
    /// <summary>
    /// 高抛低吸策略
    /// </summary>
    public class HighSellLowBuyStrategyRegression : IStrategyRegression
    {
        public string Code => "hslb";

        public string Name => "高抛低吸";

        public InvestmentSnapshot Regress(StockQuote quote)
        {
            // 1 先买半仓
            // 2 涨过去三个交易日累计涨3%卖出，跌3%买入

            return new InvestmentSnapshot(Name, quote, null);
        }
    }
}
