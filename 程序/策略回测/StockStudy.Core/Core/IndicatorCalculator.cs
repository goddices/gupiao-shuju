using StockStudy.Models;

namespace StockStudy.Core
{
    public class IndicatorCalculator
    {
        public StockIndicators Calculate(StockIndicators Indicators, StockQuoteLine[] QuoteLines)
        {
            // 计算指标 
            int[] ma_periods = [5, 10, 20];
            var boll_ma_period = 20;
            var boll_K = 2;

            var rsi_period = 6;
            var div = rsi_period - 1;
            var firstDay = false;
            decimal avgGain = 0, avgLoss = 0;

            var lineArray = QuoteLines.ToArray();

            decimal average20 = 0;
            for (int index = 0; index < lineArray.Length; index++)
            {
                var currentLine = lineArray[index];
                // MA5, MA10, MA20, MACD, RSI, KDJ 等等

                foreach (var period in ma_periods)
                {
                    var alpha = 2m / (period + 1);

                    if (index + 1 >= period)
                    {
                        Indicators[StockIndicatorNames.SMA(period)].Add(
                            currentLine.TradeDate,
                            lineArray.Skip(index - period + 1).Take(period).Average(e => e.Close).Round4()
                        );

                        if (index > period)
                        {
                            average20 = alpha * currentLine.Close + (1 - alpha) * average20;
                        }
                        else
                        {
                            average20 = Indicators[StockIndicatorNames.SMA(period)].GetValue(currentLine.TradeDate);
                        }

                        Indicators[StockIndicatorNames.EMA20].Add(
                            currentLine.TradeDate,
                            average20.Round6()
                        );
                    }
                }

                // BOLL
                // MA20
                // BOLL上轨 = MA20 + 2 * stddev(20)
                // BOLL下轨 = MA20 - 2 * stddev(20)
                if (index + 1 >= boll_ma_period)
                {
                    var bollma = Indicators[StockIndicatorNames.SMA(boll_ma_period)].FirstOrDefault(e => e.TradeDate == currentLine.TradeDate);
                    if (bollma != null)
                    {
                        var ema20 = Indicators[StockIndicatorNames.EMA20].GetValue(currentLine.TradeDate);
                        var sma20 = Indicators[StockIndicatorNames.SMA20].GetValue(currentLine.TradeDate);
                        var stddev = lineArray.Skip(index - (boll_ma_period - 1)).Take(boll_ma_period).Select(e => e.Close).StandardDeviation(sma20).Round4();
                        Indicators[StockIndicatorNames.BOLL_UPPER].Add(currentLine.TradeDate, bollma.Value + boll_K * stddev); // BOLL上轨
                        Indicators[StockIndicatorNames.BOLL_LOWER].Add(currentLine.TradeDate, bollma.Value - boll_K * stddev); // BOLL下轨
                    }
                }

                // RSI

                if (index + 1 >= rsi_period) // 15Ks才能计算RSI
                {
                    var gains = new List<decimal>();
                    var losses = new List<decimal>();
                    for (int i = index - rsi_period + 1; i <= index; i++)
                    {
                        if (i == 0)
                        {
                            firstDay = true;
                            continue; // 跳过第一个元素 
                        }
                        var change = lineArray[i].Close - lineArray[i - 1].Close;
                        if (change > 0)
                        {
                            gains.Add(change);
                            losses.Add(0);
                        }
                        else
                        {
                            gains.Add(0);
                            losses.Add(-change);
                        }
                    }
                    if (firstDay)
                    {
                        avgGain = gains.Any() ? gains.Sum() / div : 0;
                        avgLoss = losses.Any() ? losses.Sum() / div : 0;
                    }
                    else
                    {
                        avgGain = (avgGain * div + gains.Last()) / rsi_period;
                        avgLoss = (avgLoss * div + losses.Last()) / rsi_period;
                    }
                    var rs = avgLoss == 0 ? 100 : avgGain / avgLoss;
                    var rsi = 100 - (100 / (1 + rs));
                    Indicators[StockIndicatorNames.RSI].Add(currentLine.TradeDate, rsi.Round4());

                    firstDay = false;
                }
            }
            return Indicators;
        }
    }
}
