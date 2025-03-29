using Microsoft.EntityFrameworkCore.Design;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration; 
using StockStudy.Configuration;

namespace StockStudy.Storage
{
    public class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<LocalDbContext>
    {
        private readonly IConfiguration _configuration;

        public DesignTimeDbContextFactory()
        {
            _configuration = ConfigurationHelper.BuildConfiguration();
        }

        public LocalDbContext CreateDbContext(string[] args)
        {
            var builder = new DbContextOptionsBuilder<LocalDbContext>();
            builder.UseSqlite(_configuration.GetConnectionString(GlobalConstants.DbConnStrName));
            return new LocalDbContext(builder.Options);
        }
    }
}
