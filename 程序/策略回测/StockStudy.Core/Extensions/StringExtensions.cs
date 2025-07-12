using StockStudy.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy
{
    public static class StringExtensions
    {
        public static string StringJoin(this IEnumerable<decimal> values)
        {
            return string.Join(',', values);
        }

        public static string StringJoin(this StockIndicatorEntryCollection coll)
        {
            return coll.OrderBy(e => e.TradeDate).Select(e => e.Value).StringJoin();
        }
    }
}
