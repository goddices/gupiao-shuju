namespace StockStudy
{
    using System.Collections.Generic;
    using System.Linq;
    using System.Net.Http;
    using System.Text;
    using Newtonsoft.Json;
    using Newtonsoft.Json.Linq;

    public partial class Form1 : Form
    {
        private readonly HttpClient _httpClient = new HttpClient();



        public Form1()
        {
            InitializeComponent();
        }

        private async Task<string?> RequestQuotes(string market, string code, string fqt, string period)
        {
            var randomString = $"jQuery3510{Random.Shared.Next(1000_0000, 99999_9999)}_171{Random.Shared.Next(100_00000, 999_99999)}";
            var url = $"https://push2his.eastmoney.com/api/qt/stock/kline/get?cb={randomString}&secid={market}.{code}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt={period}&fqt={fqt}&end=20500101&lmt=744&_=1716992167964";
            var resp = await _httpClient.GetAsync(url);
            if (resp.IsSuccessStatusCode)
            {
                var content = await resp.Content.ReadAsStringAsync();


                var data = content
                    .Replace($"{randomString}(", string.Empty)
                    .Replace(");", string.Empty);
                return data;
            }
            return null;
        }

        private EastmoneyWebQuote? ConverQuote(string content)
        {
            var jobject = JsonConvert.DeserializeObject<JObject>(content);
            if (jobject!["data"]!.HasValues && jobject!["data"]!["klines"]!.HasValues)
            {
                var list = new List<EastmoneyWebQuoteDetail>();
                var lines = JsonConvert.DeserializeObject<IEnumerable<string>>(jobject!["data"]!["klines"]!.ToString());
                list.AddRange(lines!.Select(e => new EastmoneyWebQuoteDetail(e)));
                return new EastmoneyWebQuote
                {
                    Name = jobject!["data"]!["name"]!.ToString(),
                    Quotes = list.OrderBy(e => e.TradeDay)
                };
            }
            return null;
        }

        private async Task<EastmoneyWebQuote?> ReadQuotes(Stream stream)
        {
            var content = await new StreamReader(stream).ReadToEndAsync();
            return ConverQuote(content);
        }

        private InvestmentSummary TradeStrategy(EastmoneyWebQuote? quotes)
        {
            var fixedAmount = 1_000M;
            var investedAmount = 0M;
            var totalStocks = 0M;
            foreach (var quo in quotes!.Quotes)
            {
                if (quo == null) continue;
                var buyPrice = 0.5M * (quo!.High + quo!.Low);
                if (buyPrice == 0) continue;
                totalStocks += fixedAmount / buyPrice;
                investedAmount += fixedAmount;
            }
            var finalAmount = totalStocks * quotes.Quotes.Last().Close;
            return new InvestmentSummary
            {
                Name = quotes.Name,
                TotalDays = Convert.ToInt32((quotes.Quotes.Last().TradeDay - quotes.Quotes.First().TradeDay).TotalDays),
                CostAmount = investedAmount,
                FinalAmount = finalAmount,
            };

        }

        private async void button1_Click(object sender, EventArgs e)
        {
            var market = "1";
            if (radioButton1.Checked) market = "1";
            if (radioButton2.Checked) market = "0";
            var code = textBox1.Text;
            var resp = await RequestQuotes(market, code, (comboBox1.SelectedIndex + 1).ToString(), "102");
            var s = ConverQuote(resp);
            if (s != null)
            {
                textBox2.AppendText(TradeStrategy(s).ToString());
            }
            else { textBox2.AppendText("½âÎö´íÎó"); }
            textBox2.AppendText(Environment.NewLine);
            textBox2.ScrollToCaret();
        }

        private async void button2_Click(object sender, EventArgs e)
        {
            if (openFileDialog1.ShowDialog(this) == DialogResult.OK)
            {
                using (var stream = openFileDialog1.OpenFile())
                {
                    var ks = await ReadQuotes(stream);
                    if (ks != null)
                    {
                        TradeStrategy(ks);
                    }
                    else
                    {
                        MessageBox.Show("½âÎö´íÎó");
                    }
                }
            }

        }

        private void Form1_Load(object sender, EventArgs e)
        {
            comboBox1.SelectedIndex = 0;
            comboBox2.SelectedIndex = 0;
        }
    }
}
