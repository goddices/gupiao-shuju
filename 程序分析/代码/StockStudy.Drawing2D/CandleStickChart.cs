using System.Drawing;

namespace StockStudy.Drawing2D
{
    public class CandleStickChart
    {
        private readonly Color _backColor;
        private readonly Graphics _graphics;
        private readonly RectangleF _area;
        private decimal _maxPrice, _minPrice;

        public CandleStickChart(Color backColor, Graphics graphics)
        {
            _backColor = backColor;
            _graphics = graphics;
            _area = _graphics.VisibleClipBounds;
        }

        public int MaxShowSeries { get; set; } = 60;

        public IEnumerable<CandleStickEntry>? Series { get; set; }

        public void DrawCandleStick()
        {
            DrawSeries();
        }

        public void DrawBuySellPoints()
        {

        }

        private void DrawSeries()
        {
            if (Series != null)
            {
                _graphics.Clear(_backColor);
                var showSeries = Series.OrderByDescending(e => e.TradeDate).Take(MaxShowSeries)
                    .Select((e, i) => { e.CurrentIndex = MaxShowSeries - 1 - i; return e; }).ToList();
                _maxPrice = showSeries.Select(e => e.High).Max();
                _minPrice = showSeries.Select(e => e.Low).Min();
                showSeries.ForEach(DrawEntry);
            }
        }

        private void DrawMaxMinPrice()
        {

        }

        private void DrawEntry(CandleStickEntry entry)
        {
            var brush = new SolidBrush(IsRaised(entry) ? Color.Red : Color.Green);
            DrawCandleStick(brush, entry);
        }

        private static bool IsRaised(CandleStickEntry entry)
        {
            return entry.Open < entry.Close;
        }

        private void DrawRectangle(Brush brush, RectangleF rect)
        {
            _graphics.FillRectangle(brush, rect);
        }

        private void DrawLine(Brush brush, float width, PointF p1, PointF p2)
        {
            _graphics.DrawLine(new Pen(brush, width), p1, p2);
        }

        private void DrawCandleStick(Brush brush, CandleStickEntry entry)
        {
            var baseWidth = _area.Width / MaxShowSeries;
            var width = baseWidth - 1;
            var left = entry.CurrentIndex * baseWidth - 1;
            var priceHeight = _maxPrice - _minPrice;
            var top = (float)(((_maxPrice - (IsRaised(entry) ? entry.Close : entry.Open)) / priceHeight)) * _area.Height;
            var height = (float)(((Math.Abs(entry.Close - entry.Open)) / priceHeight)) * _area.Height;
            var rect = new RectangleF(left, top, width, height);
            DrawRectangle(brush, rect);

            var middle = entry.CurrentIndex * baseWidth + 0.5f * baseWidth - 1;
            var high = (float)(((_maxPrice - entry.High) / priceHeight)) * _area.Height;
            var low = (float)(((_maxPrice - entry.Low) / priceHeight)) * _area.Height;
            DrawLine(brush, 1, new PointF(middle, high), new PointF(middle, low));
        }
    }
}
