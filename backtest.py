"""
Polymarket BTC 15m Backtest
Strategy: RSI(14) < 43 -> BUY YES | RSI(14) > 57 -> BUY NO
Market: BTC Up/Down on Polymarket (binary, 15m resolution)
Period: 3 Years
"""

import requests
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
SYMBOL        = "BTCUSDT"
INTERVAL      = "15m"
RSI_PERIOD    = 14
RSI_BUY       = 43      # RSI < 43 → YES (price goes up)
RSI_SELL      = 57      # RSI > 57 → NO  (price goes down)
STAKE         = 0.50    # cost per trade on Polymarket
WIN_PAYOUT    = 1.00    # binary win
FEE_RATE      = 0.02    # 2% Polymarket fee on winnings
YEARS         = 3

END_TIME   = datetime(2026, 3, 25, 23, 59, 59, tzinfo=timezone.utc)
START_TIME = END_TIME - timedelta(days=YEARS * 365)

DATA_FILE    = "data/btcusdt_15m_3y.csv"
RESULTS_FILE = "results/backtest_report.txt"

# ── Data Download ─────────────────────────────────────────────────────────────

def fetch_binance_15m(start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    base_url = "https://api.binance.com/api/v3/klines"
    all_rows = []

    start_ts = int(start_dt.timestamp() * 1000)
    end_ts   = int(end_dt.timestamp() * 1000)
    current  = start_ts

    print(f"Downloading {SYMBOL} {INTERVAL} data: {start_dt.date()} → {end_dt.date()}")

    while current < end_ts:
        params = {
            "symbol":    SYMBOL,
            "interval":  INTERVAL,
            "startTime": current,
            "endTime":   end_ts,
            "limit":     1000,
        }
        try:
            resp = requests.get(base_url, params=params, timeout=10)
            data = resp.json()

            if not data or not isinstance(data, list):
                break

            for k in data:
                all_rows.append({
                    "timestamp": pd.to_datetime(int(k[0]), unit="ms", utc=True),
                    "open":      float(k[1]),
                    "high":      float(k[2]),
                    "low":       float(k[3]),
                    "close":     float(k[4]),
                    "volume":    float(k[5]),
                })

            current = int(data[-1][0]) + 1
            print(f"  fetched {len(all_rows):,} candles...", end="\r")
            time.sleep(0.1)

            if len(data) < 1000:
                break

        except Exception as e:
            print(f"\nError: {e}")
            break

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.sort_values("timestamp").reset_index(drop=True)
    print(f"\nTotal candles downloaded: {len(df):,}")
    return df


def load_or_download() -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        print(f"Loading cached data from {DATA_FILE}...")
        df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
        print(f"Loaded {len(df):,} candles.")
        return df

    df = fetch_binance_15m(START_TIME, END_TIME)
    if df.empty:
        raise RuntimeError("No data fetched. Check network / Binance API access.")

    os.makedirs("data", exist_ok=True)
    df.to_csv(DATA_FILE, index=False)
    print(f"Saved to {DATA_FILE}")
    return df


# ── Indicators ────────────────────────────────────────────────────────────────

def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).ewm(alpha=1 / period, adjust=False).mean()
    loss  = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / period, adjust=False).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))


