
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone, timedelta

# Constants
SYMBOL = "BTCUSDT"
INTERVAL = "1m"

# Past 30 Days from Feb 6, 2026
END_TIME = datetime(2026, 2, 6, 23, 59, 59, tzinfo=timezone.utc)
START_TIME = END_TIME - timedelta(days=32) # Fetch 32 days to ensure indicator warmup

ENTRY_PRICE = 0.50
FEES = 0.02

def fetch_binance_klines(start_dt, end_dt):
    base_url = "https://api.binance.com/api/v3/klines"
    all_data = []
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    current_start = start_ts
    
    print(f"Fetching {SYMBOL} data from {start_dt.date()} to {end_dt.date()}...")
    
    while current_start < end_ts:
        params = {
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "startTime": current_start,
            "limit": 1000
        }
        try:
            resp = requests.get(base_url, params=params)
            data = resp.json()
            
            if not data or not isinstance(data, list):
                break
                
            for kline in data:
                ts = int(kline[0])
                if ts > end_ts:
                    break
                all_data.append({
                    "timestamp": pd.to_datetime(ts, unit='ms'),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5])
                })
            
            last_ts = data[-1][0]
            current_start = last_ts + 60000
            time.sleep(0.05)
            
            if len(data) < 1000:
                break
                
        except Exception as e:
            print(f"Error: {e}")
            break
            
    df = pd.DataFrame(all_data)
    print(f"Fetched {len(df)} candles.")
    return df

def run_simulation(df):
    if df.empty:
        return

    # Filter strictly for last 30 days for REPORTING, but use full data for CALCULATION
    report_start_date = (END_TIME - timedelta(days=30)).date()
    print(f"Reporting Period: {report_start_date} to {END_TIME.date()}")

    print("Resampling to 15m...")
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()
    
    # Indicators
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # Shift Logic
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    # Thresholds (Architecture: Use Shared Constants from Strategy Module)
    # This ensures "What you backtest is exactly what runs live"
    try:
        from src.features.strategy import (
            RSI_OVERSOLD_DEFAULT, RSI_OVERBOUGHT_DEFAULT,
            RSI_BUY_DOWNTREND, RSI_SELL_UPTREND
        )
        print("Using Shared Strategy Constants.")
    except ImportError:
        # Fallback if run from wrong dir
        print("WARNING: Could not import strategy. Using local defaults.")
        RSI_OVERSOLD_DEFAULT = 43
        RSI_OVERBOUGHT_DEFAULT = 58
        RSI_BUY_DOWNTREND = 38
        RSI_SELL_UPTREND = 62

    conditions = [
        (df_15m['dist_ema'] < 0),
        (df_15m['dist_ema'] > 0)
    ]
    choices_buy = [RSI_BUY_DOWNTREND, RSI_OVERSOLD_DEFAULT]
    choices_sell = [RSI_OVERBOUGHT_DEFAULT, RSI_SELL_UPTREND]
    
    df_15m['thresh_buy'] = np.select(conditions, choices_buy, default=RSI_OVERSOLD_DEFAULT)
    df_15m['thresh_sell'] = np.select(conditions, choices_sell, default=RSI_OVERBOUGHT_DEFAULT)
    
    # Signals
    df_15m['signal'] = 'NONE'
    df_15m.loc[df_15m['prev_rsi'] < df_15m['thresh_buy'], 'signal'] = 'YES'
    df_15m.loc[df_15m['prev_rsi'] > df_15m['thresh_sell'], 'signal'] = 'NO'
    
    trades = df_15m[df_15m['signal'] != 'NONE'].copy()
    trades['entry_price'] = trades['open']
    trades['exit_price'] = trades['close']
    
    trades['result'] = 'LOSS'
    trades.loc[(trades['signal'] == 'YES') & (trades['exit_price'] > trades['entry_price']), 'result'] = 'WIN'
    trades.loc[(trades['signal'] == 'NO') & (trades['exit_price'] < trades['entry_price']), 'result'] = 'WIN'
    
    cost = ENTRY_PRICE
    fees = cost * FEES
    trades['pnl'] = np.where(trades['result'] == 'WIN', (1.0 - cost - fees), (-cost - fees))
    
    # Filter for Reporting Period
    trades['date'] = trades.index.date
    trades = trades[trades['date'] >= report_start_date].copy()
    
    # Summary
    total_trades = len(trades)
    wins = len(trades[trades['result'] == 'WIN'])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    total_pnl = trades['pnl'].sum()
    
    print("\n" + "="*50)
    print("PAST 30 DAYS PERFORMANCE (Live Data)")
    print(f"Period: {report_start_date} - {END_TIME.date()}")
    print("="*50)
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate:     {win_rate:.2f}%")
    print(f"Total PnL:    ${total_pnl:.2f}")
    print("-" * 50)
    
    # Daily Breakdown
    daily = trades.groupby('date').agg({'pnl': 'sum', 'result': 'count'}).rename(columns={'result': 'trades'})
    if not daily.empty:
        daily['win_rate'] = trades.groupby('date').apply(lambda x: len(x[x['result']=='WIN']) / len(x) * 100)
    
    print("DAILY BREAKDOWN:")
    print(daily)
    print("="*50)

    # Export to text file as requested
    output_file = "results/last_30d_performance.txt"
    with open(output_file, "w") as f:
        f.write("date        pnl       trades  win_rate\n")
        for date, row in daily.iterrows():
            # Ensure win_rate exists
            wr = row['win_rate'] if 'win_rate' in row else 0.0
            # Matches format: 2026-01-07  1.78      22  59.090909
            f.write(f"{date}  {row['pnl']:.2f}      {int(row['trades'])}  {wr:.6f}\n")
        f.write("=====================================\n")
    print(f"\nSaved report to {output_file}")

if __name__ == "__main__":
    df = fetch_binance_klines(START_TIME, END_TIME)
    run_simulation(df)
