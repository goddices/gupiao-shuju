using Microsoft.Extensions.Configuration;

namespace StockStudy.Configuration
{
    public static class ConfigurationHelper
    {
        public static IConfiguration BuildConfiguration()
        {
            var builder = new ConfigurationBuilder()
               .SetBasePath(Directory.GetCurrentDirectory())
               .AddJsonFile("appsettings.json")
               .AddJsonFile($"appsettings.{Environment.GetEnvironmentVariable("DOTNET_ENVIRONMENT")}.json", optional: true, reloadOnChange: false)
               ;
            return builder.Build();
        }
    }
}
