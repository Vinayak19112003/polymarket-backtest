
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone, timedelta

# Constants
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
# 2 Years ago from today (Feb 6, 2026)
END_TIME = datetime(2026, 2, 6, 23, 59, 59, tzinfo=timezone.utc)
START_TIME = END_TIME - timedelta(days=730) # 2 Years

ENTRY_PRICE = 0.50
FEES = 0.02

def fetch_binance_klines(start_dt, end_dt):
    base_url = "https://api.binance.com/api/v3/klines"
    all_data = []
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    current_start = start_ts
    
    print(f"Fetching {SYMBOL} data from {start_dt.date()} to {end_dt.date()} (~2 years)...")
    print("This may take a minute due to rate limits...")
    
    while current_start < end_ts:
        params = {
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "startTime": current_start,
            "endTime": end_ts,
            "limit": 1000
        }
        try:
            resp = requests.get(base_url, params=params)
            if resp.status_code != 200:
                print(f"Error {resp.status_code}: {resp.text}")
                time.sleep(1)
                continue
                
            data = resp.json()
            
            if not data or not isinstance(data, list):
                break
                
            for kline in data:
                ts = int(kline[0])
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
            
            # Progress indicator
            if len(all_data) % 50000 == 0:
                print(f"Fetched {len(all_data)} candles...")
                
            time.sleep(0.05) # Be gentle with API
            
            if len(data) < 1000:
                break
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
    df = pd.DataFrame(all_data)
    print(f"Total fetched: {len(df)} candles.")
    return df

def run_simulation(df):
    if df.empty:
        return

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
    
    # Shift logic (Strict)
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    # Dynamic Thresholds
    conditions = [
        (df_15m['dist_ema'] < 0),
        (df_15m['dist_ema'] > 0)
    ]
    choices_buy = [38, 43]
    choices_sell = [58, 62]
    
    df_15m['thresh_buy'] = np.select(conditions, choices_buy, default=43)
    df_15m['thresh_sell'] = np.select(conditions, choices_sell, default=58)
    
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
    
    # Daily aggregation
    trades['date'] = trades.index.date
    daily = trades.groupby('date').agg({'pnl': 'sum', 'result': 'count'}).rename(columns={'result': 'trades'})
    
    daily['win_rate'] = trades.groupby('date').apply(lambda x: len(x[x['result']=='WIN']) / len(x) * 100 if len(x) > 0 else 0)
    
    # Sort worst first
    worst_days = daily.sort_values('pnl', ascending=True).head(10)
    
    print("\n" + "="*70)
    print("TOP 10 WORST DAYS (Last 2 Years - Up to Feb 6 2026)")
    print("="*70)
    print(f"{'Date':<15} | {'PnL ($)':<10} | {'Trades':<8} | {'Win Rate':<10}")
    print("-" * 70)
    
    for date, row in worst_days.iterrows():
        print(f"{str(date):<15} | ${row['pnl']:<9.2f} | {row['trades']:<8} | {row['win_rate']:.1f}%")
    print("="*70)

if __name__ == "__main__":
    df = fetch_binance_klines(START_TIME, END_TIME)
    run_simulation(df)
