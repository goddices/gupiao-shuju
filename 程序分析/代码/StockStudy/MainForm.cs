namespace StockStudy
{
    using Microsoft.Extensions.DependencyInjection;
    using StockStudy.Drawing2D;
    using StockStudy.Extensions;
    using StockStudy.Models;
    using System.Diagnostics;

    public partial class MainForm : Form
    {
        private readonly IQuoteReader _quoteReader;
        private readonly IAnalyst _analyst;
        private CandleStickChart? _chart;

        public MainForm(IQuoteReader quoteReader, IAnalyst analyst) : base()
        {
            _quoteReader = quoteReader;
            _analyst = analyst;
            InitializeComponent();
            DynamicLoadControls();
        }

        private void WriteAnalysisResult(StockQuote? quote)
        {
            var code = string.Empty;
            for (var idx = 0; idx < stragtegyBox.Controls.Count; idx++)
            {
                var ctrl = stragtegyBox.Controls[idx];
                if (ctrl is RadioButton rdb && rdb.Checked)
                {
                    code = ctrl.Text;
                }
            }


            if (string.IsNullOrWhiteSpace(code))
            {
                MessageBox.Show("必须选择一个策略");
                return;
            }

            if (quote != null)
            {
                var result = _analyst.StrategyAnalyze(code, quote);
                textboxLogger.WriteLine(result);
                textboxLogger.WriteLine(result.GetDetails());
                _chart!.BuySellMarks = result.TradingSnapshots.Select(e => new BuySellMark
                {
                    DateTime = e.TradeDate,
                    Direction = e.StockHoldings?.FirstOrDefault()?.TradeDirection == TransactionDirection.Buy ? BuySellMark.BuySell.Buy : BuySellMark.BuySell.Sell,
                    Price = e.StockHoldings?.FirstOrDefault()?.TradePrice ?? 0,
                });
                _chart!.Series = quote.QuoteLines.Select(e => new CandleStickEntry
                {
                    High = e.High,
                    Low = e.Low,
                    Open = e.Open,
                    TradeDate = e.TradeDate,
                    Close = e.Close,
                });
                _chart!.DrawCandleStick();
            }
            else
                textboxLogger.WriteLine("解析错误");
        }

        private void DynamicLoadControls()
        {
            LoadTypeSelections();
            LoadStrategySelections();
        }

        private void LoadTypeSelections()
        {
            adjustSelect.AddOptions(AdjustPriceType.Pre, AdjustPriceType.Post);
            periodSelect.AddOptions(PeriodType.Daily, PeriodType.Weekly);
            adjustSelect.SelectedIndex = 1;
            periodSelect.SelectedIndex = 1;
        }

        private void LoadStrategySelections()
        {
            var idx = 0;
            foreach (var strategy in _analyst.StrategyCodeList)
            {
                var rdb = new RadioButton
                {
                    Text = strategy
                };
                rdb.Left = idx * rdb.Width + 10;
                rdb.Top = stragtegyBox.Height / 2 - rdb.Height / 2;
                stragtegyBox.Controls.Add(rdb);
                idx++;
            }
        }

        private async void ButtonApi_Click(object sender, EventArgs e)
        {
            var market = "1";
            if (markketSH.Checked) market = "1";
            if (marketSZ.Checked) market = "0";
            var code = stockCodeInput.Text;
            var quote = await _quoteReader.ReadQuoteAsync(
                market,
                code,
                adjustSelect.GetSelectedValue<AdjustPriceType>(),
                periodSelect.GetSelectedValue<PeriodType>()
            );
            WriteAnalysisResult(quote);
        }

        private async void ButtonFile_Click(object sender, EventArgs e)
        {
            if (openFileDialog1.ShowDialog(this) == DialogResult.OK)
            {
                using (var stream = openFileDialog1.OpenFile())
                {
                    var quote = await _quoteReader.ReadQuoteAsync(stream);
                    WriteAnalysisResult(quote);
                }
            }

        }

        private void ButtonTestPy_Click(object sender, EventArgs e)
        {
            Process p = new Process();
            p.StartInfo = new ProcessStartInfo
            {
                CreateNoWindow = true,
                WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory,
                Arguments = "PythonFiles/test.py",
                FileName = "python"
            };
            p.Start();
        }

        private void ChartBox_Paint(object sender, PaintEventArgs e)
        {
            _chart!.DrawCandleStick();
        }

        private void MainForm_Load(object sender, EventArgs e)
        {
            _chart = new CandleStickChart(this.BackColor, chartBox.CreateGraphics());
        }

        private void ButtonZoomOut_Click(object sender, EventArgs e)
        {
            _chart!.MaxShowSeries += 20;
            _chart!.DrawCandleStick();
        }

        private void ButtonZoomIn_Click(object sender, EventArgs e)
        {
            _chart!.MaxShowSeries -= 20;
            _chart!.DrawCandleStick();
        }
    }
}
