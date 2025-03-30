using StockStudy.Models;

namespace StockStudy.Core
{
    public class DefaultTrader : ITrader
    {
        private readonly IDictionary<string, decimal> _holdings = new Dictionary<string, decimal>();
        private decimal _availableCash;
        private decimal _buyLossFactor;
        private decimal _sellLossFactor;

        public IDictionary<string, decimal> Holdings => _holdings;

        public decimal AvailableCash { get => _availableCash; set => _availableCash = value; }

        public decimal InitialCash { get; set; }

        public void Reset()
        {
            _availableCash = 0;
            _holdings.Clear();
        }

        public void SetInitialParameters(decimal availableCash, decimal buyLossFactor, decimal sellLossFactor)
        {
            if (availableCash <= 0) throw new ArgumentOutOfRangeException(nameof(availableCash), "availableCash must > 0");
            if (buyLossFactor >= 1) throw new ArgumentOutOfRangeException(nameof(buyLossFactor), "buyLossFactor must < 1");
            if (sellLossFactor >= 1) throw new ArgumentOutOfRangeException(nameof(sellLossFactor), "sellLossFactor must < 1");

            _availableCash = availableCash;
            _buyLossFactor = buyLossFactor;
            _sellLossFactor = sellLossFactor;
        }

        public TransactionRecord? BuySingleTarget(string target, DateTime tradingDate, decimal price, decimal volume)
        {
            EnsureTargetHoldings(target);
            var total = price * volume * (1 + _buyLossFactor);
            if (total <= _availableCash)
            {
                _availableCash -= total;
                _holdings[target] += volume;

                return new TransactionRecord(
                    GenerateUniqueId(tradingDate),
                    target,
                    tradingDate,
                    TransactionDirection.Buy,
                    price,
                    volume,
                    price * volume * _buyLossFactor);
            }
            return null;
        }

        public TransactionRecord? SellSingleTarget(string target, DateTime tradingDate, decimal price, decimal volume)
        {
            EnsureTargetHoldings(target);

            if (volume <= _holdings[target])
            {
                _holdings[target] -= volume;
                _availableCash += price * volume * (1 - _sellLossFactor);

                return new TransactionRecord(
                    GenerateUniqueId(tradingDate),
                    target,
                    tradingDate,
                    TransactionDirection.Sell,
                    price,
                    volume,
                    price * volume * _sellLossFactor);
            }
            return null;
        }

        private static string GenerateUniqueId(DateTime tradingDate) => Guid.NewGuid().ToString();

        private void EnsureTargetHoldings(string target)
        {
            if (!_holdings.ContainsKey(target))
            {
                _holdings.Add(target, 0);
            }

        }

        public decimal EstimateBuyingAmount(decimal price, decimal volume)
        {
            return price * volume * (1 + _buyLossFactor);
        }

        public decimal EstimateSellingAmount(decimal price, decimal volume)
        {
            return price * volume * (1 - _sellLossFactor);
        }
    }
}
