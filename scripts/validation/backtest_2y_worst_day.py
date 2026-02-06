
import sys
import os
import pandas as pd
import numpy as np
from datetime import timedelta

# Constants
ENTRY_PRICE = 0.50
FEES = 0.02
DATA_FILE = "data/btcusdt_1m.csv"

def run_analysis():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    print(f"Loading {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # USE FULL DATA (Assuming file is ~2 years)
    start_date = df['timestamp'].min()
    end_date = df['timestamp'].max()
    print(f"Data Range: {start_date} to {end_date}")
    
    if df.empty:
        print("No data found.")
        return

    print("Resampling to 15m...")
    
    # Resample to 15m
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()
    
    # Compute Indicators
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # Shift indicators
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    
    # Signal Logic
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
    
    df_15m['signal'] = 'NONE'
    df_15m.loc[df_15m['prev_rsi'] < df_15m['thresh_buy'], 'signal'] = 'YES'
    df_15m.loc[df_15m['prev_rsi'] > df_15m['thresh_sell'], 'signal'] = 'NO'
    
    # Trades only
    trades = df_15m[df_15m['signal'] != 'NONE'].copy()
    
    trades['entry_price'] = trades['open']
    trades['exit_price'] = trades['close']
    
    trades['result'] = 'LOSS'
    trades.loc[(trades['signal'] == 'YES') & (trades['exit_price'] > trades['entry_price']), 'result'] = 'WIN'
    trades.loc[(trades['signal'] == 'NO') & (trades['exit_price'] < trades['entry_price']), 'result'] = 'WIN'
    
    cost = ENTRY_PRICE
    fees = cost * FEES
    trades['pnl'] = np.where(trades['result'] == 'WIN', (1.0 - cost - fees), (-cost - fees))
    
    # GROUP BY DAY
    trades['date'] = trades.index.date
    daily = trades.groupby('date').agg({
        'pnl': 'sum', 
        'result': 'count',
    }).rename(columns={'result': 'trades'})
    
    daily['win_rate'] = trades.groupby('date').apply(lambda x: len(x[x['result']=='WIN']) / len(x) * 100 if len(x) > 0 else 0)
    
    # Sort by PnL (Worst first)
    worst_days = daily.sort_values('pnl', ascending=True).head(15)
    
    print("\n" + "="*60)
    print("WORST 15 DAYS (Last 2 Years)")
    print("="*60)
    print(f"{'Date':<12} | {'PnL ($)':<10} | {'Trades':<8} | {'Win Rate':<10}")
    print("-" * 60)
    
    for date, row in worst_days.iterrows():
        print(f"{str(date):<12} | ${row['pnl']:<9.2f} | {row['trades']:<8} | {row['win_rate']:.1f}%")
        
    print("-" * 60)

if __name__ == "__main__":
    run_analysis()
