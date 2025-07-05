using Newtonsoft.Json.Linq;
using Newtonsoft.Json;
using StockStudy.Models;
using StockStudy.Mappers;

namespace StockStudy.EastmoneyImpl
{
    public class EastmoneyQuoteReader : IQuoteReader
    {
        private readonly HttpClient _httpClient = new HttpClient();
        private readonly IMappers _mappers;

        public EastmoneyQuoteReader(IMappers mappers)
        {
            _mappers = mappers;
        }

        public async Task<StockQuote?> ReadQuoteAsync(string market, string code, AdjustPriceType adjustType, PeriodType periodType, CancellationToken token = default)
        {
            if (token.IsCancellationRequested) return null;
            var fqt = _mappers.GetAdjustPriceParameterValue(adjustType);
            var klt = _mappers.GetPeriodTypeParamValue(periodType);
            var randomString = $"jQuery3510{Random.Shared.Next(1_0000_0000, 9_9999_9999)}_171{Random.Shared.Next(100_00000, 999_99999)}";
            var url = $"https://push2his.eastmoney.com/api/qt/stock/kline/get?cb={randomString}&secid={market}.{code}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt={klt}&fqt={fqt}&end=20500101&lmt=744&_=1716992167964";

            var resp = await _httpClient.GetAsync(url, token);
            if (resp.IsSuccessStatusCode)
            {
                var content = await resp.Content.ReadAsStringAsync(token);
                if (string.IsNullOrWhiteSpace(content))
                    return null;

                content = content
                    .Replace($"{randomString}(", string.Empty)
                    .Replace(");", string.Empty);
                return ConvertQuote(content, periodType);
            }
            return null;
        }

        public async Task<StockQuote?> ReadQuoteAsync(Stream stream, CancellationToken token = default)
        {
            if (token.IsCancellationRequested) return null;

            var content = await new StreamReader(stream).ReadToEndAsync(token);
            return ConvertQuote(content);
        }

        private static StockQuote? ConvertQuote(string content, PeriodType periodType = PeriodType.Unset)
        {
            try
            {
                var jobject = JsonConvert.DeserializeObject<JObject>(content);
                if (jobject!["data"]!.HasValues && jobject!["data"]!["klines"]!.HasValues)
                {
                    var list = new List<StockQuoteLine>();
                    var lines = JsonConvert.DeserializeObject<IEnumerable<string>>(jobject!["data"]!["klines"]!.ToString());
                    list.AddRange(lines!.Select(ReadLine));
                    return new StockQuote
                    (
                        stockName: jobject!["data"]!["name"]!.ToString(),
                        quoteLines: list.OrderBy(e => e.TradeDate),
                        periodType: periodType
                    );
                }
            }
            catch
            {
            }

            return null;
        }

        private static StockQuoteLine ReadLine(string content)
        {
            var data = content.Split(',', StringSplitOptions.RemoveEmptyEntries);
            return new StockQuoteLine
            {
                TradeDate = DateTime.Parse(data[0]),
                Open = Convert.ToDecimal(data[1]),
                Close = Convert.ToDecimal(data[2]),
                High = Convert.ToDecimal(data[3]),
                Low = Convert.ToDecimal(data[4]),
                TradeVolume = Convert.ToDecimal(data[5]),
                TradeAmount = Convert.ToDecimal(data[6])
            };
        }
    }
}