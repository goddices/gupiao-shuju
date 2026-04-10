import random
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']

base = 100
values = [base]

for _ in range(240):
    percent = random.uniform(-0.1, 0.1)
    
    factor1 = random.uniform(0.9, 1.1)
    factor2 = random.uniform(0.95, 1.05)
    factor3 = random.uniform(0.98, 1.02)
    
    percent = percent * factor1 * factor2 * factor3
    
    change = base * percent
    base += change
    values.append(base)

percentages = [(v - 100) / 100 * 100 for v in values]

colors = ['green' if v < 100 else 'red' for v in values]

plt.figure(figsize=(14, 6))
for i in range(len(values) - 1):
    plt.plot([i, i + 1], [values[i], values[i + 1]], color=colors[i + 1], linewidth=2)

plt.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
plt.ylabel('股价')
plt.title('股票模拟')
plt.grid(True, alpha=0.3)

plt.twinx()
# plt.plot(range(len(percentages)), percentages, color='blue', linewidth=2)
plt.ylabel('涨跌幅 (%)')
plt.xlabel('迭代次数')
plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.show()
