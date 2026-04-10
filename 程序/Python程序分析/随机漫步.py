import random
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

titles = ['完全随机', '正数概率高', '负数概率高', '正负概率一样但绝对值大']

for idx, ax in enumerate(axes.flatten()):
    base = 100
    values = [base]

    for _ in range(240):
        if idx == 0:
            percent = random.uniform(-0.1, 0.1)
        elif idx == 1:
            percent = random.uniform(-0.05, 0.1)
        elif idx == 2:
            percent = random.uniform(-0.1, 0.05)
        else:
            percent = random.uniform(-0.2, 0.2)
        
        change = base * percent
        base += change
        values.append(base)

    percentages = [(v - 100) / 100 * 100 for v in values]

    colors = ['green' if v < 100 else 'red' for v in values]

    for i in range(len(values) - 1):
        ax.plot([i, i + 1], [values[i], values[i + 1]], color=colors[i + 1], linewidth=2)

    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('股价')
    ax.set_title(titles[idx])
    ax.grid(True, alpha=0.3)

    ax2 = ax.twinx()
    ax2.plot(range(len(percentages)), percentages, color='blue', alpha=0, linewidth=0)
    ax2.set_ylabel('涨跌幅 (%)')
    ax2.set_xlabel('迭代次数')
    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.show()
