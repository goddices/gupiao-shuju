using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Models
{
    public class InvestmentSnapshot
    {
        public string? StockName { get; set; }

        public int TotalDays { get; set; }

        public decimal FinalAmount { get; set; }

        public decimal CostAmount { get; set; }

        public decimal Earnings => FinalAmount - CostAmount;

        public decimal Rate => Earnings / CostAmount;

        public override string ToString()
        {
            return $"投资{StockName} {TotalDays}天（{(TotalDays / 365M).ToString("0.00")}年), 赚了{Earnings.ToString("0.00")}, 收益率 {(Rate * 100).ToString("0.00")}%, 市值 {FinalAmount.ToString("0.00")}, 成本 {CostAmount.ToString("0.00")}";
        }
    }
}
