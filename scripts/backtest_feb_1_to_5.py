
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone

# Constants
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
START_TIME = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
END_TIME = datetime(2026, 2, 6, 0, 0, 0, tzinfo=timezone.utc) # Up to end of Feb 5
ENTRY_PRICE = 0.50
FEES = 0.02

def fetch_binance_klines(start_dt, end_dt):
    base_url = "https://api.binance.com/api/v3/klines"
    all_data = []
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    current_start = start_ts
    
    print(f"Fetching {SYMBOL} data from {start_dt} to {end_dt}...")
    
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
                print("No more data received or error.")
                break
                
            for kline in data:
                # [Open time, Open, High, Low, Close, Volume, ...]
                ts = int(kline[0])
                if ts >= end_ts:
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
            current_start = last_ts + 60000 # +1 minute
            
            # Rate limit respect
            time.sleep(0.1)
            
            if len(data) < 1000:
                break
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
    df = pd.DataFrame(all_data)
    print(f"Fetched {len(df)} candles.")
    return df

def run_simulation(df):
    if df.empty:
        print("No data to backtest.")
        return

    print("Resampling to 15m (Strict Snapshot Logic)...")
    
    # Resample to 15m
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()
    
    # Compute Indicators on 15m
    # RSI 14
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    
    # EMA 50
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # Shift indicators by 1 (We use PREVIOUS Close to decide at CURRENT Open)
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    
    # Signal Logic (Vectorized)
    # Dist < 0 means Prev Close < Prev EMA (Downtrend)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    # Thresholds (Dynamic)
    conditions = [
        (df_15m['dist_ema'] < 0), # Downtrend
        (df_15m['dist_ema'] > 0)  # Uptrend
    ]
    choices_buy = [38, 43]
    choices_sell = [58, 62]
    
    df_15m['thresh_buy'] = np.select(conditions, choices_buy, default=43)
    df_15m['thresh_sell'] = np.select(conditions, choices_sell, default=58)
    
    # Generate Signals
    df_15m['signal'] = 'NONE'
    df_15m.loc[df_15m['prev_rsi'] < df_15m['thresh_buy'], 'signal'] = 'YES'
    df_15m.loc[df_15m['prev_rsi'] > df_15m['thresh_sell'], 'signal'] = 'NO'
    
    # Filter only trades
    trades = df_15m[df_15m['signal'] != 'NONE'].copy()
    
    trades['entry_price'] = trades['open']
    trades['exit_price'] = trades['close']
    
    # Win/Loss
    trades['result'] = 'LOSS'
    trades.loc[(trades['signal'] == 'YES') & (trades['exit_price'] > trades['entry_price']), 'result'] = 'WIN'
    trades.loc[(trades['signal'] == 'NO') & (trades['exit_price'] < trades['entry_price']), 'result'] = 'WIN'
    
    # PnL
    cost = ENTRY_PRICE
    fees = cost * FEES
    trades['pnl'] = np.where(trades['result'] == 'WIN', (1.0 - cost - fees), (-cost - fees))
    
    # REPORTING
    total_trades = len(trades)
    win_rate = len(trades[trades['result'] == 'WIN']) / total_trades * 100 if total_trades > 0 else 0
    total_pnl = trades['pnl'].sum()
    
    # Daily (Feb 1-5 specific)
    trades['date'] = trades.index.date
    daily = trades.groupby('date').agg({'pnl': 'sum', 'result': 'count'})
    if not trades.empty:
        daily['win_rate'] = trades.groupby('date').apply(lambda x: len(x[x['result']=='WIN']) / len(x) * 100)
    
    print("\n" + "="*50)
    print("PERFORMANCE REPORT: FEB 1 - FEB 5, 2026")
    print("="*50)
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate:     {win_rate:.2f}%")
    print(f"Total PnL:    ${total_pnl:.2f}")
    print("-" * 50)
    print("DAILY BREAKDOWN:")
    print(daily)
    print("="*50)
    
    trades[['signal','entry_price','exit_price','result','pnl']].to_csv("results/feb_1_5_trades.csv")

if __name__ == "__main__":
    df = fetch_binance_klines(START_TIME, END_TIME)
    run_simulation(df)
