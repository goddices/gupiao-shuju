namespace StockStudy.Models
{
    public class InvestmentSummary
    {
        public InvestmentSummary(string strategyName, StockQuote quote, IEnumerable<TradingSnapshot> tradingSnapshots)
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

        public decimal HoldingValue { get; set; }

        public decimal Cost { get; set; }

        public decimal Earnings => HoldingValue - Cost;

        public decimal Rate => Earnings / Cost;

        public IEnumerable<TradingSnapshot> TradingSnapshots { get; set; }
        public StockQuoteLine First { get; set; }
        public StockQuoteLine Last { get; set; }

        public decimal? Holdings => TradingSnapshots.Last()?.HoldingShares;

        public decimal BaseEarnings => Holdings * (Last.Close - First.Close) ?? 0;

        public decimal OverEarnings => Earnings - BaseEarnings;


        public override string ToString()
        {
            return $"投资{StockName} {TotalDays}天({(TotalDays / 365M):0.00}年), 持仓: {Holdings:0.000}, 市值: {HoldingValue:0.000}, 成本 {Cost:0.000}  {Environment.NewLine}" +
                $"期初价格: {First.Close:0.000}，期末价格: {Last.Close:0.000}, 基准收益: {BaseEarnings:0.000}, 基准收益率: {(Last.Close - First.Close) / Last.Close:0.000%} {Environment.NewLine}" +
                $"采用 {StrategyName} 赚了{Earnings:0.000}, 收益率: {(Rate * 100):0.000}%, 超额收益: {OverEarnings:0.000},超额收益率:{OverEarnings / BaseEarnings:0.000%} ";

        }

        public IEnumerable<string> GetDetails()
        {
            return TradingSnapshots.Select(e => e.ToString());
        }
    }
}