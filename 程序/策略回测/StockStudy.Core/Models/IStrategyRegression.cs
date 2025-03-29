using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Models
{
    public interface IStrategyRegression
    {
        string Code { get; }
        string Name { get; }
        InvestmentSnapshot Regress(StockQuote quote);
    }
}
