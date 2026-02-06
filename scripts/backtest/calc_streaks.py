"""
Calculate Max Consecutive Losses
To clarify that -$34 drawdown != 34 losses in a row.
"""

import pandas as pd
import numpy as np
from datetime import timedelta

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
    trades.append(won)

# Calculate streaks
streaks = []
current_streak = 0
current_type = None # True (Win) or False (Loss)

for won in trades:
    if current_type is None:
        current_type = won
        current_streak = 1
    elif won == current_type:
        current_streak += 1
    else:
        streaks.append((current_type, current_streak))
        current_type = won
        current_streak = 1
streaks.append((current_type, current_streak))

# Analyze
max_win_streak = max([s[1] for s in streaks if s[0]])
max_loss_streak = max([s[1] for s in streaks if not s[0]])
avg_win_streak = np.mean([s[1] for s in streaks if s[0]])
avg_loss_streak = np.mean([s[1] for s in streaks if not s[0]])

print("="*50)
print("STREAK ANALYSIS")
print("="*50)
print(f"Total Trades: {len(trades)}")
print(f"Max Consecutive WINS:   {max_win_streak}")
print(f"Max Consecutive LOSSES: {max_loss_streak}")
print(f"Avg Win Streak:         {avg_win_streak:.1f}")
print(f"Avg Loss Streak:        {avg_loss_streak:.1f}")
