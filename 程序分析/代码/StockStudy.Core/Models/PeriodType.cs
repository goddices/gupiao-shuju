using System.ComponentModel; 

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
