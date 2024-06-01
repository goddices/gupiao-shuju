using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using StockStudy.Core;
using StockStudy.EastmoneyImpl;
using StockStudy.Models;
using StockStudy.Storage;

namespace StockStudy
{
    public static class ServiceCollectionExtensions
    {
        public static IServiceCollection AddAllServices(this IServiceCollection services, IConfiguration configuration)
        {
            if (configuration == null)
                throw new ArgumentNullException(nameof(configuration));

            var connectionString = configuration.GetConnectionString(GlobalConstants.DbConnStrName);
            if (string.IsNullOrWhiteSpace(connectionString))
                throw new ArgumentNullException(nameof(connectionString));

            return services.AddDbContextService(connectionString).AddCoreServices();
        }

        public static IServiceCollection AddDbContextService(this IServiceCollection services, string connectionString)
        {
            // register dbcontext
            return services.AddDbContext<LocalDbContext>(options => options.UseSqlite(connectionString));
        }

        public static IServiceCollection AddCoreServices(this IServiceCollection services)
        {
            return services
                .AddSingleton<IAnalyst, DefaultAnalyst>()
                .AddSingleton<IQuoteReader, EastmoneyQuoteReader>();
        }
    }
}
