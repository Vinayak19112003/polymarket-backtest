"""
Final Verification of Fixed Dynamic RSI Strategy
Trend-Dependent Thresholds:
- Base: Buy < 43, Sell > 58
- Downtrend (Dist < 0): Buy < 38 (Stricter)
- Uptrend (Dist > 0): Sell > 62 (Stricter)
"""

import pandas as pd
import numpy as np
from datetime import timedelta

print("="*60)
print("FINAL STRATEGY VERIFICATION (FIXED)")
print("Dynamic RSI 43/58 (Trend Adjusted)")
print("="*60)

df = pd.read_csv('data/btcusdt_1m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

end_date = df['timestamp'].max()
start_date = end_date - timedelta(days=180)
df = df[df['timestamp'] >= start_date].copy().reset_index(drop=True)

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi_14'] = 100 - (100 / (1 + rs))

# EMA 50 for Trend
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
df['dist_ema_50'] = df['close'] / df['ema_50'] - 1

# Target
df['future_close'] = df['close'].shift(-15)
df['target'] = (df['future_close'] > df['close']).astype(int)

df = df.dropna()
df = df[df['timestamp'].dt.minute.isin([0, 15, 30, 45])].reset_index(drop=True)

trades = []
balance = 100.0

for i in range(len(df)):
    row = df.iloc[i]
    rsi = row['rsi_14']
    dist = row['dist_ema_50']
    
    # Dynamic thresholds
    rsi_buy = 43
    rsi_sell = 58
    
    if dist < 0: # Downtrend
        rsi_buy = 38
    if dist > 0: # Uptrend
        rsi_sell = 62
        
    signal = None
    if rsi < rsi_buy: signal = 'YES'
    elif rsi > rsi_sell: signal = 'NO'
    
    if not signal: continue
    
    won = (signal == 'YES' and row['target'] == 1) or (signal == 'NO' and row['target'] == 0)
    pnl = 0.96 if won else -1.02
    
    balance += pnl
    trades.append({'month': row['timestamp'].to_period('M'), 'pnl': pnl})

if not trades:
    print("No trades found")
    exit()

tdf = pd.DataFrame(trades)
monthly = tdf.groupby('month')['pnl'].sum()

print(f"\nTotal ROI: +{(balance - 100):.2f}%")
print(f"Total Trades: {len(trades)}")
print("\nMonthly Breakdown:")
print(monthly)

if (monthly > 10).all(): # Ensure at least $10 profit per month
    print("\nSUCCESS: All months > $10 profit!")
else:
    print("\nWARNING: Some months weak")
    for m, p in monthly.items():
        if p <= 10: print(f"  {m}: ${p:.2f} (Weak)")
