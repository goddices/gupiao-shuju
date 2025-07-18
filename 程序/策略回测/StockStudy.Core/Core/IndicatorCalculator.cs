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
                        var stddev = lineArray.Skip(index - boll_ma_period + 1).Take(boll_ma_period).Select(e => e.Close).StandardDeviation().Round4();
                        Indicators[StockIndicatorNames.BOLL_UPPER].Add(currentLine.TradeDate, bollma.Value + boll_K * stddev); // BOLL上轨
                        Indicators[StockIndicatorNames.BOLL_LOWER].Add(currentLine.TradeDate, bollma.Value - boll_K * stddev); // BOLL下轨
                    }
                }

                // RSI

                if (index >= rsi_period) // 跳过前rsi_period才能计算RSI
                {
                    decimal gain = 0, loss = 0;
                    for (int j = index - rsi_period + 1; j <= index; j++)
                    {
                        var change = lineArray[j].Close - lineArray[j - 1].Close;
                        if (change > 0) gain += change;
                        else loss -= change;
                    }
                    decimal avgGain = gain / rsi_period;
                    decimal avgLoss = loss / rsi_period;
                    decimal rs = avgLoss == 0 ? 100 : avgGain / avgLoss;
                    decimal rsi = 100 - (100 / (1 + rs));
                    Indicators[StockIndicatorNames.RSI].Add(currentLine.TradeDate, rsi.Round4());

                }
            }
            return Indicators;
        }
    }
}
