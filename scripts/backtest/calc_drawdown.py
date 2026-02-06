"""
Calculate Max Drawdown for the Final Strategy (Fixed Dynamic RSI)
"""

import pandas as pd
import numpy as np
from datetime import timedelta

print("="*60)
print("CALCULATING MAX DRAWDOWN")
print("Dynamic RSI 43/58 (Trend Adjusted)")
print("="*60)

df = pd.read_csv('data/btcusdt_1m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

end_date = df['timestamp'].max()
start_date = end_date - timedelta(days=180)
df = df[df['timestamp'] >= start_date].copy().reset_index(drop=True)

# Features
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi_14'] = 100 - (100 / (1 + rs))

df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
df['dist_ema_50'] = df['close'] / df['ema_50'] - 1

df['future_close'] = df['close'].shift(-15)
df['target'] = (df['future_close'] > df['close']).astype(int)

df = df.dropna()
df = df[df['timestamp'].dt.minute.isin([0, 15, 30, 45])].reset_index(drop=True)

trades = []
balance = 100.0
equity_curve = [100.0]

for i in range(len(df)):
    row = df.iloc[i]
    rsi = row['rsi_14']
    dist = row['dist_ema_50']
    
    rsi_buy = 43
    rsi_sell = 58
    
    if dist < 0: rsi_buy = 38
    if dist > 0: rsi_sell = 62
        
    signal = None
    if rsi < rsi_buy: signal = 'YES'
    elif rsi > rsi_sell: signal = 'NO'
    
    if not signal: continue
    
    won = (signal == 'YES' and row['target'] == 1) or (signal == 'NO' and row['target'] == 0)
    pnl = 0.96 if won else -1.02
    
    balance += pnl
    equity_curve.append(balance)

# Calculate Max DD
equity_series = pd.Series(equity_curve)
peak = equity_series.cummax()
drawdown = (equity_series - peak)  # Dollar amount drawdown
drawdown_pct = (drawdown / peak) * 100  # Percentage drawdown

max_dd_dollars = drawdown.min()
max_dd_pct = drawdown_pct.min()

print(f"\nMax Drawdown ($): {max_dd_dollars:.2f}")
print(f"Max Drawdown (%): {max_dd_pct:.2f}%")
print(f"Final Balance:    ${balance:.2f}")
print(f"Return/DD Ratio:  {(balance-100) / abs(max_dd_dollars):.2f}")
