using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Drawing2D
{
    public class CandleStickEntry
    {
        public int CurrentIndex { get; set; }
        /// <summary>
        /// 交易日
        /// </summary>
        public DateTime TradeDate { get; set; }

        /// <summary>
        /// 开盘
        /// </summary>
        public decimal Open { get; set; }

        /// <summary>
        /// 收盘
        /// </summary>
        public decimal Close { get; set; }

        /// <summary>
        /// 最高
        /// </summary>
        public decimal High { get; set; }

        /// <summary>
        /// 最低
        /// </summary>
        public decimal Low { get; set; }

        public override string ToString()
        {
            return $"{TradeDate:yyyy-MM-dd} 开:{Open} 高:{High} 低:{Low} 收:{Close}";
        }
    }
}
