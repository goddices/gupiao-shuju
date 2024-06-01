using StockStudy.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Mappers
{
    public interface IPeriodMapper
    {
        string GetPeriodTypeParamValue(PeriodType period);
    }
}
