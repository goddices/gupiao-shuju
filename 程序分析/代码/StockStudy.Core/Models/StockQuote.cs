using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Models
{
    public class StockQuote
    {
        public StockQuote()
        {

        }

        public StockQuote(string stockName, PeriodType periodType, IEnumerable<StockQuoteLine> quoteLines)
        {
            StockName = stockName;
            PeriodType = periodType;
            QuoteLines = quoteLines;
        }

        public string StockName { get; set; }

        public PeriodType PeriodType { get; set; }

        public IEnumerable<StockQuoteLine> QuoteLines { get; set; }
    }
}
