namespace StockStudy.Models
{
    public interface ITrader
    {
        IDictionary<string, decimal> Holdings { get; }

        decimal AvailableCash { get; set; }

        decimal InitialCash { get; set; }

        void Reset(); 

        void SetInitialParameters(decimal availableCash, decimal buyLossFactor, decimal sellLossFactor);

        TransactionRecord? BuySingleTarget(string target, DateTime tradingDate, decimal price, decimal volume);

        TransactionRecord? SellSingleTarget(string target, DateTime tradingDate, decimal price, decimal volume);

        decimal EstimateBuyingAmount(decimal price, decimal volume);

        decimal EstimateSellingAmount(decimal price, decimal volume);
    }
}
