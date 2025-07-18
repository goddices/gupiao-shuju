using Microsoft.Extensions.DependencyInjection;
using StockStudy.Configuration;
using StockStudy.Models;

namespace StockStudy.CmdApp
{
    internal class Program
    {
        static void Main(string[] args)
        {
            var provider = AddServices(new ServiceCollection()).BuildServiceProvider();
            var quoteReader = provider.GetRequiredService<IQuoteReader>();
            TaskMainAsync(quoteReader).Wait();
            Console.ReadLine();
        }

        static IServiceCollection AddServices(IServiceCollection services)
        {
            //register configuration 
            var configuration = ConfigurationHelper.BuildConfiguration();
            services.AddSingleton(configuration);
            services.AddAllServices(configuration);
            return services;
        }

        static async Task TaskMainAsync(IQuoteReader quoteReader)
        {
            var quo = await quoteReader.ReadQuoteAsync(
                Market.Shanghai,
                "601728",
                AdjustPriceType.Pre,
                PeriodType.Monthly);
            var indicators = quo!.CalculateIndicators();
            Console.WriteLine($"股票名称: {quo.StockName}, 周期: {quo.PeriodType}, 行情数据条数: {quo.QuoteLines.Count()}");
            Console.WriteLine("BOLL中轨");
            Console.WriteLine(indicators[StockIndicatorNames.SMA20].StringJoin());
            Console.WriteLine("BOLL上轨");
            Console.WriteLine(indicators[StockIndicatorNames.BOLL_UPPER].StringJoin());
            Console.WriteLine("BOLL下轨");
            Console.WriteLine(indicators[StockIndicatorNames.BOLL_LOWER].StringJoin());
            Console.WriteLine(Environment.NewLine);
            Console.WriteLine("RSI");
            Console.WriteLine(indicators[StockIndicatorNames.RSI].StringJoin());
        }
    }
}
