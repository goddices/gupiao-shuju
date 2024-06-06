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
            var enumType = typeof(TEnum);
            if (!enumType.IsEnum)
                throw new ArgumentOutOfRangeException(nameof(enumType));

            var enumName = Enum.GetName(typeof(TEnum), value);
            if (string.IsNullOrWhiteSpace(enumName))
                throw new ArgumentNullException(nameof(enumName));

            var fieldInfo = enumType.GetField(enumName);
            if (fieldInfo == null)
                throw new ArgumentNullException(nameof(fieldInfo));

            var attr = fieldInfo.GetCustomAttribute<DescriptionAttribute>();
            if (attr == null)
                throw new ArgumentNullException(nameof(attr));

            Name = attr.Description;
            Value = value;
        }

        public string Name { get; set; }

        public TEnum Value { get; set; }
    }
}
