using Microsoft.EntityFrameworkCore.Metadata.Internal;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using StockStudy.Models;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Tests
{
    [TestClass]
    public class IndicatorsTests
    {
        // 2021年8月 开始的中国电信月K线收盘价数据
        private decimal[] closePriceArray = [
            3.70m,3.43m,3.53m,3.42m,3.47m,3.30m,3.26m,3.14m,3.03m,3.01m,3.04m,3.02m,3.06m,3.26m,3.36m,
            3.77m,3.62m,4.43m,5.28m,5.76m,6.12m,5.52m,5.14m,5.19m,5.41m,5.44m,4.98m,4.84m,5.06m,5.40m,
            5.50m,5.73m,5.65m,5.59m,5.89m,5.76m,5.84m,6.62m,6.27m,6.38m,7.13m,6.97m,7.66m,7.76m,7.60m,
            7.94m,7.75m,7.62m
            ];

        [TestMethod]
        public void BOLL_CalculatorTest()
        {
            var quote = new StockQuote
            (
                stockName: "中国电信",
                periodType: PeriodType.Monthly,
                quoteLines: closePriceArray.Select((e, index) => new StockQuoteLine
                {
                    TradeDate = new DateTime(2021, 8, 30).AddMonths(index),
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
        public void BOLL_DirectTest()
        {
            var (mb, ub, lb) = CalculateBollingerBands(closePriceArray, 20, 2m);

            Console.WriteLine("BOLL中轨");
            Console.WriteLine(mb.StringJoin());
            Console.WriteLine("BOLL上轨");
            Console.WriteLine(ub.StringJoin());
            Console.WriteLine("BOLL下轨");
            Console.WriteLine(lb.StringJoin());
        }

        private static (decimal[] MB, decimal[] UB, decimal[] LB) CalculateBollingerBands
            (decimal[] prices, int period = 20, decimal k = 2m)
        {
            int len = prices.Length;
            var MB = new decimal[len - period + 1];
            var UB = new decimal[len - period + 1];
            var LB = new decimal[len - period + 1];

            for (int i = period - 1; i < len; i++)
            {
                decimal sum = 0;
                for (int j = i - period + 1; j <= i; j++)
                    sum += prices[j];
                decimal mean = sum / period;

                decimal sqDiffSum = 0;
                for (int j = i - period + 1; j <= i; j++)
                {
                    var diff = prices[j] - mean;
                    sqDiffSum += diff * diff;
                }
                var sd = (decimal)Math.Sqrt((double)(sqDiffSum / period));

                MB[i - period + 1] = mean.Round4();
                UB[i - period + 1] = (mean + k * sd).Round4();
                LB[i - period + 1] = (mean - k * sd).Round4();
            }

            return (MB, UB, LB);
        }

        [TestMethod]
        public void RSI_CalculatorTest()
        {
            var quote = new StockQuote
                (
                    stockName: "中国电信",
                    periodType: PeriodType.Monthly,
                    quoteLines: closePriceArray.Select((e, index) => new StockQuoteLine
                    {
                        TradeDate = new DateTime(2021, 8, 30).AddMonths(index),
                        Close = e
                    })
                );
            var indicators = quote.CalculateIndicators();
            Console.WriteLine("收盘价序列");
            Console.WriteLine(closePriceArray.StringJoin());
            Console.WriteLine("RSI6");
            Console.WriteLine(indicators[StockIndicatorNames.RSI(6)].StringJoin());
        }

        [TestMethod]
        public void RSI_DirectTest()
        {
            var indicators = CalculateRSI(closePriceArray.ToList(), 6);
            Console.WriteLine("RSI6");
            Console.WriteLine(indicators.StringJoin());

            Console.WriteLine("RSI6平滑");
            Console.WriteLine(CalculateEMA(indicators, closePriceArray.Length).StringJoin());
        }

        // 计算 RSI（14日）
        private static List<decimal> CalculateRSI(List<decimal> prices, int period = 14)
        {
            var rsiList = new List<decimal>();
            if (prices.Count < period + 1) return rsiList;

            decimal avgGain = 0, avgLoss = 0;
            for (int i = period; i < prices.Count; i++)
            {
                List<decimal> gain = new List<decimal>(), loss = new List<decimal>();
                for (int j = i - period; j < i; j++)
                {
                    if (j == 0) continue; // 跳过第一个元素，因为没有前一个价格
                    decimal change = prices[j] - prices[j - 1];

                    if (change > 0)
                    {
                        gain.Add(change);
                        loss.Add(0);
                    }
                    else if (change < 0)
                    {
                        gain.Add(0);
                        loss.Add(-change);
                    }
                    else
                    {
                        gain.Add(0);
                        loss.Add(0);
                    }
                }
                if (i == period)
                {
                    // 第一次计算，直接使用平均值
                    avgGain = gain.Sum() / period;
                    avgLoss = loss.Sum() / period;
                }
                else
                {
                    // 后续计算使用前一周期的平均值
                    avgGain = (avgGain * (period - 1) + gain[period - 1]) / period;
                    avgLoss = (avgLoss * (period - 1) + loss[period - 1]) / period;
                }

                decimal rs = avgLoss == 0 ? 100 : avgGain / avgLoss;
                decimal rsi = 100 - (100 / (1 + rs));
                rsiList.Add(rsi.Round4());

            }

            return rsiList;
        }

        // 对 RSI 做 EMA 平滑处理（如5日）
        private static List<decimal> CalculateEMA(List<decimal> values, int period)
        {
            var emaList = new List<decimal>();
            if (values.Count == 0) return emaList;

            decimal alpha = 2m / (period + 1);
            emaList.Add(values[0]); // 初始值

            for (int i = 1; i < values.Count; i++)
            {
                decimal ema = alpha * values[i] + (1 - alpha) * emaList[i - 1];
                emaList.Add(ema.Round4());
            }

            return emaList;
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
