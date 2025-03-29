using Microsoft.Extensions.DependencyInjection;
using StockStudy.Models;

namespace StockStudy.Core
{
    public class DefaultAnalystEngine : IAnalyst
    {
        private IDictionary<string, IStrategyRegression> _strategyDict;

        public DefaultAnalystEngine(IServiceProvider serviceProvider)
        {
            _strategyDict = new IStrategyRegression[]
            {
                serviceProvider.GetRequiredService<TestStrategyRegression>(),
                serviceProvider.GetRequiredService<DollarCostAveragingStrategyRegression>(),
                serviceProvider.GetRequiredService<MyPullbackStrategyRegression>(),
            }.ToDictionary(k => k.Name, k => k);
        }

        public IEnumerable<string> StrategyCodeList => _strategyDict.Keys;

        public InvestmentSnapshot StrategyAnalyze(string strategyCode, StockQuote? quote)
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

        private IStrategyRegression SelectStrategy(string code)
        {
            if (!StrategyCodeList.Contains(code))
                throw new NotSupportedException($"不支持这个{code}的策略");
            return _strategyDict[code];
        }
    }
}
