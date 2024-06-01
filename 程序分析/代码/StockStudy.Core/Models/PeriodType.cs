using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Models
{
    public enum PeriodType
    {
        [Description("未设置")]
        Unset = 0,

        [Description("日K线")]
        Daily,

        [Description("五日K线")]
        FiveDay,

        [Description("周K线")]
        Weekly,

        [Description("月K线")]
        Monthly,

        [Description("年K线")]
        Year
    }
}
