using StockStudy.Core;

namespace StockStudy.Models
{
    public class StockQuote
    {

        public StockQuote(string stockName, PeriodType periodType, IEnumerable<StockQuoteLine> quoteLines)
        {
            StockName = stockName;
            PeriodType = periodType;
            QuoteLines = quoteLines;
        }

        public string StockName { get; set; }

        public PeriodType PeriodType { get; set; }

        public IEnumerable<StockQuoteLine> QuoteLines { get; set; }

        public StockIndicators Indicators { get; set; } = new StockIndicators();

        public StockIndicators CalculateIndicators()
        {
            return new IndicatorCalculator().Calculate(Indicators, QuoteLines.ToArray());
        }
    }
}