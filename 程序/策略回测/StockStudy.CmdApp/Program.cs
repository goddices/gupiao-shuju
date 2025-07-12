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
            var a = quo!.CalculateIndicators();
        }
    }
}
