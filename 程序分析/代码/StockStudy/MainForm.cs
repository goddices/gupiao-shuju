namespace StockStudy
{
    using Microsoft.Extensions.DependencyInjection;
    using StockStudy.Extensions;
    using StockStudy.Models;
    using System.Diagnostics;
    using System.Linq;

    public partial class MainForm : Form
    {
        private readonly IQuoteReader _quoteReader;
        private readonly IServiceProvider _serviceProvider;
        private IAnalyst _analyst;

        public MainForm(IQuoteReader quoteReader, IServiceProvider serviceProvider) : base()
        {
            InitializeComponent();
            _quoteReader = quoteReader;
            _serviceProvider = serviceProvider;
            _analyst = _serviceProvider.GetRequiredService<IAnalyst>();
            DynamicLoad();
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
            }
            else
                textboxLogger.WriteLine("解析错误");
        }

        private void DynamicLoad()
        {
            InitTypeSelectOptions();
            LoadStrategySelections();
        }

        private void InitTypeSelectOptions()
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
    }
}
