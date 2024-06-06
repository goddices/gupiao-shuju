namespace StockStudy
{
    using StockStudy.Extensions;
    using StockStudy.Models;
    using System.Collections;
    using System.Collections.Generic;
    using System.Linq;

    public partial class MainForm : Form
    {
        private readonly IAnalyst _analyst;
        private readonly IQuoteReader _quoteReader;

        public MainForm(IAnalyst analyst, IQuoteReader quoteReader) : base()
        {
            InitializeComponent();
            _analyst = analyst;
            _quoteReader = quoteReader;
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

        private void WriteAnalysisResult(StockQuote? quote)
        {
            var index = 0;
            if (dollerCostAveragingStrategy.Checked) index = 1;
            else if (myAnyTestStrategy.Checked) index = 0;
            var code = _analyst.StrategyCodeList.ElementAt(index);
            if (quote != null)
                logArea.WriteLine(_analyst.StrategyAnalyze(code, quote));
            else
                logArea.WriteLine("½âÎö´íÎó");
        }

        private void Form1_Load(object sender, EventArgs e)
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


    }
}
