using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy
{
    public interface IStockQuote
    {
        public string Name { get; set; }
        public IEnumerable<IStockQuoteDetail> Quotes { get; set; }
    }

    public interface IStockQuoteDetail
    {
        public DateTime TradeDay { get; set; }
        public decimal Open { get; set; }
        public decimal Close { get; set; }
        public decimal High { get; set; }
        public decimal Low { get; set; }
    }
}
