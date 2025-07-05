using Microsoft.VisualStudio.TestTools.UnitTesting;
using StockStudy.Core;
using StockStudy.Models;

namespace StockStudy.Tests
{
    [TestClass]
    public class DollarCostAveragingStrategyTests
    {
        private StockQuote CreateSimpleQuote()
        {
            return new StockQuote(

                stockName: "test",
                quoteLines:
                [
                    new StockQuoteLine
                    {
                        High = 3,
                        Low = 1,
                        Open  =1,
                        Close = 3,
                        TradeDate = DateTime.Now.Date.AddDays(-4)
                    },
                    new StockQuoteLine
                    {
                        High = 4,
                        Low = 2,
                        Open  =2,
                        Close = 4,
                        TradeDate = DateTime.Now.Date.AddDays(-3)
                    },
                    new StockQuoteLine
                    {
                        High = 5,
                        Low = 3,
                        Open  =3,
                        Close = 5,
                        TradeDate = DateTime.Now.Date.AddDays(-2)
                    },
                    new StockQuoteLine
                    {
                        High = 7,
                        Low = 5,
                        Open  =5,
                        Close = 7,
                        TradeDate = DateTime.Now.Date.AddDays(-1)
                    },
                    new StockQuoteLine
                    {
                        High = 8,
                        Low = 8,
                        Open  =8,
                        Close = 8,
                        TradeDate = DateTime.Now.Date
                    },
                ],
                periodType: PeriodType.Weekly
            );
        } 
         
        [TestMethod()]
        public void SmokeTest()
        {
            var strategy = new DollarCostAveragingStrategy(new DefaultEngine(new DefaultTrader()));
            var summary = strategy.Regress(CreateSimpleQuote());
            var sum = summary.ToString();
            var det = summary.GetDetails();
        }
    }
}