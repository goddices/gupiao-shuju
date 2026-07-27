import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from result_saver import reset_saver

matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']

def main():
    saver = reset_saver("随机漫步")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    titles = ['完全随机', '正数概率高', '负数概率高', '正负概率一样但绝对值大']

    for idx, ax in enumerate(axes.flatten()):
        base = 100
        values = [base]

        for _ in range(500):
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

        total_points = len(values) - 1
        rise_25_50_count = 0
        rise_50_100_count = 0
        rise_100_count = 0

        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                if values[i] > 0:
                    change_percent = (values[j] - values[i]) / values[i] * 100
                    if change_percent >= 25 and change_percent < 50:
                        rise_25_50_count += 1
                    elif change_percent >= 50 and change_percent < 100:
                        rise_50_100_count += 1
                    elif change_percent >= 100:
                        rise_100_count += 1

        ax.text(0.02, 0.98, f'总迭代: {total_points}\n涨25-50%: {rise_25_50_count} ({rise_25_50_count/total_points*100:.1f}%)\n涨50-100%: {rise_50_100_count} ({rise_50_100_count/total_points*100:.1f}%)\n涨100%+: {rise_100_count} ({rise_100_count/total_points*100:.1f}%)',
                transform=ax.transAxes, verticalalignment='top', fontsize=8, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        saver.log(f"[{titles[idx]}] 总迭代: {total_points}, 涨25-50%: {rise_25_50_count}, 涨50-100%: {rise_50_100_count}, 涨100%+: {rise_100_count}")

    plt.tight_layout()
    saver.save_chart("随机漫步_图表.jpg")
    saver.finalize()

if __name__ == "__main__":
    main()
