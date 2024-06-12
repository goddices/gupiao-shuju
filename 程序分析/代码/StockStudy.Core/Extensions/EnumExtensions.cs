using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Xml.Linq;

namespace StockStudy.Extensions
{
    public static class EnumExtensions
    {
        public static string GetDesciption<TEnum>(this TEnum value) where TEnum : struct
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

            return attr.Description;
        }
    }
}
