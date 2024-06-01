using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Models
{
    public enum AdjustPriceType
    {
        [Description("未设置")]
        Unset = 0,

        [Description("前复权")]
        Pre,

        [Description("后复权")]
        Post
    }
}
