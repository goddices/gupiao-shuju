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
        private IDictionary<string, InvestmentSummary>? _results;
        private StockQuote? _quote;

        public MainForm(IQuoteReader quoteReader, IAnalyst analyst) : base()
        {
            _quoteReader = quoteReader;
            _analyst = analyst;
            InitializeComponent();
            DynamicLoadControls();
        }

        private void WriteAnalysisResult(StockQuote? quote)
        {
            if (quote != null)
            {
                _quote = quote;
                _results = _analyst.Analyze(quote);
                foreach (var result in _results.Values)
                {
                    textboxLogger.WriteLine(result?.GetSummary());
                    //textboxLogger.WriteLine(result.GetDetails());
                }
            }
            else
                textboxLogger.WriteLine("解析错误");
        }

        private void DynamicLoadControls()
        {
            LoadTypeSelections();
            LoadStrategySelections();
        }

        private void LoadChart()
        {
            _chart!.FocusOn += ChartFocusOn;
        }

        private void LoadTypeSelections()
        {
            adjustSelect.AddOptions(AdjustPriceType.Pre, AdjustPriceType.Post);
            periodSelect.AddOptions(PeriodType.Daily, PeriodType.Weekly, PeriodType.Monthly);
            adjustSelect.SelectedIndex = 1;
            periodSelect.SelectedIndex = 1;
        }

        private void LoadStrategySelections()
        {
            var idx = 0;
            foreach (var strategy in _analyst.StrategyNames)
            {
                var rdb = new RadioButton
                {
                    Text = strategy
                };
                rdb.CheckedChanged += StrategyRadioButton_CheckedChanged;
                rdb.Left = idx * rdb.Width + 10;
                rdb.Top = stragtegyBox.Height / 2 - rdb.Height / 2;
                stragtegyBox.Controls.Add(rdb);
                idx++;
            }
        }

        private void StrategyRadioButton_CheckedChanged(object? sender, EventArgs e)
        {
            if (sender is not null && sender is RadioButton rdb && _results is not null && _quote is not null)
            {
                var code = rdb.Text;
                if (string.IsNullOrWhiteSpace(code) || !_results.ContainsKey(code))
                {
                    MessageBox.Show("必须选择一个策略");
                    return;
                }
                _chart!.BuySellMarks = _results[code].TradingSnapshots.Select(e => new BuySellMark
                {
                    DateTime = e.TradeDate,
                    Direction = e.TradeDirection == TransactionDirection.Buy ? BuySellMark.BuySell.Buy : BuySellMark.BuySell.Sell,
                    Price = e.TradePrice,
                });
                _chart!.Series = _quote.QuoteLines.Select(e => new CandleStickEntry
                {
                    High = e.High,
                    Low = e.Low,
                    Open = e.Open,
                    TradeDate = e.TradeDate,
                    Close = e.Close,
                });
                _chart!.DrawCandleStick();
            }
        }

        private async void ButtonApi_Click(object sender, EventArgs e)
        {
            var market = Market.Unset;
            if (markketSH.Checked) market = Market.Shanghai;
            if (marketSZ.Checked) market = Market.Shengzhen;
            var code = stockCodeInput.Text;
            var quote = await _quoteReader.ReadQuoteAsync(
                market,
                code,
                adjustSelect.GetSelectedValue<AdjustPriceType>(),
                periodSelect.GetSelectedValue<PeriodType>()
            );
            var a = quote.CalculateIndicators();
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
            LoadChart();
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

        private void ChartBox_MouseMove(object sender, MouseEventArgs e)
        {
            _chart!.FocusOneStick(e.Location);
        }

        private void ChartFocusOn(object? sender, CandleStickChart.FocusOnEventArgs e)
        {
            labelFocusQuote.Text = $"{e.Entry?.ToString()}";
        }

        private void ChartBox_MouseLeave(object sender, EventArgs e)
        {
            labelFocusQuote.Text = "";
            _chart!.DrawCandleStick();
        }
    }
}
