namespace StockStudy.Models
{
    public interface IQuoteReader
    {
        /// <summary>
        /// 读取行情
        /// </summary>
        /// <param name="market">市场代码</param>
        /// <param name="code">公司代码</param>
        /// <param name="fqType">复权类型</param>
        /// <param name="periodType">周期</param>
        /// <returns>行情数据<seealso cref="StockQuote"/></returns>
        Task<StockQuote?> ReadQuoteAsync(string market, string code, AdjustPriceType fqType, PeriodType periodType, CancellationToken token = default);

        /// <summary>
        /// 从流中读取行情
        /// </summary>
        /// <param name="stream"></param>
        /// <returns>行情数据<seealso cref="StockQuote"/></returns>
        Task<StockQuote?> ReadQuoteAsync(Stream stream, CancellationToken token = default);

    }
}
