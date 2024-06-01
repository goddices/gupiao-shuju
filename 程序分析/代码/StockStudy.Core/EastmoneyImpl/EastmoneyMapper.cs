using StockStudy.Mappers;
using StockStudy.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.EastmoneyImpl
{
    /// <summary>
    /// 选项类型映射，例如复权类型，K线类型
    /// </summary>
    public class EastmoneyMapper : IMappers
    {
        public string GetPeriodTypeParamValue(PeriodType period)
        {
            return period switch { PeriodType.Daily => "101", PeriodType.Weekly => "102", _ => string.Empty };
        }

        public string GetAdjustPriceParameterValue(AdjustPriceType adjust)
        {
            return adjust switch { AdjustPriceType.Pre => "1", AdjustPriceType.Post => "2", _ => string.Empty };
        }
    }
}
