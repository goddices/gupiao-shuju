using static System.Runtime.InteropServices.JavaScript.JSType;

namespace StockStudy
{
    public static class MathExtensions
    {
        public static decimal StandardDeviation(this IEnumerable<decimal> priceList)
        {
            var count = priceList.Count();
            if (priceList == null || count == 0) return 0;

            decimal mean = priceList.Average();
            decimal sumSq = 0;

            foreach (var value in priceList)
            {
                decimal diff = value - mean;
                sumSq += diff * diff;
            }

            // 转换为 double 计算平方根
            double stdDev = Math.Sqrt((double)(sumSq / count));
            return (decimal)stdDev;
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
