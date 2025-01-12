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

        public MainForm(IQuoteReader quoteReader, IServiceProvider serviceProvider) : base()
        {
            InitializeComponent();
            DynamicInitialize();
            _quoteReader = quoteReader;
            _serviceProvider = serviceProvider;
        }

        private void WriteAnalysisResult(StockQuote? quote)
        {
            var index = 0;
            if (dollerCostAveragingStrategy.Checked) index = 1;
            else if (myAnyTestStrategy.Checked) index = 0;
            var analyst = _serviceProvider.GetRequiredService<IAnalyst>();
            var code = analyst.StrategyCodeList.ElementAt(index);
            if (quote != null)
            {
                var result = analyst.StrategyAnalyze(code, quote);
                textboxLogger.WriteLine(result);
                textboxLogger.WriteLine(result.GetDetails());
            }
            else
                textboxLogger.WriteLine("½âÎö´íÎó");
        }

        private void DynamicInitialize()
        {
            InitTypeSelectOptions();
        }

        private void InitTypeSelectOptions()
        {
            adjustSelect.AddOptions(AdjustPriceType.Pre, AdjustPriceType.Post);
            periodSelect.AddOptions(PeriodType.Daily, PeriodType.Weekly);
            adjustSelect.SelectedIndex = 1;
            periodSelect.SelectedIndex = 1;
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
