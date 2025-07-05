using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace StockStudy.Winform
{
    public partial class FormSearch : Form
    {
        public FormSearch()
        {
            InitializeComponent();
        }

        private void FormSearch_Load(object sender, EventArgs e)
        {
            //https://searchadapter.eastmoney.com/api/suggest/get?cb=jQuery18309723990275089607_1736673283810&input=%E7%94%B5%E4%BF%A1&type=14&token=D43BF722C8E33BDC906FB84D85E326E8&markettype=&mktnum=&jys=&classify=&securitytype=&status=&count=5&_=1736673690434
            //https://searchadapter.eastmoney.com/api/suggest/get?cb=jQuery18309723990275089607_1736673283811&input=%E8%8B%B1%E4%BC%9F%E8%BE%BE&type=14&token=D43BF722C8E33BDC906FB84D85E326E8&markettype=&mktnum=&jys=&classify=&securitytype=&status=&count=5&_=1736673799930
        }
    }
}
