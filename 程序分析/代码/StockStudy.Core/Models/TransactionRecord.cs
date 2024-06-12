namespace StockStudy.Models
{
    public class TransactionRecord
    {
        public TransactionRecord(string uniqueId,
            string transactionTarget,
            DateTime transactionDate,
            TransactionDirection direction,
            decimal price, decimal volume)
        {
            UniqueId = uniqueId;
            TransactionTarget = transactionTarget;
            TransactionDate = transactionDate;
            Direction = direction;
            Price = price;
            Volume = volume;
            Amount = price * volume;
        }

        /// <summary>
        /// 唯一号
        /// </summary>
        public string UniqueId { get; set; }

        /// <summary>
        /// 交易日
        /// </summary>
        public DateTime TransactionDate { get; set; }

        /// <summary>
        /// 交易标的物
        /// </summary>
        public string TransactionTarget { get; set; }

        /// <summary>
        /// 成交价格
        /// </summary>
        public decimal Price { get; set; }

        /// <summary>
        /// 成交标的物数量
        /// </summary>
        public decimal Volume { get; set; }

        /// <summary>
        /// 成交金额
        /// </summary>
        public decimal Amount { get; set; }

        public TransactionDirection Direction { get; set; }
    }

}
