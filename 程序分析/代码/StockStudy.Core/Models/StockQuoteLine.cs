namespace StockStudy.Models
{
    public class StockQuoteLine
    {
        /// <summary>
        /// 交易日
        /// </summary>
        public DateTime TradeDay { get; set; }

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

        /// <summary>
        /// 涨跌幅 %
        /// </summary>
        public decimal ChangePercent { get; set; }

        /// <summary>
        /// 涨跌额
        /// </summary>
        public decimal ChangeVolume { get; set; }

        /// <summary>
        /// 成交额
        /// </summary>
        public decimal TradeVolume { get; set; }
    }
}
