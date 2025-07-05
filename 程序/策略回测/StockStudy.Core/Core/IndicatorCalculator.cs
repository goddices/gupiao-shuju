using StockStudy.Models;

namespace StockStudy.Core
{
    public static class StockQuoteExtensions
    {
        public static decimal StandardDeviation(this IEnumerable<decimal> priceList, decimal ma)
        {
            // 各个软件中BOLL指标误差较大 两位小数
            bool eqq = ma == priceList.Average();
            if (!priceList.Any()) return 0; // 如果没有数据，返回0
            var sqrt = Math.Sqrt(Convert.ToDouble(priceList.Select(price => price - priceList.Average()).Select(e => e * e).Sum()) / Convert.ToDouble(priceList.Count()));
            return Convert.ToDecimal(sqrt);
        }

        public static decimal Round2(this decimal value)
        {
            return Math.Round(value, 2, MidpointRounding.AwayFromZero);
        }
        public static decimal Round4(this decimal value)
        {
            return Math.Round(value, 4, MidpointRounding.AwayFromZero);
        }
    }

    public class IndicatorCalculator
    {
        public StockIndicators Calculate(StockIndicators Indicators, StockQuoteLine[] QuoteLines)
        {
            // 计算指标 
            int[] ma_periods = [5, 10, 20];
            var lineArray = QuoteLines.ToArray();
            for (int index = 0; index < lineArray.Length; index++)
            {
                var currentLine = lineArray[index];

                // MA5, MA10, MA20, MACD, RSI, KDJ 等等

                foreach (var period in ma_periods)
                {
                    if (index + 1 >= period)
                    {
                        Indicators[StockIndicatorNames.MA(period)].Add(
                            currentLine.TradeDate,
                            lineArray.Skip(index - period + 1).Take(period).Average(e => e.Close).Round4()
                        );
                    }
                }

                // BOLL
                // MA20
                // BOLL上轨 = MA20 + 2 * stddev(20)
                // BOLL下轨 = MA20 - 2 * stddev(20)
                var boll_ma_period = 20;
                if (index + 1 >= boll_ma_period)
                {
                    var ma20 = Indicators[StockIndicatorNames.MA(boll_ma_period)].FirstOrDefault(e => e.TradeDate == currentLine.TradeDate);
                    if (ma20 != null)
                    {
                        var stddev = lineArray.Skip(index - (boll_ma_period - 1)).Take(boll_ma_period).Select(e => e.Close).StandardDeviation(ma20.Value).Round4();
                        Indicators[StockIndicatorNames.BOLL_TOP].Add(currentLine.TradeDate, ma20.Value + 2 * stddev); // BOLL上轨
                        Indicators[StockIndicatorNames.BOLL_BTM].Add(currentLine.TradeDate, ma20.Value - 2 * stddev); // BOLL下轨
                    }
                }
            }
            return Indicators;
        }
    }
}
