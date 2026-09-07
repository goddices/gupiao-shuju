import json
import pandas as pd
from datetime import datetime
from emdata import (
    get_quote_reader,
    Market,
    AdjustPriceType,
    PeriodType,
)

# ---------- 内置分红数据（来自您之前的 JSON）----------
DIVIDEND_JSON = """
[
  {"seq":1,"annual":"2007年末期","plan_10shares":"1.5686元","per_share":0.15686,"record_date":"2008-06-12","ex_dividend_date":"2008-06-13","payment_date":"2008-06-30"},
  {"seq":2,"annual":"2008年中期","plan_10shares":"1.3183元","per_share":0.13183,"record_date":"2008-09-18","ex_dividend_date":"2008-09-19","payment_date":"2008-09-26"},
  {"seq":3,"annual":"2008年末期","plan_10shares":"1.4953元","per_share":0.14953,"record_date":"2009-06-18","ex_dividend_date":"2009-06-19","payment_date":"2009-06-30"},
  {"seq":4,"annual":"2009年中期","plan_10shares":"1.2417元","per_share":0.12417,"record_date":"2009-09-21","ex_dividend_date":"2009-09-22","payment_date":"2009-09-30"},
  {"seq":5,"annual":"2009年末期","plan_10shares":"1.3003元","per_share":0.13003,"record_date":"2010-06-02","ex_dividend_date":"2010-06-03","payment_date":"2010-06-30"},
  {"seq":6,"annual":"2010年中期","plan_10shares":"1.6063元","per_share":0.16063,"record_date":"2010-09-15","ex_dividend_date":"2010-09-16","payment_date":"2010-09-30"},
  {"seq":7,"annual":"2010年末期","plan_10shares":"1.8357元","per_share":0.18357,"record_date":"2011-06-15","ex_dividend_date":"2011-06-16","payment_date":"2011-06-30"},
  {"seq":8,"annual":"2011年中期","plan_10shares":"1.6229元","per_share":0.16229,"record_date":"2011-09-15","ex_dividend_date":"2011-09-16","payment_date":"2011-09-30"},
  {"seq":9,"annual":"2011年末期","plan_10shares":"1.6462元","per_share":0.16462,"record_date":"2012-06-15","ex_dividend_date":"2012-06-18","payment_date":"2012-06-29"},
  {"seq":10,"annual":"2012年中期","plan_10shares":"1.5250元","per_share":0.15250,"record_date":"2012-09-19","ex_dividend_date":"2012-09-20","payment_date":"2012-09-28"},
  {"seq":11,"annual":"2012年末期","plan_10shares":"1.3106元","per_share":0.13106,"record_date":"2013-06-18","ex_dividend_date":"2013-06-19","payment_date":"2013-06-28"},
  {"seq":12,"annual":"2013年中期","plan_10shares":"1.6110元","per_share":0.16110,"record_date":"2013-09-16","ex_dividend_date":"2013-09-17","payment_date":"2013-09-30"},
  {"seq":13,"annual":"2013年末期","plan_10shares":"1.5755元","per_share":0.15755,"record_date":"2014-06-17","ex_dividend_date":"2014-06-18","payment_date":"2014-06-30"},
  {"seq":14,"annual":"2014年中期","plan_10shares":"1.6750元","per_share":0.16750,"record_date":"2014-09-18","ex_dividend_date":"2014-09-19","payment_date":"2014-09-30"},
  {"seq":15,"annual":"2014年末期","plan_10shares":"0.9601元","per_share":0.09601,"record_date":"2015-07-07","ex_dividend_date":"2015-07-08","payment_date":"2015-07-15"},
  {"seq":16,"annual":"2015年中期","plan_10shares":"0.6247元","per_share":0.06247,"record_date":"2015-09-16","ex_dividend_date":"2015-09-17","payment_date":"2015-09-25"},
  {"seq":17,"annual":"2015年末期","plan_10shares":"0.2486元","per_share":0.02486,"record_date":"2016-06-06","ex_dividend_date":"2016-06-07","payment_date":"2016-06-22"},
  {"seq":18,"annual":"2016年中期","plan_10shares":"0.2131元","per_share":0.02131,"record_date":"2016-09-19","ex_dividend_date":"2016-09-20","payment_date":"2016-09-29"},
  {"seq":19,"annual":"2016年末期","plan_10shares":"0.3801元","per_share":0.03801,"record_date":"2017-06-20","ex_dividend_date":"2017-06-21","payment_date":"2017-06-30"},
  {"seq":20,"annual":"2017年中期","plan_10shares":"0.6926元","per_share":0.06926,"record_date":"2017-09-13","ex_dividend_date":"2017-09-14","payment_date":"2017-09-22"},
  {"seq":21,"annual":"2017年末期","plan_10shares":"0.6074元","per_share":0.06074,"record_date":"2018-06-19","ex_dividend_date":"2018-06-20","payment_date":"2018-06-29"},
  {"seq":22,"annual":"2018年中期","plan_10shares":"0.8880元","per_share":0.08880,"record_date":"2018-09-19","ex_dividend_date":"2018-09-20","payment_date":"2018-09-28"},
  {"seq":23,"annual":"2018年末期","plan_10shares":"0.9000元","per_share":0.09000,"record_date":"2019-06-26","ex_dividend_date":"2019-06-27","payment_date":"2019-07-05"},
  {"seq":24,"annual":"2019年中期","plan_10shares":"0.7765元","per_share":0.07765,"record_date":"2019-09-20","ex_dividend_date":"2019-09-23","payment_date":"2019-09-30"},
  {"seq":25,"annual":"2019年末期","plan_10shares":"0.6601元","per_share":0.06601,"record_date":"2020-06-24","ex_dividend_date":"2020-06-29","payment_date":"2020-07-06"},
  {"seq":26,"annual":"2020年中期","plan_10shares":"0.8742元","per_share":0.08742,"record_date":"2020-09-18","ex_dividend_date":"2020-09-21","payment_date":"2020-09-29"},
  {"seq":27,"annual":"2020年末期","plan_10shares":"0.8742元","per_share":0.08742,"record_date":"2021-06-25","ex_dividend_date":"2021-06-28","payment_date":"2021-07-05"},
  {"seq":28,"annual":"2021年中期","plan_10shares":"1.3040元","per_share":0.13040,"record_date":"2021-09-15","ex_dividend_date":"2021-09-16","payment_date":"2021-09-27"},
  {"seq":29,"annual":"2021年末期","plan_10shares":"0.9622元","per_share":0.09622,"record_date":"2022-06-24","ex_dividend_date":"2022-06-27","payment_date":"2022-07-08"},
  {"seq":30,"annual":"2022年中期","plan_10shares":"2.0258元","per_share":0.20258,"record_date":"2022-09-16","ex_dividend_date":"2022-09-19","payment_date":"2022-09-29"},
  {"seq":31,"annual":"2022年末期","plan_10shares":"2.2000元","per_share":0.22000,"record_date":"2023-06-26","ex_dividend_date":"2023-06-27","payment_date":"2023-07-07"},
  {"seq":32,"annual":"2023年中期","plan_10shares":"2.1000元","per_share":0.21000,"record_date":"2023-09-18","ex_dividend_date":"2023-09-19","payment_date":"2023-09-28"},
  {"seq":33,"annual":"2023年末期","plan_10shares":"2.3000元","per_share":0.23000,"record_date":"2024-06-24","ex_dividend_date":"2024-06-25","payment_date":"2024-07-05"},
  {"seq":34,"annual":"2024年中期","plan_10shares":"2.2000元","per_share":0.22000,"record_date":"2024-09-13","ex_dividend_date":"2024-09-18","payment_date":"2024-09-30"},
  {"seq":35,"annual":"2024年末期","plan_10shares":"2.5000元","per_share":0.25000,"record_date":"2025-06-23","ex_dividend_date":"2025-06-24","payment_date":"2025-07-03"},
  {"seq":36,"annual":"2025年中期","plan_10shares":"2.2000元","per_share":0.22000,"record_date":"2025-09-15","ex_dividend_date":"2025-09-16","payment_date":"2025-09-26"},
  {"seq":37,"annual":"2025年末期","plan_10shares":"2.5000元","per_share":0.25000,"record_date":"2026-06-25","ex_dividend_date":"2026-06-26","payment_date":"2026-06-26"}
]
"""


