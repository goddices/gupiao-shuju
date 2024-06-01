using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Extensions
{
    internal static class ComboBoxExtensions
    {
        internal static TEnum GetSelectedValue<TEnum>(this ComboBox comboBox) where TEnum : struct
        {
            if (comboBox.SelectedItem == null)
                return Enum.Parse<TEnum>("0");
            else
            {
                return ((ComboBoxExtensionItem<TEnum>)comboBox.SelectedItem).Value;
            }
        }

        internal static void AddItemValues<TEnum>(this ComboBox comboBox, params TEnum[] values) where TEnum : struct
        {
            var data = values.Select(v => new ComboBoxExtensionItem<TEnum>(v)).ToArray();
            comboBox.DataSource = data;
            comboBox.DisplayMember = nameof(ComboBoxExtensionItem<TEnum>.Name);
            comboBox.ValueMember = nameof(ComboBoxExtensionItem<TEnum>.Value);
          
          
          //  comboBox.Items.AddRange(data);
           
        }
    }
}
