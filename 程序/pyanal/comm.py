
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# 设置中文字体（Linux环境）
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

# ---------------------- 1. 数据预处理（手动整理为DataFrame）----------------------
# 中国电信数据（移动用户数、5G套餐用户数、有线宽带用户数）
telecom_data = [
    ["2023-04", 40019, 28723, 18482],
    ["2023-05", 40112, 29062, 18565],
    ["2023-06", 40191, 29486, 18626],
    ["2023-07", 40269, 29815, 18686],
    ["2023-08", 40365, 30298, 18777],
    ["2023-10", 40664, 31132, 18962],
    ["2023-11", 40723, 31463, 19006],
    ["2023-12", 40777, 31866, 19016],
    ["2024-01", 40905, 32174, 19144],
    ["2024-02", 40974, 32406, 19163],
    ["2024-03", 41165, 32872, 19222],
    ["2024-04", 41345, 33162, 19230],
    ["2024-05", 41538, 33426, 19284],
    ["2024-06", 41685, 33663, 19335],
    ["2024-07", 41906, 33975, 19431],
    ["2024-08", 42074, 34289, 19504],
    ["2024-09", 42267, 34506, 19626],
    ["2024-10", 42343, 34753, 19662],
    ["2024-11", 42370, 34937, 19681],
    ["2024-12", 42452, 35148, 19744],
    ["2025-Q1", 42947, 26621, 19811],  # 注意：2025年5G数据可能存在统计口径差异
    ["2025-Q2", 43271, 28202, 19860],
    ["2025-Q3", 43719, 29241, 20049],
]

# 中国移动数据（移动用户数、5G套餐用户数、有线宽带用户数）
mobile_data = [
    ["2023-05", 98310.8, 70695.6, 28444.4],
    ["2023-06", 98538.6, 72180.4, 28640.4],
    ["2023-07", 98600.0, 72633.5, 28817.1],
    ["2023-08", 98647.4, 73317.9, 29045.2],
    ["2023-09", 99003.1, 75036.2, 29468.4],
    ["2023-10", 99077.7, 75877.6, 29638.0],
    ["2023-11", 99094.8, 77880.0, 29824.8],
    ["2023-12", 99100.0, 79450.3, 29824.6],
    ["2024-01", 99157.6, 78951.2, 30085.9],
    ["2024-02", 99106.6, 80078.5, 30237.3],
    ["2024-03", 99562.5, 79853.6, 30507.6],
    ["2024-04", 99736.2, 79917.9, 30640.3],
    ["2024-05", 99844.0, 50255.8, 30752.1],  # 2024年5月后5G统计口径可能调整
    ["2024-06", 100025.6, 51421.8, 30917.2],
    ["2024-07", 100081.5, 52795.6, 30920.5],
    ["2024-08", 100154.5, 53352.2, 31061.0],
    ["2024-09", 100397.7, 53943.0, 31360.4],
    ["2024-10", 100427.7, 54569.0, 31483.4],
    ["2024-11", 100510.1, 54712.0, 31586.8],
    ["2024-12", 100431.5, 55240.0, 31457.0],
    ["2025-Q1", 100338.0, 57767.0, 32005.0],
    ["2025-Q2", 100488.0, 59931.0, 32323.0],
    ["2025-Q3", 100887.0, 62235.0, 32877.0],
]

# 转换为DataFrame并统一日期格式
telecom_df = pd.DataFrame(telecom_data, columns=["日期", "移动用户数", "5G套餐用户数", "有线宽带用户数"])
mobile_df = pd.DataFrame(mobile_data, columns=["日期", "移动用户数", "5G套餐用户数", "有线宽带用户数"])

# 处理2025年季度数据为月度均值（便于趋势展示）
def convert_quarter_to_month(df):
    new_rows = []
    for idx, row in df.iterrows():
        date_str = row["日期"]
        if "Q" in date_str:
            year, quarter = date_str.split("-")
            quarter_num = int(quarter.replace("Q", ""))
            # 季度起始月份（Q1=1月, Q2=4月, Q3=7月）
            month = (quarter_num - 1) * 3 + 1
            for i in range(3):
                new_date = f"{year}-{month + i:02d}"
                new_rows.append({
                    "日期": new_date,
                    "移动用户数": row["移动用户数"],
                    "5G套餐用户数": row["5G套餐用户数"],
                    "有线宽带用户数": row["有线宽带用户数"]
                })
        else:
            new_rows.append(row.to_dict())
    return pd.DataFrame(new_rows)

telecom_df = convert_quarter_to_month(telecom_df)
mobile_df = convert_quarter_to_month(mobile_df)

# 转换日期为datetime格式并排序
telecom_df["日期"] = pd.to_datetime(telecom_df["日期"])
mobile_df["日期"] = pd.to_datetime(mobile_df["日期"])
telecom_df = telecom_df.sort_values("日期")
mobile_df = mobile_df.sort_values("日期")

# ---------------------- 2. 生成多维度对比图表 ----------------------
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("三大运营商运营数据对比分析（2023-2025）", fontsize=16, fontweight="bold")

# 颜色配置
colors = {
    "中国移动": "#E60012",
    "中国电信": "#0091D5",
    "5G套餐": "#FF7D00",
    "有线宽带": "#00B42A"
}

# 子图1：移动用户数趋势对比
ax1 = axes[0, 0]
ax1.plot(telecom_df["日期"], telecom_df["移动用户数"], 
         label="中国电信", color=colors["中国电信"], linewidth=2.5, marker="o", markersize=4)
