using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Models
{
    public class StockQuoteLine
    {
        public DateTime TradeDay { get; set; }
        public decimal Open { get; set; }
        public decimal Close { get; set; }
        public decimal High { get; set; }
        public decimal Low { get; set; }
        public decimal Percentage { get; set; }
        public decimal RaiseAmount { get; set; }
        public decimal DealedAmount { get; set; }
    }
}
