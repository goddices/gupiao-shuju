using StockStudy.Extensions;

namespace StockStudy.Models
{
    /// <summary>
    /// 
    /// </summary>
    public class TradingSnapshot
    {
        /// <summary>
        /// 交易日
        /// </summary>
        public DateTime TradeDate { get; set; }

        /// <summary>
        /// 现金余额
        /// </summary>
        public decimal AvailableCash { get; set; }
        /// <summary>
        /// 持有股票名
        /// </summary>
        public string? StockName { get; set; }

        /// <summary>
        /// 持有股数
        /// </summary>
        public decimal HoldingShares { get; set; }

        /// <summary>
        /// 当前价格
        /// </summary>
        public decimal TradePrice { get; set; }

        /// <summary>
        /// 成交数量
        /// </summary>
        public decimal TradeVolume { get; set; }

        /// <summary>
        /// 交易方向
        /// </summary>
        public TransactionDirection TradeDirection { get; set; }

        public string GetDetail()
        {
            return $"{TradeDirection.GetDesciption()}{StockName}了{TradeVolume:0.00}，价格为 {TradePrice:0.00}，持有{HoldingShares:0.00}";
        }


        public override string ToString()
        {
            var details = string.Join(Environment.NewLine, GetDetail());
            return $"在{TradeDate:yyyy-MM-dd} {details}  现金余额：{AvailableCash:0.00}";
        }

    }
}
