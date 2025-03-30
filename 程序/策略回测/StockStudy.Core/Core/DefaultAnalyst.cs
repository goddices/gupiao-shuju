using Microsoft.Extensions.DependencyInjection;
using StockStudy.Models;

namespace StockStudy.Core
{
    public class DefaultAnalyst : IAnalyst
    {
        private readonly IServiceProvider _serviceProvider;

        public DefaultAnalyst(IServiceProvider serviceProvider)
        {
            _serviceProvider = serviceProvider;
        }

        public IEnumerable<string> StrategyNames =>
            new IRegressionStrategy[]
            {
                _serviceProvider.GetRequiredService<DollarCostAveragingStrategy>(),
                _serviceProvider.GetRequiredService<MyPullbackStrategy>(),
                _serviceProvider.GetRequiredService<HighSellLowBuyStrategy>(),
            }.Select(e => e.Name);

        public IDictionary<string, InvestmentSummary> Analyze(StockQuote? quote)
        {
            using (var scope = _serviceProvider.CreateScope())
            {
                var engine = _serviceProvider.GetRequiredService<DefaultEngine>();
                var list = new IRegressionStrategy[]
                {
                    scope.ServiceProvider.GetRequiredService<DollarCostAveragingStrategy>(),
                    scope.ServiceProvider.GetRequiredService<MyPullbackStrategy>(),
                    scope.ServiceProvider.GetRequiredService<HighSellLowBuyStrategy>(),
                };
                if (quote == null ||
                    quote.QuoteLines == null ||
                    !quote.QuoteLines.Any() ||
                    quote.QuoteLines.Any(e => e == null))
                {
                    throw new ArgumentNullException(nameof(quote));
                }
                return list.ToDictionary(entry => entry.Name, entry => entry.InitializeParameters().Regress(quote));
            }
        }
    }
}
