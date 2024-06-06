using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using StockStudy.Storage; 

namespace StockStudy
{
    public static class InitServiceExtensions
    {
        public static void InitService(this IServiceProvider provider)
        {
            var context = provider.GetRequiredService<LocalDbContext>();
            context.Database.Migrate();
        }
    }
}
