namespace StockStudy.Models
{
    public interface IAnalyst
    {
        /// <summary>
        /// 策略分析
        /// </summary>
        /// <param name="quotes">行情数据</param>
        /// <returns>最终结果，不带中间细节</returns>
        IDictionary<string, InvestmentSummary> Analyze(StockQuote? quote);

        IEnumerable<string> StrategyNames { get; }
    }
}
