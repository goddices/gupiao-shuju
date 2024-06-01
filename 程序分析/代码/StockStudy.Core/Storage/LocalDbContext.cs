using Microsoft.EntityFrameworkCore;
 
namespace StockStudy.Storage
{
    public class LocalDbContext : DbContext
    {
        public LocalDbContext(DbContextOptions<LocalDbContext> options) : base(options)
        {

        }
    }
}
