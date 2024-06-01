using Newtonsoft.Json.Linq;
using Newtonsoft.Json;
using System.Net.Http;
using System.Text;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using StockStudy.Models;
using StockStudy.EastmoneyImpl;

namespace StockStudy.Core
{
    public class DefaultAnalyst : IAnalyst
    {
        public InvestmentSnapshot StrategyAnanlyzeFinal(StockQuote? quote)
        {
            if (quote == null ||
                quote.QuoteLines == null ||
                !quote.QuoteLines.Any() ||
                quote.QuoteLines.Any(e => e == null))
            {
                throw new ArgumentNullException(nameof(quote));
            }

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

            return new InvestmentSnapshot
            {
                StockName = quote.StockName,
                TotalDays = Convert.ToInt32((quote.QuoteLines.Last().TradeDay - quote.QuoteLines.First().TradeDay).TotalDays),
                CostAmount = investedAmount,
                FinalAmount = finalAmount,
            };
        }
    }
}
