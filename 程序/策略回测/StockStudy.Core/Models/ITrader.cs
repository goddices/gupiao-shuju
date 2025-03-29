namespace StockStudy.Models
{
    public interface ITrader
    {
        TransactionRecord DoBuy(string target, DateTime tradingDate, decimal price, decimal volume);

        TransactionRecord? TryBuy(string target, DateTime tradingDate, decimal availableCash, decimal price);

        TransactionRecord DoSell(string target, DateTime tradingDate, decimal price, decimal volume);

        TransactionRecord? TrySell(string target, DateTime tradingDate, decimal availableHoldings, decimal price);

    }
}
