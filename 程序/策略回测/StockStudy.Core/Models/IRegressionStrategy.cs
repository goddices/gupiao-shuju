using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Models
{
    public interface IRegressionStrategy
    {  
        string Code { get; }

        string Name { get; }

        InvestmentSummary Regress(StockQuote quote);
    }
}
