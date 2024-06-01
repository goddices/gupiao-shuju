using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy
{
    public static class TextboxExtensions
    {
        public static void WriteLine(this TextBox box, object? obj)
        {
            box.WriteLine(obj?.ToString());
        }

        public static void WriteLine(this TextBox textbox, string? message, params object[] args)
        {
            if (string.IsNullOrWhiteSpace(message)) return;
            if (args == null || !args.Any())
                textbox.AppendText(message);
            else
                textbox.AppendText(string.Format(message, args));
            textbox.AppendText(Environment.NewLine);
            textbox.ScrollToCaret();
        }
    }
}
