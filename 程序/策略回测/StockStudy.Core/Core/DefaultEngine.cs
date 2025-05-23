﻿using StockStudy.Models;

namespace StockStudy.Core
{
    public class DefaultEngine
    {
        protected readonly ITrader _trader;

        protected readonly IList<TradingSnapshot> _tradingSnapshots = new List<TradingSnapshot>();
        protected readonly IList<TransactionRecord> _transactionList = new List<TransactionRecord>();

        public DefaultEngine(ITrader trader)
        {
            _trader = trader;
        }

        public void Buy(string target, DateTime tradeDate, decimal price, decimal volumn)
        {
            var record = _trader.BuySingleTarget(target, tradeDate, price, volumn);
            if (record != null)
            {
                _transactionList.Add(record);
                _tradingSnapshots.Add(new TradingSnapshot
                {
                    TradeDate = tradeDate,
                    AvailableCash = volumn,
                    TradePrice = price,
                    HoldingShares = _trader.Holdings[target],
                    StockName = target,
                    TradeVolume = record.Volume,
                    TradeDirection = record.Direction,
                });
            }
        }

        public void Sell(string target, DateTime tradeDate, decimal price, decimal volumn)
        {
            var record = _trader.SellSingleTarget(target, tradeDate, price, volumn);
            if (record != null)
            {
                _transactionList.Add(record);
                _tradingSnapshots.Add(new TradingSnapshot
                {
                    TradeDate = tradeDate,
                    AvailableCash = volumn,
                    TradePrice = price,
                    HoldingShares = _trader.Holdings[target],
                    StockName = target,
                    TradeVolume = record.Volume,
                    TradeDirection = record.Direction,
                });
            }
        }

        public InvestmentSummary CreateSummary(string strategyName, StockQuote quote)
        {
            return new InvestmentSummary(strategyName, quote, _tradingSnapshots)
            {
                Cost = _transactionList.Sum(e => e.Amount)+ _trader.AvailableCash,
                Holdings = _trader.Holdings[quote.StockName],
                AvailableCash = _trader.AvailableCash,
                InitialCash = _trader.InitialCash,
            };
        }

        public void Deposit(decimal amount)
        {
            _trader.AvailableCash += amount;
        }

        public void Deposit(decimal price, decimal volume)
        {
            var total = _trader.EstimateBuyingAmount(price, volume);
            Deposit(total);
        }

        public void Withdraw(decimal amount)
        {
            _trader.AvailableCash -= amount;
        }

        public void Withdraw(decimal price, decimal volume)
        {
            var total = _trader.EstimateSellingAmount(price, volume);
            Withdraw(total);
        }

        public void Reset()
        {
            _trader.Reset();
            _tradingSnapshots.Clear();
            _transactionList.Clear();
        }
    }
}
