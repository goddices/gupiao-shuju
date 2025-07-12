namespace StockStudy.Models
{
    public class StockIndicatorNames
    {
        public static readonly string SMA5 = nameof(SMA5);
        public static readonly string SMA10 = nameof(SMA10);
        public static readonly string SMA20 = nameof(SMA20);
        public static readonly string EMA5 = nameof(EMA5);
        public static readonly string EMA10 = nameof(EMA10);
        public static readonly string EMA20 = nameof(EMA20);
        public static readonly string MACD = "MACD";
        public static readonly string RSI = "RSI";
        public static readonly string KDJ = "KDJ";
        public static readonly string BOLL_UPPER = "BOLL_UPPER";
        public static readonly string BOLL_LOWER = "BOLL_LOWER";

        public static string SMA(int period)
        {
            return $"SMA{period}";
        }
    }

    public class StockIndicators
    {
        private IDictionary<string, StockIndicatorEntryCollection> _indicatorStore = new Dictionary<string, StockIndicatorEntryCollection>();


        public StockIndicators()
        {
            // 初始化常用指标
            _indicatorStore[StockIndicatorNames.SMA5] = new StockIndicatorEntryCollection(StockIndicatorNames.SMA5);
            _indicatorStore[StockIndicatorNames.SMA10] = new StockIndicatorEntryCollection(StockIndicatorNames.SMA10);
            _indicatorStore[StockIndicatorNames.SMA20] = new StockIndicatorEntryCollection(StockIndicatorNames.SMA20);
            _indicatorStore[StockIndicatorNames.EMA5] = new StockIndicatorEntryCollection(StockIndicatorNames.EMA5);
            _indicatorStore[StockIndicatorNames.EMA10] = new StockIndicatorEntryCollection(StockIndicatorNames.EMA10);
            _indicatorStore[StockIndicatorNames.EMA20] = new StockIndicatorEntryCollection(StockIndicatorNames.EMA20);
            _indicatorStore[StockIndicatorNames.MACD] = new StockIndicatorEntryCollection(StockIndicatorNames.MACD);
            _indicatorStore[StockIndicatorNames.RSI] = new StockIndicatorEntryCollection(StockIndicatorNames.RSI);
            _indicatorStore[StockIndicatorNames.KDJ] = new StockIndicatorEntryCollection(StockIndicatorNames.KDJ);
            _indicatorStore[StockIndicatorNames.BOLL_UPPER] = new StockIndicatorEntryCollection(StockIndicatorNames.BOLL_UPPER);
            _indicatorStore[StockIndicatorNames.BOLL_LOWER] = new StockIndicatorEntryCollection(StockIndicatorNames.BOLL_LOWER);
        }

        public IEnumerable<StockIndicatorEntryCollection> GetAllIndicators()
        {
            return _indicatorStore.Values;
        }

        public StockIndicatorEntryCollection this[string name]
        {
            get
            {
                if (_indicatorStore.TryGetValue(name, out var entry))
                {
                    return entry;
                }
                throw new KeyNotFoundException($"Indicator '{name}' not found.");
            }
            set
            {
                _indicatorStore[name] = value;
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
            var sb = new System.Text.StringBuilder();
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
