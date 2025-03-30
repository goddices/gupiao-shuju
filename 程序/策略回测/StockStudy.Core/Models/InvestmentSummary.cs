namespace StockStudy.Models
{
    public class InvestmentSummary
    {
        public InvestmentSummary(string strategyName, StockQuote quote, IEnumerable<TradingSnapshot> tradingSnapshots)
        {
            StockName = quote.StockName;
            StrategyName = strategyName;
            TotalDays = (int)(quote.QuoteLines.Last().TradeDate - quote.QuoteLines.First().TradeDate).TotalDays;
            TradingSnapshots = tradingSnapshots.ToList();
            First = quote.QuoteLines.First();
            Last = quote.QuoteLines.Last();
        }

        public string? StrategyName { get; set; }

        public string? StockName { get; set; }

        public IEnumerable<TradingSnapshot> TradingSnapshots { get; set; }

        public StockQuoteLine First { get; set; }

        public StockQuoteLine Last { get; set; }

        public int TotalDays { get; set; }

        public decimal Holdings { get; set; }

        public decimal Cost { get; set; }

        public decimal InitialCash { get; set; }

        public decimal AvailableCash { get; set; }

        public decimal HoldingValue => Holdings * Last.Close;

        public decimal Earnings => HoldingValue + AvailableCash - Cost;

        public decimal BaseEarnings => Holdings * (Last.Close - First.Close);

        public decimal OverEarnings => Earnings - (BaseEarnings + AvailableCash);

        public decimal Rate => Cost == 0 ? 0 : Earnings / Cost;

        public string GetSummary()
        {
            return
                Holdings == 0 ?
                $"采用【{StrategyName}】投资【{StockName}】{TotalDays}天({(TotalDays / 365M):0.00}年), 持仓: {Holdings:0.000}, 可用现金: {AvailableCash:0.000}, 市值: {HoldingValue:0.000} {Environment.NewLine}" +
                $"成本 {Cost:0.000}, 赚了{Earnings:0.000}, 收益率: {(Rate * 100):0.000}% {Environment.NewLine}" +
                $"基准期初价格: {First.Close:0.000}, 期末价格: {Last.Close:0.000}, 基准收益率: {(Last.Close - First.Close) / Last.Close:0.000%} {Environment.NewLine}" +
                $"{StrategyName}的超额收益: {OverEarnings:0.000}" 
                :
                $"采用【{StrategyName}】投资【{StockName}】{TotalDays}天({(TotalDays / 365M):0.00}年), 持仓: {Holdings:0.000}, 可用现金: {AvailableCash:0.000}, 市值: {HoldingValue:0.000} {Environment.NewLine}" +
                $"成本 {Cost:0.000}, 赚了{Earnings:0.000}, 收益率: {(Rate * 100):0.000}% {Environment.NewLine}" +
                $"【基准】期初价格: {First.Close:0.000}, 期末价格: {Last.Close:0.000}, 基准收益: {BaseEarnings:0.000}, 基准收益率: {(Last.Close - First.Close) / Last.Close:0.000%} {Environment.NewLine}" +
                $"【{StrategyName}】的超额收益: {OverEarnings:0.000}, 超额收益率:{OverEarnings / BaseEarnings:0.000%} ";

        }

        public IEnumerable<string> GetDetails()
        {
            return TradingSnapshots.Select(e => e.ToString());
        }
    }
}