def main():
    # 1. 解析分红数据
    dividends = json.loads(DIVIDEND_JSON)
    for d in dividends:
        d["payment_date"] = datetime.strptime(d["payment_date"], "%Y-%m-%d").date()
        d["per_share"] = float(d["per_share"])

    # 2. 获取中国石油不复权日线
    print("正在获取中国石油(601857)日线数据...")
    reader = get_quote_reader()
    quote = reader.read_quote(
        market=Market.SHANGHAI,
        stock_code="601857",
        adjust_type=AdjustPriceType.NONE,
        period_type=PeriodType.DAILY,
        limit=5000,
    )
    if not quote:
        print("获取行情失败，请检查网络。")
        return

    # 转为 DataFrame
    df = (
        pd.DataFrame(
            [{"date": q.trade_date.date(), "close": q.close} for q in quote.quote_lines]
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    print(f"数据范围：{df['date'].min()} 至 {df['date'].max()}")

    # 前复权日线（成本前复权口径：每笔交易按当日前复权价折算）
    quote_fwd = reader.read_quote(
        market=Market.SHANGHAI,
        stock_code="601857",
        adjust_type=AdjustPriceType.FORWARD,
        period_type=PeriodType.DAILY,
        limit=5000,
    )
    fwd_map = {}
    if quote_fwd and quote_fwd.quote_lines:
        for q in quote_fwd.quote_lines:
            fwd_map[q.trade_date.date()] = float(q.close)
    if fwd_map:
        print(f"前复权数据范围：{min(fwd_map)} 至 {max(fwd_map)}")

    # 3. 初始买入（2010-01-01后首个交易日）
    start_date = datetime(2010, 1, 1).date()
    first_row = df[df["date"] >= start_date].iloc[0]
    buy_date = first_row["date"]
    buy_price = first_row["close"]
    cash = 1_000_000
    shares = int(cash // buy_price)
    cash -= shares * buy_price
    # 每笔交易明细（日期/价格/数量），前复权口径成本基于此折算
    trades = [
        {"date": buy_date, "kind": "建仓", "price": buy_price,
         "shares": shares, "amount": shares * buy_price}
    ]
    print(
        f"初始买入：{buy_date}，价格 {buy_price:.2f}，持股 {shares} 股，剩余现金 {cash:.2f}"
    )

    # 4. 构建分红再投日列表（派息日后的第一个交易日）
    reinvest_events = []
    for d in dividends:
        pay_date = d["payment_date"]
        if pay_date < buy_date:
            continue
        next_trade = df[df["date"] > pay_date]
        if not next_trade.empty:
            reinvest_date = next_trade.iloc[0]["date"]
            reinvest_events.append((reinvest_date, d["per_share"]))
    reinvest_events.sort(key=lambda x: x[0])

    # 5. 遍历交易日，执行分红再投
    idx = 0
    total_dividend = 0.0
    for _, row in df[df["date"] >= buy_date].iterrows():
        cur_date = row["date"]
        cur_price = row["close"]
        while idx < len(reinvest_events) and reinvest_events[idx][0] == cur_date:
            _, div_per_share = reinvest_events[idx]
            div_cash = shares * div_per_share
            total_dividend += div_cash
            cash += div_cash
            buy_qty = int(cash // cur_price)
            if buy_qty > 0:
                shares += buy_qty
                cash -= buy_qty * cur_price
                trades.append({"date": cur_date, "kind": "红利再投", "price": cur_price,
                               "shares": buy_qty, "amount": buy_qty * cur_price})
                print(
                    f"分红再投：{cur_date}，每股 {div_per_share:.4f}，得 {div_cash:.2f} 元，"
                    f"以 {cur_price:.2f} 买入 {buy_qty} 股，余现金 {cash:.2f}"
                )
            else:
                print(
                    f"分红再投：{cur_date}，分红 {div_cash:.2f} 元，但股价 {cur_price:.2f} 过高，暂不买入"
                )
            idx += 1

    # 6. 最终结果
    last_row = df.iloc[-1]
    last_date = last_row["date"]
    last_price = last_row["close"]
    final_value = shares * last_price + cash
    years = (last_date - buy_date).days / 365.25
    total_return = (final_value / 1_000_000 - 1) * 100
    annual_return = (pow(final_value / 1_000_000, 1 / years) - 1) * 100

    print("\n========== 最终结果 ==========")
    print(f"起始日期：{buy_date}  结束日期：{last_date}")
    print(f"持股数：{shares:,} 股  最新收盘价：{last_price:.2f} 元")
    print(f"现金余额：{cash:.2f} 元  总市值：{final_value:,.2f} 元")
    print(f"累计分红（已再投）：{total_dividend:,.2f} 元")
    print(f"总收益率：{total_return:.2f}%  年化收益率：{annual_return:.2f}%")
    print(f"持仓成本（不复权）：{1_000_000 / shares:.2f} 元/股")

    # 前复权口径：每笔交易成本按当日前复权价折算（参考前复权K线对应日期），
    # 期末市值 = 买入股数合计 × 最新前复权价（分红送转已隐含在复权价格中，现金另行列示）
    bought_shares = sum(t["shares"] for t in trades)
    fwd_ok = (bought_shares > 0 and all(t["date"] in fwd_map for t in trades)
              and last_date in fwd_map)
    if fwd_ok:
        fwd_cost = sum(t["shares"] * fwd_map[t["date"]] for t in trades)
        fwd_cost_avg = fwd_cost / bought_shares
        fwd_value = bought_shares * fwd_map[last_date]
        fwd_return = (fwd_value / fwd_cost - 1) * 100
        print("\n---------- 前复权口径（成本价前复权） ----------")
        print(f"前复权成本合计：{fwd_cost:,.2f} 元  成本均价：{fwd_cost_avg:.4f} 元/股")
        print(f"最新前复权价：{fwd_map[last_date]:.4f} 元  前复权市值：{fwd_value:,.2f} 元")
        print(f"前复权收益率：{fwd_return:.2f}%")
        print("\n每笔交易明细（日期/价格/数量 + 当日前复权价）:")
        print(f"  {'交易日期':<12}{'类型':>10}{'成交价(不复权)':>14}{'数量':>10}{'金额':>14}{'当日前复权价':>14}")
        for t in trades:
            print(f"  {str(t['date']):<12}{t['kind']:>10}{t['price']:>14.2f}{t['shares']:>10,}"
                  f"{t['amount']:>14,.2f}{fwd_map[t['date']]:>14.4f}")
    else:
        print("\n前复权口径：未计算（前复权数据缺失或覆盖不全）")


if __name__ == "__main__":
    main()
