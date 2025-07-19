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

            int[] rsi_periods = [6, 12, 24];

            var lineArray = QuoteLines.ToArray();

            decimal average20 = 0, avgGain = 0, avgLoss = 0;

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
                        Indicators[StockIndicatorNames.BOLL_MIDDLE].Add(currentLine.TradeDate, bollma.Value); // BOLL中轨

                        var stddev = lineArray.Skip(index - boll_ma_period + 1).Take(boll_ma_period).Select(e => e.Close).StandardDeviation().Round4();
                        Indicators[StockIndicatorNames.BOLL_UPPER].Add(currentLine.TradeDate, bollma.Value + boll_K * stddev); // BOLL上轨
                        Indicators[StockIndicatorNames.BOLL_LOWER].Add(currentLine.TradeDate, bollma.Value - boll_K * stddev); // BOLL下轨
                    }
                }

                // RSI
                List<decimal> gain = new List<decimal>(), loss = new List<decimal>();
                foreach (var rsi_period in rsi_periods)
                {
                    if (index >= rsi_period) // 跳过前rsi_period才能计算RSI
                    {
                        for (int j = index - rsi_period; j < index; j++)
                        {
                            if (j == 0) continue; // 跳过第一个元素    
                            var change = lineArray[j].Close - lineArray[j - 1].Close;
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
                        if (index == rsi_period)
                        {
                            // 第一次计算，直接使用平均值
                            avgGain = gain.Sum() / rsi_period;
                            avgLoss = loss.Sum() / rsi_period;
                        }
                        else
                        {
                            // 后续计算使用前一周期的平均值
                            avgGain = (avgGain * (rsi_period - 1) + gain[rsi_period - 1]) / rsi_period;
                            avgLoss = (avgLoss * (rsi_period - 1) + loss[rsi_period - 1]) / rsi_period;
                        }
                        decimal rs = avgLoss == 0 ? 100 : avgGain / avgLoss;
                        decimal rsi = 100 - (100 / (1 + rs));
                        Indicators[StockIndicatorNames.RSI(rsi_period)].Add(currentLine.TradeDate, rsi.Round4());

                    }
                }
            }
            return Indicators;
        }
    }
}
