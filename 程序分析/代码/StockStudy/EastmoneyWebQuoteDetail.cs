using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy
{
    public class EastmoneyWebQuote : IStockQuote
    {
        public string Name { get; set; }
        public IEnumerable<IStockQuoteDetail> Quotes { get; set; }
    }
    public class EastmoneyWebQuoteDetail : IStockQuoteDetail
    {
        public DateTime TradeDay { get; set; }
        public decimal Open { get; set; }
        public decimal Close { get; set; }
        public decimal High { get; set; }
        public decimal Low { get; set; }
        public decimal Percentage { get; set; }
        public decimal RaiseAmount { get; set; }
        public decimal DealedAmount { get; set; }

        public EastmoneyWebQuoteDetail()
        {

        }

        public EastmoneyWebQuoteDetail(string text)
        {
            var data = text.Split(',', StringSplitOptions.RemoveEmptyEntries);
            TradeDay = DateTime.Parse(data[0]);
            Open = Convert.ToDecimal(data[1]);
            Close = Convert.ToDecimal(data[2]);
            High = Convert.ToDecimal(data[3]);
            Low = Convert.ToDecimal(data[4]);
            Percentage = Convert.ToDecimal(data[5]);
            RaiseAmount = Convert.ToDecimal(data[6]);
            DealedAmount = Convert.ToDecimal(data[7]);
        }
    }
}
