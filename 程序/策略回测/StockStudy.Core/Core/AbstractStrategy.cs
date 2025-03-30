using StockStudy.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Core
{
    public abstract class AbstractStrategy : IRegressionStrategy
    {
        private readonly DefaultEngine _engine;

        public AbstractStrategy(DefaultEngine engine)
        {
            _engine = engine;
        }

        public abstract string Code { get; }

        public abstract string Name { get; }

        protected DefaultEngine Engine => _engine;

        public IRegressionStrategy InitializeParameters()
        {
            return this;
        }

        public InvestmentSummary Regress(StockQuote quote)
        {
            RegressInternal(quote);
            var summary = _engine.CreateSummary(Name, quote);
            _engine.Reset();
            return summary;
        }

        protected abstract void RegressInternal(StockQuote quote);
    }
}
