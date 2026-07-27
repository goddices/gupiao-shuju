import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from result_saver import reset_saver

matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']

def main():
    saver = reset_saver("股票模拟")

    base = 100
    values = [base]

    events = ['No event', 'Market rally', 'Earnings beat', 'Product launch', 'Regulatory approval',
              'Market correction', 'Earnings miss', 'Product recall', 'Regulatory fine', 'Competitor announcement']

    rise_25_count = 0
    rise_50_count = 0
    rise_100_count = 0

    for i in range(300):
        fundamental = 1.0
        sentiment = random.uniform(0.90, 1.10)
        technical = random.uniform(0.95, 1.05)
        noise = random.uniform(0.99, 1.01)

        event = random.choice(events)
        event_impact = 0

        if event == 'Market rally':
            event_impact = 0.05
        elif event == 'Earnings beat':
            event_impact = 0.03
        elif event == 'Product launch':
            event_impact = 0.02
        elif event == 'Regulatory approval':
            event_impact = 0.02
        elif event == 'Market correction':
            event_impact = -0.04
        elif event == 'Earnings miss':
            event_impact = -0.03
        elif event == 'Product recall':
            event_impact = -0.04
        elif event == 'Regulatory fine':
            event_impact = -0.02
        elif event == 'Competitor announcement':
            event_impact = -0.01

        percent = fundamental * sentiment * technical * noise + event_impact

        base = base * percent
        values.append(base)

    percentages = [(v - 100) / 100 * 100 for v in values]

    colors = ['green' if v < 100 else 'red' for v in values]

    plt.figure(figsize=(14, 6))
    for i in range(len(values) - 1):
        plt.plot([i, i + 1], [values[i], values[i + 1]], color=colors[i + 1], linewidth=2)

    plt.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
    plt.ylabel('Stock Price')
    plt.title('Stock Simulation')
    plt.grid(True, alpha=0.3)

    plt.twinx()
    plt.ylabel('Change (%)')
    plt.xlabel('Iteration')
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

    plt.tight_layout()

    total_points = len(values) - 1
    for i in range(1, len(values)):
        change_percent = (values[i] - values[i-1]) / values[i-1] * 100
        if change_percent >= 25:
            rise_25_count += 1
        if change_percent >= 50:
            rise_50_count += 1
        if change_percent >= 100:
            rise_100_count += 1

    saver.log(f"总迭代次数: {total_points}")
    saver.log(f"上涨25%以上的次数: {rise_25_count}, 占比: {rise_25_count/total_points*100:.2f}%")
    saver.log(f"上涨50%以上的次数: {rise_50_count}, 占比: {rise_50_count/total_points*100:.2f}%")
    saver.log(f"上涨100%以上的次数: {rise_100_count}, 占比: {rise_100_count/total_points*100:.2f}%")

    saver.save_chart("股票模拟_图表.jpg")
    saver.finalize()

if __name__ == "__main__":
    main()