# ── Backtest ──────────────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rsi"] = calc_rsi(df["close"], RSI_PERIOD)

    # Signal uses PREVIOUS closed candle's RSI → trade on CURRENT candle
    df["prev_rsi"] = df["rsi"].shift(1)

    df["signal"] = None
    df.loc[df["prev_rsi"] < RSI_BUY,  "signal"] = "YES"
    df.loc[df["prev_rsi"] > RSI_SELL, "signal"] = "NO"

    trades = df[df["signal"].notna()].copy()

    # Win = price moved in predicted direction over the candle
    trades["won"] = (
        ((trades["signal"] == "YES") & (trades["close"] > trades["open"])) |
        ((trades["signal"] == "NO")  & (trades["close"] < trades["open"]))
    )

    fee = WIN_PAYOUT * FEE_RATE          # $0.02
    trades["pnl"] = np.where(
        trades["won"],
        WIN_PAYOUT - STAKE - fee,        # +$0.48
        -STAKE                           # -$0.50
    )

    trades["cumulative_pnl"] = trades["pnl"].cumsum()
    return trades


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(trades: pd.DataFrame, df: pd.DataFrame):
    total  = len(trades)
    wins   = trades["won"].sum()
    losses = total - wins
    wr     = wins / total * 100
    pnl    = trades["pnl"].sum()

    # Drawdown
    equity  = trades["cumulative_pnl"]
    peak    = equity.cummax()
    dd      = equity - peak
    max_dd  = dd.min()

    # Streaks
    results = trades["won"].astype(int).tolist()
    max_win_streak = max_loss_streak = cur = 0
    cur_type = None
    for r in results:
        if r == cur_type:
            cur += 1
        else:
            cur = 1
            cur_type = r
        if r == 1:
            max_win_streak  = max(max_win_streak, cur)
        else:
            max_loss_streak = max(max_loss_streak, cur)

    yes_trades = trades[trades["signal"] == "YES"]
    no_trades  = trades[trades["signal"] == "NO"]

    yes_wr = yes_trades["won"].mean() * 100 if len(yes_trades) else 0
    no_wr  = no_trades["won"].mean()  * 100 if len(no_trades)  else 0

    # Monthly breakdown
    trades["month"] = trades["timestamp"].dt.to_period("M")
    monthly = trades.groupby("month").agg(
        trades_count=("pnl", "count"),
        pnl=("pnl", "sum"),
        win_rate=("won", lambda x: x.mean() * 100)
    )

    lines = []
    lines.append("=" * 60)
    lines.append("  POLYMARKET BTC 15M BACKTEST — 3 YEAR REPORT")
    lines.append("=" * 60)
    lines.append(f"  Period       : {df['timestamp'].min().date()} → {df['timestamp'].max().date()}")
    lines.append(f"  Strategy     : RSI({RSI_PERIOD}) < {RSI_BUY} = YES  |  RSI > {RSI_SELL} = NO")
    lines.append(f"  Stake/Trade  : ${STAKE:.2f}  |  Fee: {FEE_RATE*100:.0f}%")
    lines.append(f"  Total Candles: {len(df):,}")
    lines.append("-" * 60)
    lines.append("  PERFORMANCE")
    lines.append("-" * 60)
    lines.append(f"  Total Trades : {total:,}")
    lines.append(f"  Wins         : {wins:,}")
    lines.append(f"  Losses       : {losses:,}")
    lines.append(f"  Win Rate     : {wr:.2f}%")
    lines.append(f"  Total PnL    : ${pnl:.2f}")
    lines.append(f"  Avg PnL/Trade: ${pnl/total:.4f}")
    lines.append(f"  Max Drawdown : ${max_dd:.2f}")
    lines.append(f"  Max Win Streak : {max_win_streak}")
    lines.append(f"  Max Loss Streak: {max_loss_streak}")
    lines.append("-" * 60)
    lines.append("  BY SIGNAL")
    lines.append("-" * 60)
    lines.append(f"  YES Trades: {len(yes_trades):,}  |  Win Rate: {yes_wr:.2f}%  |  PnL: ${yes_trades['pnl'].sum():.2f}")
    lines.append(f"  NO  Trades: {len(no_trades):,}  |  Win Rate: {no_wr:.2f}%  |  PnL: ${no_trades['pnl'].sum():.2f}")
    lines.append("-" * 60)
    lines.append("  MONTHLY BREAKDOWN")
    lines.append("-" * 60)
    lines.append(f"  {'Month':<10} {'Trades':>7} {'Win Rate':>10} {'PnL':>10}")
    lines.append(f"  {'-'*10} {'-'*7} {'-'*10} {'-'*10}")
    for month, row in monthly.iterrows():
        lines.append(f"  {str(month):<10} {int(row['trades_count']):>7} {row['win_rate']:>9.2f}% {row['pnl']:>10.2f}")
    lines.append("=" * 60)

    report = "\n".join(lines)
    print(report)

    os.makedirs("results", exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        f.write(report + "\n")
    print(f"\nReport saved → {RESULTS_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df     = load_or_download()
    trades = run_backtest(df)
    print_report(trades, df)
