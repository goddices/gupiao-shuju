using StockStudy.Models; 

namespace StockStudy.Mappers
{
    public interface IAdjustPriceMapper
    {
        string GetAdjustPriceParameterValue(AdjustPriceType adjust); 
    }
}
