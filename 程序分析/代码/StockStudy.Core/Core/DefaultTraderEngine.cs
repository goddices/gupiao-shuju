using Microsoft.EntityFrameworkCore.Metadata.Internal;
using StockStudy.Models;

namespace StockStudy.Core
{
    public class DefaultTraderEngine : ITrader
    {

        public TransactionRecord? TryBuy(string target, DateTime tradingDate, decimal availableCash, decimal price)
        {
            var volume = MaxAvailableBuyingVolume(availableCash, price);
            if (volume > 0)
            {
                return new TransactionRecord(
                    GenerateUniqueId(tradingDate),
                    target,
                    tradingDate,
                    TransactionDirection.Buy,
                    price,
                    volume);
            }
            return null;
        }

        public TransactionRecord DoBuy(string target, DateTime tradingDate, decimal price, decimal volume)
        {
            return new TransactionRecord(
                GenerateUniqueId(tradingDate),
                target,
                tradingDate,
                TransactionDirection.Buy,
                price,
                volume);
        }

        public TransactionRecord? TrySell(string target, DateTime tradingDate, decimal availableHoldings, decimal price)
        {
            throw new NotImplementedException();
        }

        public TransactionRecord DoSell(string target, DateTime tradingDate, decimal price, decimal volume)
        {
            return new TransactionRecord(
                GenerateUniqueId(tradingDate),
                target,
                tradingDate,
                TransactionDirection.Sell,
                price,
                volume);
        }

        private static string GenerateUniqueId(DateTime tradingDate) => Guid.NewGuid().ToString();

        private static decimal MaxAvailableBuyingVolume(decimal availableCash, decimal targetPrice)
        {
            return availableCash / targetPrice;
        }
    }
}
