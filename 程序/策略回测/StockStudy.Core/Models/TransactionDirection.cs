using System.ComponentModel;

namespace StockStudy.Models
{
    public enum TransactionDirection
    {
        [Description("未知")]
        None = 0,
        [Description("买入")]
        Buy,
        [Description("卖出")]
        Sell
    }
}
