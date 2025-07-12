using System.ComponentModel; 

namespace StockStudy.Models
{
    /// <summary>
    /// 复权价类型 
    /// </summary>
    public enum AdjustPriceType
    {
        [Description("不复权")]
        None = 0,

        [Description("前复权")]
        Pre,

        [Description("后复权")]
        Post
    }
}
