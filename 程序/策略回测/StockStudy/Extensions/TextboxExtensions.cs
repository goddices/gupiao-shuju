using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy
{
    internal static class TextboxExtensions
    {
        internal static void WriteLine(this TextBox box, IEnumerable<string> multi)
        {
            foreach (var item in multi)
            {
                box.WriteLine(item);
            }
        }


        internal static void WriteLine(this TextBox box, object? obj)
        {
            box.WriteLine(obj?.ToString());
        }

        internal static void WriteLine(this TextBox textbox, string? message, params object[] args)
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
