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
            First = quote.QuoteLines.First();
            Last = quote.QuoteLines.Last();
        }

        public string? StrategyName { get; set; }

        public string? StockName { get; set; }

        public int TotalDays { get; set; }

        public decimal Final { get; set; }

        public decimal Cost { get; set; }

        public decimal Earnings => Final - Cost;

        public decimal Rate => Earnings / Cost;

        public IEnumerable<TradingSnapshot> TradingSnapshots { get; set; }
        public StockQuoteLine First { get; set; }
        public StockQuoteLine Last { get; set; }

        public decimal? Holdings => TradingSnapshots?.Last()?.StockHoldings?.First()?.HoldingShares;

        public decimal BaseEarnings => Holdings * (Last.Close - First.Close) ?? 0;

        public decimal OverEarnings => Final - BaseEarnings;


        public override string ToString()
        {
            return $"采用{StrategyName} 投资{StockName} {TotalDays}天（{(TotalDays / 365M).ToString("0.00")}年), " +
                $"赚了{Earnings.ToString("0.000")}, 收益率 {(Rate * 100).ToString("0.000")}%, {Environment.NewLine}" +
                $"持仓{Holdings:0.000} 市值 {Final.ToString("0.000")}, 成本 {Cost.ToString("0.000")} {Environment.NewLine}" +
                $"{StockName} 期始价格{First.Close:0.000}，期末价格{Last.Close:0.000},原本收益 {BaseEarnings:0.000}  超额收益 {OverEarnings:0.000}";
        }

        public IEnumerable<string> GetDetails()
        {
            return TradingSnapshots.Select(e => e.ToString());
        }
    }
}
