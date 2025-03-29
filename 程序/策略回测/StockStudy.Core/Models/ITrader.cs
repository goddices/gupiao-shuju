namespace StockStudy.Models
{
    public interface ITrader
    {
        TransactionRecord? BuySingleTarget(string target, DateTime tradingDate, decimal price, decimal volume);

        TransactionRecord? SellSingleTarget(string target, DateTime tradingDate, decimal price, decimal volume);

        decimal EstimateBuyingAmount(decimal price, decimal volume);
        decimal EstimateSellingAmount(decimal price, decimal volume);

        IDictionary<string, decimal> Holdings { get; }
        decimal AvailableCash { get; set; }

        void SetInitialParameters(decimal availableCash, decimal buyLossFactor, decimal sellLossFactor);
    }
}
