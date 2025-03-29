using Microsoft.Extensions.DependencyInjection;
using StockStudy.Models;

namespace StockStudy.Core
{
    public class DefaultAnalyst : IAnalyst
    {
        private IDictionary<string, IRegressionStrategy> _strategyDict;

        public DefaultAnalyst(IServiceProvider serviceProvider)
        {
            _strategyDict = new IRegressionStrategy[]
            {
                serviceProvider.GetRequiredService<DollarCostAveragingStrategy>(),
                serviceProvider.GetRequiredService<MyPullbackStrategy>(),
                serviceProvider.GetRequiredService<HighSellLowBuyStrategy>(),
            }.ToDictionary(k => k.Name, k => k);
        }

        public IEnumerable<string> StrategyList => _strategyDict.Keys;

        public InvestmentSummary Analyze(string strategyCode, StockQuote? quote)
        {
            if (quote == null ||
                quote.QuoteLines == null ||
                !quote.QuoteLines.Any() ||
                quote.QuoteLines.Any(e => e == null))
            {
                throw new ArgumentNullException(nameof(quote));
            }
            var strategy = SelectStrategy(strategyCode);
            return strategy.Regress(quote);
        }

        private IRegressionStrategy SelectStrategy(string code)
        {
            if (!StrategyList.Contains(code))
                throw new NotSupportedException($"不支持这个{code}的策略");
            return _strategyDict[code];
        }
    }
}
