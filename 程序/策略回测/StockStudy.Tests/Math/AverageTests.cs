using Microsoft.EntityFrameworkCore.Metadata.Internal;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using StockStudy.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Tests.Math
{
    [TestClass]
    public class AverageTests
    {
        private decimal[] closePriceArray = [
            3.70m,3.43m,3.53m,3.42m,3.47m,3.30m,3.26m,3.14m,3.03m,3.01m,3.04m,3.02m,3.06m,3.26m,3.36m,
            3.77m,3.62m,4.43m,5.28m,5.76m,6.12m,5.52m,5.14m,5.19m,5.41m,5.44m,4.98m,4.84m,5.06m,5.40m,
            5.50m,5.73m,5.65m,5.59m,5.89m,5.76m,5.84m,6.62m,6.27m,6.38m,7.13m,6.97m,7.66m,7.76m,7.60m,
            7.94m,7.75m,7.52m
            ];

        [TestMethod]
        public void BollTest()
        {
            var quote = new StockQuote
            (
                stockName: "中国电信",
                periodType: PeriodType.Monthly,
                quoteLines: closePriceArray.Select((e,index) => new StockQuoteLine
                {
                    TradeDate = DateTime.Now.Date.AddMonths(-closePriceArray.Length - index),
                    Close = e
                })
            );
            var indicators = quote.CalculateIndicators();
            Console.WriteLine("收盘价序列");
            Console.WriteLine(closePriceArray.StringJoin());
            Console.WriteLine("BOLL中轨");
            Console.WriteLine(indicators[StockIndicatorNames.SMA20].StringJoin());
            Console.WriteLine("BOLL上轨");
            Console.WriteLine(indicators[StockIndicatorNames.BOLL_UPPER].StringJoin());
            Console.WriteLine("BOLL下轨");
            Console.WriteLine(indicators[StockIndicatorNames.BOLL_LOWER].StringJoin());
        }

        [TestMethod]
        public void SMATest()
        {
            int period = 5; // 5日均线
            var sma = new List<decimal>();
            for (int index = 0; index < closePriceArray.Length; index++)
            {
                if (index + 1 >= period)
                {
                    sma.Add(closePriceArray.Skip(index - period + 1).Take(period).Average());
                }
            }

            Console.WriteLine("SMA: " + string.Join(",", sma.Select(e => e.Round4())));
        }

        [TestMethod]
        public void EMATest()
        {
            int period = 5; // 5日均线
            decimal alpha = 2m / (period + 1); // EMA的平滑系数，5日EMA
            var ema = new List<decimal>();
            decimal average = 0;
            for (int index = 0; index < closePriceArray.Length; index++)
            {
                if (index + 1 >= period)
                {
                    if (index == period)
                        average = closePriceArray.Skip(index - period + 1).Take(period).Average();
                    else
                        average = alpha * closePriceArray[index] + (1 - alpha) * average;
                    ema.Add(average);
                }
            }

            Console.WriteLine("EMA: " + string.Join(",", ema.Select(e => e.Round4())));
        }
    }
}
