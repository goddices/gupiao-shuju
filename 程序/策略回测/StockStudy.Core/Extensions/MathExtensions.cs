namespace StockStudy
{
    public static class MathExtensions
    {
        public static decimal StandardDeviation(this IEnumerable<decimal> priceList, decimal average)
        {
            // 各个软件中BOLL指标误差较大 两位小数
            if (!priceList.Any()) return 0; // 如果没有数据，返回0
            
            var sqrt = Math.Sqrt(Convert.ToDouble(priceList.Select(price => price - average).Select(e => e * e).Sum()) / Convert.ToDouble(priceList.Count()));
            return Convert.ToDecimal(sqrt);
        }

        public static decimal Round2(this decimal value)
        {
            return value.Round(2);
        }

        public static decimal Round4(this decimal value)
        {
            return value.Round(4);
        }
        public static decimal Round6(this decimal value)
        {
            return value.Round(6);
        }

        public static decimal Round(this decimal value, int decimals)
        {
            return Math.Round(value, decimals, MidpointRounding.AwayFromZero);
        }
    }
}
