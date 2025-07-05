using System.Collections;
using System.Text;

namespace StockStudy.Models
{
    public class StockIndicatorNames
    {
        public static readonly string MA5 = "MA5";
        public static readonly string MA10 = "MA10";
        public static readonly string MA20 = "MA20";
        public static readonly string MACD = "MACD";
        public static readonly string RSI = "RSI";
        public static readonly string KDJ = "KDJ";
        public static readonly string BOLL_TOP = "BOLL_TOP";
        public static readonly string BOLL_BTM = "BOLL_BTM";

        public static string MA(int period)
        {
            return $"MA{period}";
        }
    }

    public class StockIndicators
    {
        private IDictionary<string, StockIndicatorEntryCollection> _map = new Dictionary<string, StockIndicatorEntryCollection>();


        public StockIndicators()
        {
            // 初始化常用指标
            _map[StockIndicatorNames.MA5] = new StockIndicatorEntryCollection(StockIndicatorNames.MA5);
            _map[StockIndicatorNames.MA10] = new StockIndicatorEntryCollection(StockIndicatorNames.MA10);
            _map[StockIndicatorNames.MA20] = new StockIndicatorEntryCollection(StockIndicatorNames.MA20);
            _map[StockIndicatorNames.MACD] = new StockIndicatorEntryCollection(StockIndicatorNames.MACD);
            _map[StockIndicatorNames.RSI] = new StockIndicatorEntryCollection(StockIndicatorNames.RSI);
            _map[StockIndicatorNames.KDJ] = new StockIndicatorEntryCollection(StockIndicatorNames.KDJ);
            _map[StockIndicatorNames.BOLL_TOP] = new StockIndicatorEntryCollection(StockIndicatorNames.BOLL_TOP);
            _map[StockIndicatorNames.BOLL_BTM] = new StockIndicatorEntryCollection(StockIndicatorNames.BOLL_BTM);
        }

        public IEnumerable<StockIndicatorEntryCollection> GetAllIndicators()
        {
            return _map.Values;
        }

        public StockIndicatorEntryCollection this[string name]
        {
            get
            {
                if (_map.TryGetValue(name, out var entry))
                {
                    return entry;
                }
                throw new KeyNotFoundException($"Indicator '{name}' not found.");
            }
            set
            {
                _map[name] = value;
            }
        }

    }

    public class StockIndicatorEntryCollection : List<StockIndicatorEntry>
    {
        public StockIndicatorEntryCollection(string name)
        {
            Name = name;
        }

        public string Name { get; set; } = string.Empty;

        public void Add(DateTime tradeDate, decimal value)
        {
            this.Add(new StockIndicatorEntry { TradeDate = tradeDate, Value = value });
        }

        public decimal GetValue(DateTime tradeDate)
        {
            var entry = this.FirstOrDefault(e => e.TradeDate == tradeDate);
            if (entry != null)
            {
                return entry.Value;
            }
            throw new KeyNotFoundException($"No entry found for date {tradeDate}.");
        }

        public override string ToString()
        {
            var sb = new StringBuilder();
            foreach (var entry in this)
            {
                sb.AppendLine(entry.ToString());
            }
            return sb.ToString();
        }
    }

    public class StockIndicatorEntry
    {
        public DateTime TradeDate { get; set; }
        public decimal Value { get; set; }
        override public string ToString()
        {
            return $"{TradeDate:yyyy-MM-dd} {Value}";
        }
    }
}
