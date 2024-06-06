using System.ComponentModel; 

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
