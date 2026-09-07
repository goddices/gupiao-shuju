import pandas as pd
from sqlalchemy import create_engine, text

# ---------- 数据库配置 ----------
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "deepstock",
}
ENGINE = create_engine(
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4",
    echo=False,
)

ADJUST_COLUMNS = [
    "forward_open",
    "forward_high",
    "forward_low",
    "forward_close",
    "backward_open",
    "backward_high",
    "backward_low",
    "backward_close",
]


def _apply_additive_adjustment(df, df_events):
    """
    加法复权：直接在价格列上应用除权除息调整。
    - 前复权：从最新除权日向历史回溯，每次将除权日之前的开高低收调整。
    - 后复权：从最早除权日向未来前进，每次将除权日及之后的开高低收调整。
    """
    # 复制原始价格，用于后续计算
    for col in ["open_price", "high_price", "low_price", "close_price"]:
        df[f"forward_{col.split('_')[0]}"] = df[col].copy()
        df[f"backward_{col.split('_')[0]}"] = df[col].copy()

    if df_events.empty:
        return df  # 无除权事件，复权价 = 原价

    # ---------- 前复权：按除权日倒序处理 ----------
    for ex_date in sorted(df_events.index, reverse=True):
        if ex_date not in df.index:
            continue
        i = df.index.get_loc(ex_date)
        if i == 0:
            continue
        ev = df_events.loc[ex_date]
        C = ev["cash"]
        S = ev["bonus"]
        R = ev["conversion"]
        denom = 1.0 + S + R
        if denom <= 0 or df.iloc[i - 1]["close_price"] <= C:
            print(f"⚠️ 前复权跳过异常除权日 {ex_date.date()}")
            continue
        # 将该除权日之前的所有价格（包括当日之前）进行调整
        # 注意：公式中使用的价格是调整前的原始价格？还是已经调整过的？
        # 加法前复权规定：每次调整使用调整前的原价，但多个事件叠加时，按时间顺序从最新往旧调整，
        # 每次调整都基于原始价格（不含之前调整）？实际上，加法复权的公式是递推的，每次调整后，
        # 已调整部分保持，未调整部分用原价。标准算法是：从除权日向前，将除权日以前的价格应用公式，
        # 但该公式中的价格是调整前的价格（还未被本次调整影响）。由于我们按倒序处理，处理较晚除权日时，
        # 较早的历史价格还没有被调整，所以可以直接用原始价格列。但为了准确，我们应该针对每个除权日，
        # 将该除权日之前的所有日期（包括更早）的价格进行调整，而这些日期可能已被之前（更晚）的除权日调整过，
        # 所以应该使用当前已调整过的价格（即当前的 forward_* 列）。
        # 因此，我们直接对当前的 forward_* 列进行操作，这些列已经包含了更晚除权日的调整。
        # 所以，对于该除权日，将除权日之前的所有行的 forward_* 列应用：(当前值 - C) / denom
        mask = df.index < ex_date
        for pcol in ["forward_open", "forward_high", "forward_low", "forward_close"]:
            df.loc[mask, pcol] = (df.loc[mask, pcol] - C) / denom

    # ---------- 后复权：按除权日正序处理 ----------
    # 后复权从最早除权日开始，将除权日及之后的价格调整：新值 = 旧值 * denom + C
    for ex_date in sorted(df_events.index):
        if ex_date not in df.index:
            continue
        ev = df_events.loc[ex_date]
        C = ev["cash"]
        S = ev["bonus"]
        R = ev["conversion"]
        denom = 1.0 + S + R
        if denom <= 0:
            print(f"⚠️ 后复权跳过异常除权日 {ex_date.date()}")
            continue
        # 将该除权日及之后的所有价格调整
        mask = df.index >= ex_date
        for pcol in [
            "backward_open",
            "backward_high",
            "backward_low",
            "backward_close",
        ]:
            df.loc[mask, pcol] = df.loc[mask, pcol] * denom + C

    return df


