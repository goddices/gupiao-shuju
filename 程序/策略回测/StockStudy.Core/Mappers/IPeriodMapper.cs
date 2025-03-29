using StockStudy.Models; 

namespace StockStudy.Mappers
{
    public interface IPeriodMapper
    {
        string GetPeriodTypeParamValue(PeriodType period);
    }
}
