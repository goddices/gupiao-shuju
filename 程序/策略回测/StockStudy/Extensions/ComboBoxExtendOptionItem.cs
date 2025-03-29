using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

namespace StockStudy.Extensions
{
    internal class ComboBoxExtendOptionItem<TEnum> where TEnum : struct
    {
        internal ComboBoxExtendOptionItem(TEnum value)
        {
            Name = value.GetDesciption();
            Value = value;
        }

        public string Name { get; set; }

        public TEnum Value { get; set; }
    }
}
