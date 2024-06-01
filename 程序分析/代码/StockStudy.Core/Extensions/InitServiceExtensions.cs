using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using StockStudy.Storage;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

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
