namespace StockStudy.Models
{
    public class InvestmentSnapshot
    {
        public InvestmentSnapshot()
        {

        }

        public InvestmentSnapshot(string strategyName, StockQuote quote, IEnumerable<TradingSnapshot> tradingSnapshots)
        {
            StockName = quote.StockName;
            StrategyName = strategyName;
            TotalDays = (int)(quote.QuoteLines.Last().TradeDate - quote.QuoteLines.First().TradeDate).TotalDays;
            TradingSnapshots = tradingSnapshots;
        }

        public string? StrategyName { get; set; }

        public string? StockName { get; set; }

        public int TotalDays { get; set; }

        public decimal FinalAmount { get; set; }

        public decimal CostAmount { get; set; }

        public decimal Earnings => FinalAmount - CostAmount;

        public decimal Rate => Earnings / CostAmount;

        public IEnumerable<TradingSnapshot> TradingSnapshots { get; private set; }

        public override string ToString()
        {
            return $"采用{StrategyName} 投资{StockName} {TotalDays}天（{(TotalDays / 365M).ToString("0.00")}年), 赚了{Earnings.ToString("0.00")}, 收益率 {(Rate * 100).ToString("0.00")}%, 市值 {FinalAmount.ToString("0.00")}, 成本 {CostAmount.ToString("0.00")}";
        }

        public IEnumerable<string> GetDetails()
        {
            return TradingSnapshots.Select(e => e.ToString());
        }
    }
}
