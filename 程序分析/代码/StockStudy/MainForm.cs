namespace StockStudy
{
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
            var quote = await _quoteReader.ReadQuoteAsync(market, code, GetAdjustType(adjustSelect), PeriodType.Weekly);
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
            if (quote != null)
                logArea.WriteLine(_analyst.StrategyAnanlyzeFinal(quote));
            else
                logArea.WriteLine("½âÎö´íÎó");
        }

        private void Form1_Load(object sender, EventArgs e)
        {
            adjustSelect.SelectedIndex = 1;
            periodSelect.SelectedIndex = 1;
        }

        private static AdjustPriceType GetAdjustType(ComboBox comboBox)
        {
            return comboBox.SelectedIndex switch
            {
                0 => AdjustPriceType.Pre,
                1 => AdjustPriceType.Post,
                _ => AdjustPriceType.Unset
            };
        }

        private static PeriodType GetPeriodType(ComboBox comboBox)
        {
            return comboBox.SelectedIndex switch
            {
                0 => PeriodType.Daily,
                1 => PeriodType.Weekly,
                _ => PeriodType.Unset
            };
        }
    }
}