def compute_adjusted_ohlc(stock_code: str, dry_run: bool = False):
    """
    计算指定股票的前/后复权 OHLC。

    dry_run=True 时只按事件表自行重算，并与数据库现存的复权价逐行比对，
    打印差异汇总，不写库。用于核对"表里的复权价对不对"。
    dry_run=False 时重算并写回数据库。
    """
    # ---------- 1. 读取不复权行情 ----------
    df = pd.read_sql(
        text("""
            SELECT trade_date, open_price, high_price, low_price, close_price
            FROM stock_daily_quote
            WHERE stock_code = :code
            ORDER BY trade_date ASC
        """),
        ENGINE,
        params={"code": stock_code},
    )
    if df.empty:
        print(f"⚠️ 股票 {stock_code} 无行情数据")
        return

    for c in ["open_price", "high_price", "low_price", "close_price"]:
        df[c] = df[c].astype(float)
    df["date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("date").sort_index()

    # ---------- 2. 读取除权事件 ----------
    df_events = pd.read_sql(
        text("""
            SELECT ex_dividend_date, cash_per_10, bonus_per_10, conversion_per_10
            FROM stock_dividend_events
            WHERE stock_code = :code
            ORDER BY ex_dividend_date ASC
        """),
        ENGINE,
        params={"code": stock_code},
    )
    if not df_events.empty:
        df_events["cash"] = df_events["cash_per_10"].fillna(0).astype(float) / 10.0
        df_events["bonus"] = df_events["bonus_per_10"].fillna(0).astype(float) / 10.0
        df_events["conversion"] = (
            df_events["conversion_per_10"].fillna(0).astype(float) / 10.0
        )
        df_events["ex_date"] = pd.to_datetime(df_events["ex_dividend_date"])
        # 同一除权日多条事件合并
        df_events = (
            df_events.groupby("ex_date", as_index=False)
            .agg({"cash": "sum", "bonus": "sum", "conversion": "sum"})
            .set_index("ex_date")
        )
    else:
        df_events = pd.DataFrame(columns=["cash", "bonus", "conversion"])

    # ---------- 3. 应用加法复权 ----------
    df = _apply_additive_adjustment(df, df_events)

    # ---------- 4. dry_run：与现存值比对，不写库 ----------
    if dry_run:
        stored = pd.read_sql(
            text("""
                SELECT trade_date, forward_close, backward_close
                FROM stock_daily_quote
                WHERE stock_code = :code
                ORDER BY trade_date ASC
            """),
            ENGINE,
            params={"code": stock_code},
        )
        stored["date"] = pd.to_datetime(stored["trade_date"])
        stored = stored.set_index("date")
        cmp = df[["forward_close", "backward_close"]].join(
            stored.rename(
                columns={"forward_close": "stored_f", "backward_close": "stored_b"}
            )
        )
        for c in ["stored_f", "stored_b"]:
            cmp[c] = cmp[c].astype(float)
        diff_f = (cmp["forward_close"] - cmp["stored_f"]).abs()
        diff_b = (cmp["backward_close"] - cmp["stored_b"]).abs()
        print(f"\n🔍 {stock_code} dry_run 比对（共 {len(cmp)} 行）:")
        print(
            f"   前复权 close 误差>0.01: {(diff_f > 0.01).sum()} 行 | 最大误差 {diff_f.max():.4f}"
        )
        print(
            f"   后复权 close 误差>0.01: {(diff_b > 0.01).sum()} 行 | 最大误差 {diff_b.max():.4f}"
        )
        print(
            "   最近5行: close / 计算forward / 存储forward / 计算backward / 存储backward"
        )
        print(
            cmp[["forward_close", "stored_f", "backward_close", "stored_b"]]
            .assign(close=df["close_price"])
            .tail(5)
            .round(4)
        )
        print("   （dry_run 未写库）")
        return

    # ---------- 5. 写回数据库 ----------
    print(f"\n📊 {stock_code} 复权对比（最近5个交易日）：")
    print(
        df[
            [
                "open_price",
                "forward_open",
                "backward_open",
                "close_price",
                "forward_close",
                "backward_close",
            ]
        ]
        .tail(5)
        .round(4)
    )

    with ENGINE.connect() as conn:
        for col in ADJUST_COLUMNS:
            try:
                conn.execute(
                    text(
                        f"ALTER TABLE stock_daily_quote ADD COLUMN {col} DECIMAL(12,4) DEFAULT NULL"
                    )
                )
            except Exception:
                pass
        conn.commit()

    update_sql = text("""
        UPDATE stock_daily_quote
        SET
            forward_open   = :f_open, forward_high   = :f_high,
            forward_low    = :f_low,  forward_close  = :f_close,
            backward_open  = :b_open, backward_high  = :b_high,
            backward_low   = :b_low,  backward_close = :b_close
        WHERE stock_code = :code AND trade_date = :date
    """)
    rows = [
        {
            "f_open": float(r["forward_open"]),
            "f_high": float(r["forward_high"]),
            "f_low": float(r["forward_low"]),
            "f_close": float(r["forward_close"]),
            "b_open": float(r["backward_open"]),
            "b_high": float(r["backward_high"]),
            "b_low": float(r["backward_low"]),
            "b_close": float(r["backward_close"]),
            "code": stock_code,
            "date": idx.strftime("%Y-%m-%d"),
        }
        for idx, r in df.iterrows()
    ]
    with ENGINE.connect() as conn:
        conn.execute(update_sql, rows)
        conn.commit()

    print(f"✅ {stock_code} 复权OHLC已写回数据库（{len(rows)} 条）")


if __name__ == "__main__":
    # 先核对（不写库）：确认表里的复权价与按事件表自算的是否一致
    compute_adjusted_ohlc("601857", dry_run=True)

    # 核对无误后再写库：
    # compute_adjusted_ohlc("601857", dry_run=False)

    # 批量：
    # for code in ["600036", "000858"]:
    #     compute_adjusted_ohlc(code, dry_run=False)