ax1.plot(mobile_df["日期"], mobile_df["移动用户数"], 
         label="中国移动", color=colors["中国移动"], linewidth=2.5, marker="s", markersize=4)
ax1.set_title("移动用户数趋势（万户）", fontsize=12, fontweight="bold")
ax1.set_xlabel("日期")
ax1.set_ylabel("用户数（万户）")
ax1.legend()
ax1.grid(True, alpha=0.3)
# 旋转x轴标签
ax1.tick_params(axis='x', rotation=45)

# 子图2：5G套餐用户数趋势对比
ax2 = axes[0, 1]
ax2.plot(telecom_df["日期"], telecom_df["5G套餐用户数"], 
         label="中国电信", color=colors["中国电信"], linewidth=2.5, marker="o", markersize=4)
ax2.plot(mobile_df["日期"], mobile_df["5G套餐用户数"], 
         label="中国移动", color=colors["中国移动"], linewidth=2.5, marker="s", markersize=4)
ax2.set_title("5G套餐用户数趋势（万户）", fontsize=12, fontweight="bold")
ax2.set_xlabel("日期")
ax2.set_ylabel("5G用户数（万户）")
ax2.legend()
ax2.grid(True, alpha=0.3)
ax2.tick_params(axis='x', rotation=45)

# 子图3：有线宽带用户数趋势对比
ax3 = axes[1, 0]
ax3.plot(telecom_df["日期"], telecom_df["有线宽带用户数"], 
         label="中国电信", color=colors["中国电信"], linewidth=2.5, marker="o", markersize=4)
ax3.plot(mobile_df["日期"], mobile_df["有线宽带用户数"], 
         label="中国移动", color=colors["中国移动"], linewidth=2.5, marker="s", markersize=4)
ax3.set_title("有线宽带用户数趋势（万户）", fontsize=12, fontweight="bold")
ax3.set_xlabel("日期")
ax3.set_ylabel("宽带用户数（万户）")
ax3.legend()
ax3.grid(True, alpha=0.3)
ax3.tick_params(axis='x', rotation=45)

# 子图4：2025Q3业务结构占比（饼图）
ax4 = axes[1, 1]
# 提取2025Q3数据（最后3个月均值）
telecom_2025q3 = telecom_df[telecom_df["日期"].dt.year == 2025].iloc[-1]
mobile_2025q3 = mobile_df[mobile_df["日期"].dt.year == 2025].iloc[-1]

# 中国移动业务结构
mobile_labels = ["移动用户数", "5G套餐用户数", "有线宽带用户数"]
mobile_values = [mobile_2025q3["移动用户数"], mobile_2025q3["5G套餐用户数"], mobile_2025q3["有线宽带用户数"]]
# 中国电信业务结构
telecom_labels = ["移动用户数", "5G套餐用户数", "有线宽带用户数"]
telecom_values = [telecom_2025q3["移动用户数"], telecom_2025q3["5G套餐用户数"], telecom_2025q3["有线宽带用户数"]]

# 双饼图对比
ax4.pie(mobile_values, labels=mobile_labels, colors=[colors["中国移动"], colors["5G套餐"], colors["有线宽带"]], 
        autopct='%1.1f%%', startangle=90, radius=0.7, labeldistance=1.1)
ax4.pie(telecom_values, labels=telecom_labels, colors=[colors["中国电信"], colors["5G套餐"], colors["有线宽带"]], 
        autopct='%1.1f%%', startangle=90, radius=0.4, labeldistance=0.7)
ax4.set_title("2025Q3业务结构占比对比", fontsize=12, fontweight="bold")

# 调整布局
plt.tight_layout()
# 保存图片（高清格式）
plt.savefig("operator_data_analysis.png", dpi=300, bbox_inches="tight")
plt.close()

# ---------------------- 3. 输出关键统计指标 ----------------------
print("="*50)
print("三大运营商关键指标统计（截至2025Q3）")
print("="*50)

# 中国移动关键指标
mobile_latest = mobile_df.iloc[-1]
print(f"\n【中国移动】")
print(f"移动用户总数：{mobile_latest['移动用户数']:.1f} 万户")
print(f"5G套餐用户数：{mobile_latest['5G套餐用户数']:.1f} 万户")
print(f"5G渗透率：{mobile_latest['5G套餐用户数']/mobile_latest['移动用户数']*100:.1f}%")
print(f"有线宽带用户数：{mobile_latest['有线宽带用户数']:.1f} 万户")

# 中国电信关键指标
telecom_latest = telecom_df.iloc[-1]
print(f"\n【中国电信】")
print(f"移动用户总数：{telecom_latest['移动用户数']:.1f} 万户")
print(f"5G套餐用户数：{telecom_latest['5G套餐用户数']:.1f} 万户")
print(f"5G渗透率：{telecom_latest['5G套餐用户数']/telecom_latest['移动用户数']*100:.1f}%")
print(f"有线宽带用户数：{telecom_latest['有线宽带用户数']:.1f} 万户")

# 增长对比（2023年5月 vs 2025年9月）
mobile_2023 = mobile_df[mobile_df["日期"] == "2023-05"].iloc[0]
telecom_2023 = telecom_df[telecom_df["日期"] == "2023-05"].iloc[0]

print(f"\n【2023.05-2025.09 增长对比】")
print(f"中国移动移动用户增长：{mobile_latest['移动用户数']-mobile_2023['移动用户数']:.1f} 万户（{((mobile_latest['移动用户数']-mobile_2023['移动用户数'])/mobile_2023['移动用户数']*100):.1f}%）")
