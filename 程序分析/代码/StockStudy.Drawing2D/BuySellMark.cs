using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Drawing2D
{
    public class BuySellMark
    {
        public enum BuySell
        {
            Buy,Sell
        }

        public DateTime DateTime { get; set; }
        public decimal Price {  get; set; }     
        public BuySell Direction { get; set; }
    }
}
